"""Step 6 (`contour.py`): Contour extraction on filtered TIN and slope analysis.

Reuses TopoConvert's path-splitting and midpoint placement utilities (`topoconvert.core.contours`
and `topoconvert.core.kml_contours`) while tracing contours directly across the filtered TIN
triangles so contours strictly respect filtered boundaries, holes, and breaklines.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np

from survey_core.io import build_viewer_payload_from_state
from survey_core.models import ContourLine, SurveyState
from topoconvert.core.contours import _split_path_on_jumps
from topoconvert.core.kml_contours import _midpoint_xy


def _trace_level_segments_on_tin(
    verts_xyz: np.ndarray,
    triangles: np.ndarray,
    z_level: float,
    tri_z_min: np.ndarray | None = None,
    tri_z_max: np.ndarray | None = None,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Extract linear iso-elevation segments across TIN triangles at local height `z_level`."""
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    # Small perturbation avoids exact vertex degeneracy
    eps = 1e-9

    if tri_z_min is not None and tri_z_max is not None:
        cross_mask = (tri_z_min - eps <= z_level) & (z_level <= tri_z_max + eps)
        candidate_tris = triangles[cross_mask]
    else:
        candidate_tris = triangles

    for tri in candidate_tris:
        p0 = verts_xyz[tri[0]]
        p1 = verts_xyz[tri[1]]
        p2 = verts_xyz[tri[2]]

        z0 = float(p0[2])
        z1 = float(p1[2])
        z2 = float(p2[2])

        if abs(z0 - z_level) < eps:
            z0 += eps
        if abs(z1 - z_level) < eps:
            z1 += eps
        if abs(z2 - z_level) < eps:
            z2 += eps

        z_min = min(z0, z1, z2)
        z_max = max(z0, z1, z2)
        if not (z_min < z_level < z_max):
            continue

        pts_cross: list[tuple[float, float]] = []
        edges = [
            (p0, z0, p1, z1),
            (p1, z1, p2, z2),
            (p2, z2, p0, z0),
        ]
        for pa, za, pb, zb in edges:
            if (za - z_level) * (zb - z_level) < 0.0:
                t = (z_level - za) / (zb - za)
                ix = float(pa[0] + t * (pb[0] - pa[0]))
                iy = float(pa[1] + t * (pb[1] - pa[1]))
                pts_cross.append((ix, iy))

        if len(pts_cross) == 2 and (
            math.hypot(
                pts_cross[1][0] - pts_cross[0][0], pts_cross[1][1] - pts_cross[0][1]
            )
            > 1e-6
        ):
            segments.append((pts_cross[0], pts_cross[1]))

    return segments


def _stitch_segments(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
    snap_decimals: int = 4,
) -> list[list[tuple[float, float]]]:
    """Stitch unordered 2-point contour segments into continuous polylines."""
    if not segments:
        return []

    def _key(pt: tuple[float, float]) -> tuple[int, int]:
        scale = 10**snap_decimals
        return (round(pt[0] * scale), round(pt[1] * scale))

    adj: dict[tuple[int, int], list[int]] = {}
    seg_endpoints: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for idx, (p_start, p_end) in enumerate(segments):
        ka = _key(p_start)
        kb = _key(p_end)
        seg_endpoints.append((ka, kb))
        adj.setdefault(ka, []).append(idx)
        adj.setdefault(kb, []).append(idx)

    visited = [False] * len(segments)
    polylines: list[list[tuple[float, float]]] = []

    for start_idx in range(len(segments)):
        if visited[start_idx]:
            continue
        visited[start_idx] = True
        p0, p1 = segments[start_idx]
        chain: list[tuple[float, float]] = [p0, p1]
        k_head = seg_endpoints[start_idx][0]
        k_tail = seg_endpoints[start_idx][1]

        # Grow forward from k_tail
        while True:
            candidates = [i for i in adj.get(k_tail, []) if not visited[i]]
            if not candidates:
                break
            nxt = candidates[0]
            visited[nxt] = True
            ka, kb = seg_endpoints[nxt]
            sa, sb = segments[nxt]
            if ka == k_tail:
                chain.append(sb)
                k_tail = kb
            else:
                chain.append(sa)
                k_tail = ka

        # Grow backward from k_head
        while True:
            candidates = [i for i in adj.get(k_head, []) if not visited[i]]
            if not candidates:
                break
            nxt = candidates[0]
            visited[nxt] = True
            ka, kb = seg_endpoints[nxt]
            sa, sb = segments[nxt]
            if kb == k_head:
                chain.insert(0, sa)
                k_head = ka
            else:
                chain.insert(0, sb)
                k_head = kb

        if len(chain) >= 2:
            polylines.append(chain)

    return polylines


