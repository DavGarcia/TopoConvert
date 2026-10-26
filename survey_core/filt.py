"""Step 5 (`filt.py`): Filter TIN triangles by max edge length, min angle, and boundary polygon."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from survey_core.io import build_viewer_payload_from_state
from survey_core.models import SurveyState


def _compute_triangle_geometry(
    verts_xyz: np.ndarray, triangles: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute (max_edge_lengths, min_angles_deg, plan_areas, areas_3d) for each triangle."""
    if len(triangles) == 0:
        empty = np.zeros((0,), dtype=np.float64)
        return (empty, empty, empty, empty)

    p0 = verts_xyz[triangles[:, 0]]
    p1 = verts_xyz[triangles[:, 1]]
    p2 = verts_xyz[triangles[:, 2]]

    ab = p1 - p0
    ac = p2 - p0
    bc = p2 - p1

    a = np.linalg.norm(ab[:, :2], axis=1)
    b = np.linalg.norm(ac[:, :2], axis=1)
    c = np.linalg.norm(bc[:, :2], axis=1)

    max_edges = np.maximum(np.maximum(a, b), c)

    # Law of cosines for minimum interior angle
    a2 = np.maximum(a * a, 1e-12)
    b2 = np.maximum(b * b, 1e-12)
    c2 = np.maximum(c * c, 1e-12)
    cos_alpha = np.clip((b2 + c2 - a2) / (2.0 * np.sqrt(b2 * c2)), -1.0, 1.0)
    cos_beta = np.clip((a2 + c2 - b2) / (2.0 * np.sqrt(a2 * c2)), -1.0, 1.0)
    cos_gamma = np.clip((a2 + b2 - c2) / (2.0 * np.sqrt(a2 * b2)), -1.0, 1.0)
    # Largest cosine corresponds to smallest angle in [0, pi]
    max_cos = np.maximum(np.maximum(cos_alpha, cos_beta), cos_gamma)
    min_angles_deg = np.degrees(np.arccos(max_cos))

    plan_areas = 0.5 * np.abs(ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0])
    areas_3d = 0.5 * np.linalg.norm(np.cross(ab, ac), axis=1)

    return (max_edges, min_angles_deg, plan_areas, areas_3d)


def _extract_outer_boundary_from_triangles(
    verts_xyz: np.ndarray, triangles: np.ndarray
) -> list[tuple[float, float]] | None:
    """Compute outer boundary ring from filtered triangles (fast topological boundary + Shapely for small meshes)."""
    if len(triangles) == 0:
        return None
    if len(triangles) <= 1500:
        try:
            polys = []
            for t in triangles:
                p0 = (float(verts_xyz[t[0], 0]), float(verts_xyz[t[0], 1]))
                p1 = (float(verts_xyz[t[1], 0]), float(verts_xyz[t[1], 1]))
                p2 = (float(verts_xyz[t[2], 0]), float(verts_xyz[t[2], 1]))
                poly = Polygon([p0, p1, p2])
                if poly.is_valid and poly.area > 1e-9:
                    polys.append(poly)
            if not polys:
                return None
            merged = unary_union(polys)
            if merged.geom_type == "Polygon":
                return [(float(x), float(y)) for x, y in merged.exterior.coords]
            if merged.geom_type == "MultiPolygon":
                largest = max(merged.geoms, key=lambda g: g.area)
                return [(float(x), float(y)) for x, y in largest.exterior.coords]
        except (ValueError, TypeError, AttributeError):
            return None

    # Fast topological boundary extraction for large meshes (edges occurring once)
    n_v = int(len(verts_xyz) + 1)
    e01 = triangles[:, [0, 1]]
    e12 = triangles[:, [1, 2]]
    e20 = triangles[:, [2, 0]]
    directed = np.vstack([e01, e12, e20])
    undirected = np.sort(directed, axis=1)
    keys = undirected[:, 0].astype(np.int64) * n_v + undirected[:, 1].astype(np.int64)
    _uniq_keys, idx_first, counts = np.unique(
        keys, return_index=True, return_counts=True
    )
    bnd_directed = directed[idx_first[counts == 1]]
    if len(bnd_directed) < 3:
        return None
    next_map = {int(u): int(v) for u, v in bnd_directed}
    start_u = int(bnd_directed[0, 0])
    loop: list[tuple[float, float]] = []
    curr = start_u
    for _ in range(min(len(bnd_directed) + 1, 5000)):
        loop.append((float(verts_xyz[curr, 0]), float(verts_xyz[curr, 1])))
        nxt = next_map.get(curr)
        if nxt is None or nxt == start_u:
            loop.append((float(verts_xyz[start_u, 0]), float(verts_xyz[start_u, 1])))
            break
        curr = nxt
    return loop if len(loop) >= 3 else None


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 5: Filter TIN triangles by max edge length, min angle, and optional boundary polygon.

    Parameters in `params`:
        max_edge_length (float | None): Max allowed triangle edge length in meters (default: 10.0 m).
            If None or <= 0, no edge length limit is applied.
        min_angle_deg (float): Min allowed interior triangle angle in degrees (default: 0.0 deg).
        use_boundary_polygon (bool): Clip triangles to boundary polygon if available (default: True).
        boundary_local (list[tuple[float, float]] | None): Optional custom boundary polygon in local XY.
        holes_local (list[list[tuple[float, float]]] | None): Optional hole rings in local XY.
    """
    if len(state.tin_vertices_local) == 0 or len(state.tin_triangles) == 0:
        raise ValueError("ابتدا باید مرحله ۴ (تشکیل مثلث‌بندی TIN) اجرا شود.")

    params = params or {}
    max_edge_param = params.get("max_edge_length", 10.0)
    max_edge_length: float | None = (
        float(max_edge_param)
        if max_edge_param is not None and float(max_edge_param) > 0
        else None
    )
    min_angle_deg = float(params.get("min_angle_deg", 0.0))
    use_boundary_polygon = bool(params.get("use_boundary_polygon", True))

    verts = state.tin_vertices_local
    tris = state.tin_triangles

    max_edges, min_angles, plan_areas, areas_3d = _compute_triangle_geometry(
        verts, tris
    )

    mask = np.ones((len(tris),), dtype=bool)
    removed_by_edge = 0
    removed_by_angle = 0
    removed_by_boundary = 0

    if max_edge_length is not None:
        edge_ok = max_edges <= max_edge_length
        removed_by_edge = int(np.sum(~edge_ok))
        mask &= edge_ok

    if min_angle_deg > 0.0:
        angle_ok = min_angles >= min_angle_deg
        removed_by_angle = int(np.sum(mask & ~angle_ok))
        mask &= angle_ok

    # Optional boundary polygon + holes filtering via Shapely
    boundary_coords = params.get("boundary_local") or state.boundary_codes_polygon_local
    holes_coords = (
        params.get("holes_local") if "holes_local" in params else state.holes_local
    )

    if use_boundary_polygon and (boundary_coords or holes_coords):
        # Compute centroids of triangles
        centroids_x = (
            verts[tris[:, 0], 0] + verts[tris[:, 1], 0] + verts[tris[:, 2], 0]
        ) / 3.0
        centroids_y = (
            verts[tris[:, 0], 1] + verts[tris[:, 1], 1] + verts[tris[:, 2], 1]
        ) / 3.0

        poly_shell: Polygon | None = None
        if boundary_coords and len(boundary_coords) >= 3:
            poly_shell = Polygon(boundary_coords, holes=holes_coords or [])
            if not poly_shell.is_valid:
                poly_shell = poly_shell.buffer(0)
        hole_polys: list[Polygon] = []
        if not poly_shell and holes_coords:
            for h in holes_coords:
                if len(h) >= 3:
                    hp = Polygon(h)
                    if not hp.is_valid:
                        hp = hp.buffer(0)
                    hole_polys.append(hp)

        boundary_ok = np.ones((len(tris),), dtype=bool)
        for idx in range(len(tris)):
            if not mask[idx]:
                continue
            pt = Point(float(centroids_x[idx]), float(centroids_y[idx]))
            if (
                poly_shell is not None
                and not poly_shell.contains(pt)
                or hole_polys
                and any(hp.contains(pt) for hp in hole_polys)
            ):
                boundary_ok[idx] = False

        removed_by_boundary = int(np.sum(mask & ~boundary_ok))
        mask &= boundary_ok

    filtered_tris = tris[mask]
    if len(filtered_tris) == 0:
        raise ValueError(
            "با پارامترهای فیلتر فعلی تمام مثلث‌ها حذف شدند. لطفاً حداکثر طول ضلع را افزایش دهید."
        )

    unfiltered_plan_area = float(np.sum(plan_areas))
    unfiltered_3d_area = float(np.sum(areas_3d))
    filtered_plan_area = float(np.sum(plan_areas[mask]))
    filtered_3d_area = float(np.sum(areas_3d[mask]))

    derived_boundary = (
        list(boundary_coords)
        if boundary_coords
        else _extract_outer_boundary_from_triangles(verts, filtered_tris)
    )

    filter_params_used = {
        "max_edge_length": max_edge_length,
        "min_angle_deg": min_angle_deg,
        "use_boundary_polygon": use_boundary_polygon,
    }

    stats: dict[str, Any] = {
        "step": 5,
        "total_triangles_before": len(tris),
        "active_triangles_after": len(filtered_tris),
        "removed_triangles_total": int(len(tris) - len(filtered_tris)),
        "removed_by_max_edge": removed_by_edge,
        "removed_by_min_angle": removed_by_angle,
        "removed_by_boundary": removed_by_boundary,
        "unfiltered_plan_area_m2": round(unfiltered_plan_area, 3),
        "unfiltered_surface_area_3d_m2": round(unfiltered_3d_area, 3),
        "filtered_plan_area_m2": round(filtered_plan_area, 3),
        "filtered_surface_area_3d_m2": round(filtered_3d_area, 3),
        "area_reduction_pct": round(
            100.0 * (1.0 - filtered_plan_area / max(unfiltered_plan_area, 1e-9)), 2
        ),
        "edge_slider_bounds_m": {
            "min": round(float(np.min(max_edges)), 2),
            "p50": round(float(np.median(max_edges)), 2),
            "p90": round(float(np.percentile(max_edges, 90)), 2),
            "max": round(float(np.max(max_edges)), 2),
        },
        "params": filter_params_used,
    }

    new_step_stats = {k: v for k, v in state.step_stats.items() if k <= 4}
    new_step_stats[5] = stats
    completed = [s for s in state.completed_steps if s < 5] + [5]

    new_state = replace(
        state,
        filtered_triangles=filtered_tris,
        triangle_mask=mask,
        filter_params=filter_params_used,
        boundary_polygon_local=derived_boundary,
        completed_steps=completed,
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=5)
    return (new_state, stats, viewer_payload)