def _compute_label_placement(
    points_xy: list[tuple[float, float]],
) -> tuple[float, float, float] | None:
    """Compute label (x, y, angle_deg) at the length-weighted midpoint of a contour."""
    if len(points_xy) < 2:
        return None
    total_len = sum(
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(points_xy[:-1], points_xy[1:])
    )
    if total_len < 1.5:
        return None
    mx, my = _midpoint_xy(points_xy)
    # Estimate tangent angle near midpoint
    mid_idx = max(0, min(len(points_xy) - 2, len(points_xy) // 2))
    dx = points_xy[mid_idx + 1][0] - points_xy[mid_idx][0]
    dy = points_xy[mid_idx + 1][1] - points_xy[mid_idx][1]
    angle_deg = math.degrees(math.atan2(dy, dx))
    if angle_deg > 90.0:
        angle_deg -= 180.0
    elif angle_deg < -90.0:
        angle_deg += 180.0
    return (mx, my, angle_deg)


def _compute_triangle_slopes(
    verts_xyz: np.ndarray, triangles: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Compute slope in degrees and percent for each triangle from its 3D surface normal."""
    if len(triangles) == 0:
        empty = np.zeros((0,), dtype=np.float64)
        return (empty, empty)

    p0 = verts_xyz[triangles[:, 0]]
    p1 = verts_xyz[triangles[:, 1]]
    p2 = verts_xyz[triangles[:, 2]]
    ab = p1 - p0
    ac = p2 - p0
    cross = np.cross(ab, ac)
    norms = np.linalg.norm(cross, axis=1)
    nz = np.abs(cross[:, 2])
    cos_theta = np.clip(np.where(norms > 1e-12, nz / norms, 1.0), 1e-6, 1.0)
    slopes_rad = np.arccos(cos_theta)
    slopes_deg = np.degrees(slopes_rad)
    slopes_pct = np.tan(slopes_rad) * 100.0
    return (slopes_deg, slopes_pct)


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 6: Generate labeled minor/major contours on filtered TIN and compute slopes.

    Parameters in `params`:
        interval (float): Minor contour interval in meters (default: 0.2 m).
        major_multiplier (int): Every Nth contour is a major contour (default: 5).
        add_labels (bool): Compute elevation labels for contours (default: True).
        compute_slope_heatmap (bool): Include slope data for heatmap visualization (default: True).
    """
    verts = state.tin_vertices_local
    tris = (
        state.filtered_triangles
        if len(state.filtered_triangles) > 0
        else state.tin_triangles
    )
    if len(verts) == 0 or len(tris) == 0:
        raise ValueError("ابتدا باید مثلث‌بندی و فیلتر TIN اجرا شود.")

    params = params or {}
    # Pick smart default interval based on elevation span if not provided
    z_min_global = float(np.min(verts[:, 2])) + state.origin.z0
    z_max_global = float(np.max(verts[:, 2])) + state.origin.z0
    z_span = max(z_max_global - z_min_global, 1e-6)

    default_interval = 0.2 if z_span <= 5.0 else (0.5 if z_span <= 20.0 else 2.0)
    interval = float(params.get("interval", default_interval))
    if interval <= 0:
        raise ValueError("فاصله منحنی میزان باید بزرگ‌تر از صفر باشد.")

    major_multiplier = max(2, int(params.get("major_multiplier", 5)))
    add_labels = bool(params.get("add_labels", True))
    compute_slope_heatmap = bool(params.get("compute_slope_heatmap", True))

    # Determine contour levels in global elevation
    first_level = math.ceil(z_min_global / interval) * interval
    last_level = math.floor(z_max_global / interval) * interval

    if last_level >= first_level - 1e-9:
        n_steps = round((last_level - first_level) / interval) + 1
        levels_global = [
            round(first_level + i * interval, 6) for i in range(max(0, n_steps))
        ]
    else:
        levels_global = [round((z_min_global + z_max_global) / 2.0, 6)]

    # Cap max number of levels to avoid runaway if user passes tiny interval on tall mountain
    if len(levels_global) > 250:
        step_skip = math.ceil(len(levels_global) / 250.0)
        levels_global = levels_global[::step_skip]

    # Estimate max gap for path splitting
    x_span = float(np.max(verts[:, 0]) - np.min(verts[:, 0]))
    y_span = float(np.max(verts[:, 1]) - np.min(verts[:, 1]))
    max_gap = max(math.hypot(x_span, y_span) * 0.25, 25.0)

    contours: list[ContourLine] = []
    major_count = 0
    minor_count = 0

    # Precompute per-triangle Z min/max once for fast vectorized filtering
    tz0 = verts[tris[:, 0], 2]
    tz1 = verts[tris[:, 1], 2]
    tz2 = verts[tris[:, 2], 2]
    tri_z_min = np.minimum(np.minimum(tz0, tz1), tz2)
    tri_z_max = np.maximum(np.maximum(tz0, tz1), tz2)

    for elev_global in levels_global:
        z_loc = elev_global - state.origin.z0
        level_index = round(elev_global / interval)
        is_major = (level_index % major_multiplier) == 0

        segs = _trace_level_segments_on_tin(verts, tris, z_loc, tri_z_min, tri_z_max)
        polylines = _stitch_segments(segs)
        for poly in polylines:
            subpaths = _split_path_on_jumps(poly, max_gap)
            for sp in subpaths:
                if len(sp) < 2:
                    continue
                lbl = _compute_label_placement(sp) if add_labels else None
                contours.append(
                    ContourLine(
                        elevation=elev_global,
                        z_local=z_loc,
                        is_major=is_major,
                        points_local=sp,
                        label_pos_local=lbl,
                    )
                )
                if is_major:
                    major_count += 1
                else:
                    minor_count += 1

    slopes_deg, slopes_pct = _compute_triangle_slopes(verts, tris)

    slope_summary = {
        "min_deg": round(float(np.min(slopes_deg)) if len(slopes_deg) else 0.0, 2),
        "mean_deg": round(float(np.mean(slopes_deg)) if len(slopes_deg) else 0.0, 2),
        "max_deg": round(float(np.max(slopes_deg)) if len(slopes_deg) else 0.0, 2),
        "min_pct": round(float(np.min(slopes_pct)) if len(slopes_pct) else 0.0, 2),
        "mean_pct": round(float(np.mean(slopes_pct)) if len(slopes_pct) else 0.0, 2),
        "max_pct": round(float(np.max(slopes_pct)) if len(slopes_pct) else 0.0, 2),
    }

    slope_grid_data: dict[str, Any] | None = None
    if compute_slope_heatmap and len(slopes_deg) > 0:
        slope_grid_data = {
            "enabled": True,
            "triangle_slopes_deg": np.round(slopes_deg, 2).tolist(),
            "triangle_slopes_pct": np.round(slopes_pct, 2).tolist(),
            "summary": slope_summary,
        }

    contour_params_used = {
        "interval": interval,
        "major_multiplier": major_multiplier,
        "add_labels": add_labels,
        "compute_slope_heatmap": compute_slope_heatmap,
    }

    stats: dict[str, Any] = {
        "step": 6,
        "interval_m": interval,
        "major_interval_m": round(interval * major_multiplier, 4),
        "major_multiplier": major_multiplier,
        "elevation_levels_count": len(levels_global),
        "total_contour_polylines": len(contours),
        "major_contour_count": major_count,
        "minor_contour_count": minor_count,
        "elevation_range_m": [round(z_min_global, 3), round(z_max_global, 3)],
        "slope_summary": slope_summary,
        "params": contour_params_used,
    }

    new_step_stats = {k: v for k, v in state.step_stats.items() if k <= 5}
    new_step_stats[6] = stats
    completed = [s for s in state.completed_steps if s < 6] + [6]

    new_state = replace(
        state,
        contours=contours,
        contour_params=contour_params_used,
        triangle_slopes_deg=slopes_deg,
        triangle_slopes_pct=slopes_pct,
        slope_grid_data=slope_grid_data,
        completed_steps=completed,
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=6)
    return (new_state, stats, viewer_payload)
