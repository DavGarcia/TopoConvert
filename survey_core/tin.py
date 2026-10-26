"""Step 4 (`tin.py`): Delaunay TIN generation and constrained breakline enforcement.

License note on external triangulation libraries:
- `triangle` (PyPI) wraps Jonathan Shewchuk's Triangle C library and is distributed under
  LGPL-3.0 with non-commercial clauses in the underlying C source, which is incompatible
  with strict MIT-only licensing.
- `civpy` is not available on PyPI.
- Therefore, `survey_core/tin.py` uses `scipy.spatial.Delaunay` (BSD-3-Clause, MIT-compatible)
  combined with Sloan's constrained Delaunay edge-flipping algorithm and `civpy`-style
  breakline densification so breaklines are strictly honored as triangle edges.
"""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from typing import Any

import numpy as np
from scipy.spatial import Delaunay

from survey_core.io import build_viewer_payload_from_state
from survey_core.models import SurveyState


def _ccw(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Signed 2D area * 2 of triangle (a, b, c)."""
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _segments_properly_intersect(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray, eps: float = 1e-10
) -> bool:
    """Return True if segment AB and segment CD strictly intersect in their interiors."""
    # Bounding box quick reject
    if (
        max(a[0], b[0]) < min(c[0], d[0]) - eps
        or max(c[0], d[0]) < min(a[0], b[0]) - eps
        or max(a[1], b[1]) < min(c[1], d[1]) - eps
        or max(c[1], d[1]) < min(a[1], b[1]) - eps
    ):
        return False

    c1 = _ccw(a, b, c)
    c2 = _ccw(a, b, d)
    c3 = _ccw(c, d, a)
    c4 = _ccw(c, d, b)
    return (c1 * c2 < -eps) and (c3 * c4 < -eps)


def _orient_ccw(xy: np.ndarray, tri: list[int]) -> list[int]:
    """Ensure a triangle vertex list [i, j, k] is oriented counter-clockwise."""
    if _ccw(xy[tri[0]], xy[tri[1]], xy[tri[2]]) < 0.0:
        return [tri[0], tri[2], tri[1]]
    return tri


def _build_edge_map(tris: list[list[int]]) -> dict[tuple[int, int], list[int]]:
    """Map undirected edge (min_u, max_v) -> list of triangle indices sharing that edge."""
    edge_map: dict[tuple[int, int], list[int]] = {}
    for t_idx, t in enumerate(tris):
        for k in range(3):
            u, v = t[k], t[(k + 1) % 3]
            edge = (u, v) if u < v else (v, u)
            edge_map.setdefault(edge, []).append(t_idx)
    return edge_map


def _enforce_constrained_edges(
    xy: np.ndarray,
    simplices: np.ndarray,
    constrained_edges: list[tuple[int, int]],
) -> tuple[np.ndarray, int, int]:
    """Enforce constrained breakline edges in a 2D triangulation via Sloan edge flipping.

    Returns:
        (updated_simplices, enforced_count, flips_performed)
    """
    if not constrained_edges or len(simplices) == 0:
        return (simplices.astype(np.int32), 0, 0)

    tris: list[list[int]] = [_orient_ccw(xy, list(map(int, t))) for t in simplices]
    flips_performed = 0
    enforced_count = 0

    for u_raw, v_raw in constrained_edges:
        u, v = int(u_raw), int(v_raw)
        if u == v:
            continue
        target = (u, v) if u < v else (v, u)
        edge_map = _build_edge_map(tris)
        if target in edge_map:
            enforced_count += 1
            continue

        # Collect all interior edges that properly intersect segment (u, v)
        intersecting_queue: deque[tuple[int, int]] = deque()
        for edge, t_indices in edge_map.items():
            if (
                len(t_indices) == 2
                and u not in edge
                and v not in edge
                and _segments_properly_intersect(xy[u], xy[v], xy[edge[0]], xy[edge[1]])
            ):
                intersecting_queue.append(edge)

        max_attempts = max(len(intersecting_queue) * 6, 24)
        attempts = 0
        while intersecting_queue and attempts < max_attempts:
            attempts += 1
            edge = intersecting_queue.popleft()
            t_indices = edge_map.get(edge, [])
            if len(t_indices) != 2:
                continue

            t1_idx, t2_idx = t_indices[0], t_indices[1]
            t1, t2 = tris[t1_idx], tris[t2_idx]
            opp1_list = [x for x in t1 if x not in edge]
            opp2_list = [x for x in t2 if x not in edge]
            if len(opp1_list) != 1 or len(opp2_list) != 1:
                continue
            opp1, opp2 = opp1_list[0], opp2_list[0]

            # Check if quad (edge[0], opp1, edge[1], opp2) is strictly convex
            if _segments_properly_intersect(
                xy[edge[0]], xy[edge[1]], xy[opp1], xy[opp2]
            ):
                # Flip diagonal from (edge[0], edge[1]) to (opp1, opp2)
                tris[t1_idx] = _orient_ccw(xy, [opp1, opp2, edge[0]])
                tris[t2_idx] = _orient_ccw(xy, [opp1, opp2, edge[1]])
                flips_performed += 1
                edge_map = _build_edge_map(tris)

                new_diag = (opp1, opp2) if opp1 < opp2 else (opp2, opp1)
                if (
                    new_diag != target
                    and u not in new_diag
                    and v not in new_diag
                    and _segments_properly_intersect(
                        xy[u], xy[v], xy[new_diag[0]], xy[new_diag[1]]
                    )
                ):
                    intersecting_queue.append(new_diag)
            else:
                # Push back to try after adjacent edges flip
                intersecting_queue.append(edge)

        if target in _build_edge_map(tris):
            enforced_count += 1

    return (np.array(tris, dtype=np.int32), enforced_count, flips_performed)


def _densify_long_breaklines(
    vertices_xyz: np.ndarray,
    point_ids: list[str],
    point_codes: list[str],
    breaklines: list[dict[str, Any]],
    max_subsegment_len: float,
) -> tuple[np.ndarray, list[str], list[str], list[tuple[int, int]], int]:
    """Subdivide breakline segments longer than `max_subsegment_len` (`civpy` approach).

    Inserting Steiner points with linearly interpolated Z along breaklines ensures
    Delaunay circumcircles stay small around breaklines before Sloan edge flipping.
    """
    if not breaklines or max_subsegment_len <= 0:
        edges: list[tuple[int, int]] = []
        for bl in breaklines:
            v_idxs = bl.get("vertex_indices", [])
            for a, b in zip(v_idxs[:-1], v_idxs[1:]):
                if a != b:
                    edges.append((int(a), int(b)))
        return (vertices_xyz, list(point_ids), list(point_codes), edges, 0)

    verts_list = vertices_xyz.tolist()
    ids_list = list(point_ids)
    codes_list = list(point_codes)
    constrained_edges: list[tuple[int, int]] = []
    steiner_added = 0

    for bl in breaklines:
        v_idxs = bl.get("vertex_indices", [])
        code = bl.get("code", "BL")
        for a, b in zip(v_idxs[:-1], v_idxs[1:]):
            ia, ib = int(a), int(b)
            if ia == ib:
                continue
            pa = np.array(verts_list[ia], dtype=np.float64)
            pb = np.array(verts_list[ib], dtype=np.float64)
            dist_2d = float(np.hypot(pb[0] - pa[0], pb[1] - pa[1]))
            if (
                dist_2d > max_subsegment_len
                and int(np.ceil(dist_2d / max_subsegment_len)) > 1
            ):
                n_parts = min(int(np.ceil(dist_2d / max_subsegment_len)), 20)
                prev_idx = ia
                for step in range(1, n_parts):
                    t = step / float(n_parts)
                    interp = pa + t * (pb - pa)
                    new_idx = len(verts_list)
                    verts_list.append(
                        [float(interp[0]), float(interp[1]), float(interp[2])]
                    )
                    steiner_added += 1
                    ids_list.append(f"BL_{steiner_added}")
                    codes_list.append(code)
                    constrained_edges.append((prev_idx, new_idx))
                    prev_idx = new_idx
                constrained_edges.append((prev_idx, ib))
            else:
                constrained_edges.append((ia, ib))

    return (
        np.array(verts_list, dtype=np.float64),
        ids_list,
        codes_list,
        constrained_edges,
        steiner_added,
    )


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 4: Build 2D Delaunay TIN in local coordinates and enforce breaklines.

    Parameters in `params`:
        honor_breaklines (bool): Whether to enforce breakline edges in TIN (default: True).
        densify_breaklines (bool): Whether to subdivide long breaklines (`civpy` style, default: False).
        max_breakline_subsegment (float): Max subsegment length when densify_breaklines=True (default: 10.0 m).
    """
    active_pts = state.active_points or state.cleaned_points or state.raw_points
    if len(active_pts) < 3:
        raise ValueError("حداقل ۳ نقطه فعال برای مثلث‌بندی TIN نیاز است.")

    params = params or {}
    honor_breaklines = bool(params.get("honor_breaklines", True))
    densify_breaklines = bool(params.get("densify_breaklines", False))
    max_subseg = float(params.get("max_breakline_subsegment", 10.0))

    base_xyz = np.array(
        [[p.x_local, p.y_local, p.z_local] for p in active_pts], dtype=np.float64
    )
    base_ids = [p.id for p in active_pts]
    base_codes = [p.code for p in active_pts]

    steiner_added = 0
    constrained_edges: list[tuple[int, int]] = []
    if honor_breaklines and state.breaklines_local:
        if densify_breaklines:
            verts_xyz, pt_ids, pt_codes, constrained_edges, steiner_added = (
                _densify_long_breaklines(
                    base_xyz,
                    base_ids,
                    base_codes,
                    state.breaklines_local,
                    max_subseg,
                )
            )
        else:
            verts_xyz = base_xyz
            pt_ids = base_ids
            pt_codes = base_codes
            for bl in state.breaklines_local:
                v_idxs = bl.get("vertex_indices", [])
                for a, b in zip(v_idxs[:-1], v_idxs[1:]):
                    if a != b:
                        constrained_edges.append((int(a), int(b)))
    else:
        verts_xyz = base_xyz
        pt_ids = base_ids
        pt_codes = base_codes

    # Perform 2D Delaunay triangulation in local meter coordinates
    try:
        tri = Delaunay(verts_xyz[:, :2])
    except Exception as exc:
        raise ValueError(
            f"خطا در تشکیل مثلث‌بندی دلونی (نقاط هم‌خط یا تکراری): {exc}"
        ) from exc

    simplices = tri.simplices.astype(np.int32)
    # Vectorized CCW orientation of all triangles
    p0_xy = verts_xyz[simplices[:, 0], :2]
    p1_xy = verts_xyz[simplices[:, 1], :2]
    p2_xy = verts_xyz[simplices[:, 2], :2]
    cross_z = (p1_xy[:, 0] - p0_xy[:, 0]) * (p2_xy[:, 1] - p0_xy[:, 1]) - (
        p1_xy[:, 1] - p0_xy[:, 1]
    ) * (p2_xy[:, 0] - p0_xy[:, 0])
    cw_mask = cross_z < 0.0
    if np.any(cw_mask):
        c1 = simplices[cw_mask, 1].copy()
        simplices[cw_mask, 1] = simplices[cw_mask, 2]
        simplices[cw_mask, 2] = c1

    enforced_count = 0
    flips_performed = 0
    if honor_breaklines and constrained_edges:
        simplices, enforced_count, flips_performed = _enforce_constrained_edges(
            verts_xyz[:, :2], simplices, constrained_edges
        )
        tin_method = "scipy_constrained_breaklines"
        tin_method_note = (
            "مثلث‌بندی مقید با اعمال خطوط شکست (Sloan Edge-Flipping + رویکرد civpy بر پایه SciPy Delaunay؛ "
            "کتابخانه triangle به دلیل مجوز LGPL-3.0 / غیرتجاری برای حفظ سازگاری کامل با مجوز MIT کنار گذاشته شد)."
        )
    else:
        tin_method = "scipy_delaunay"
        tin_method_note = (
            "مثلث‌بندی دلونی استاندارد (SciPy Qhull Delaunay در مختصات محلی؛ "
            "کتابخانه triangle دارای مجوز LGPL-3.0 است و برای رعایت مجوز MIT از SciPy استفاده شده است)."
        )

    # Compute unfiltered areas and edge length statistics
    p0 = verts_xyz[simplices[:, 0]]
    p1 = verts_xyz[simplices[:, 1]]
    p2 = verts_xyz[simplices[:, 2]]
    ab = p1 - p0
    ac = p2 - p0
    bc = p2 - p1

    plan_areas = 0.5 * np.abs(ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0])
    areas_3d = 0.5 * np.linalg.norm(np.cross(ab, ac), axis=1)

    e01 = np.linalg.norm(ab[:, :2], axis=1)
    e02 = np.linalg.norm(ac[:, :2], axis=1)
    e12 = np.linalg.norm(bc[:, :2], axis=1)
    max_edges = np.maximum(np.maximum(e01, e02), e12)

    # Fast vectorized unique undirected edge count
    all_directed_edges = np.vstack(
        [simplices[:, [0, 1]], simplices[:, [1, 2]], simplices[:, [2, 0]]]
    )
    all_undirected_edges = np.sort(all_directed_edges, axis=1)
    edge_keys = all_undirected_edges[:, 0].astype(np.int64) * int(
        len(verts_xyz) + 1
    ) + all_undirected_edges[:, 1].astype(np.int64)
    unique_edge_count = len(np.unique(edge_keys))

    mask_all = np.ones((len(simplices),), dtype=bool)

    stats: dict[str, Any] = {
        "step": 4,
        "vertex_count": len(verts_xyz),
        "steiner_points_added": steiner_added,
        "triangle_count": len(simplices),
        "edge_count": unique_edge_count,
        "constrained_edge_target_count": len(constrained_edges),
        "constrained_edge_enforced_count": enforced_count,
        "edge_flips_performed": flips_performed,
        "unfiltered_plan_area_m2": round(float(np.sum(plan_areas)), 3),
        "unfiltered_surface_area_3d_m2": round(float(np.sum(areas_3d)), 3),
        "edge_length_stats_m": {
            "min": round(float(np.min(np.minimum(np.minimum(e01, e02), e12))), 3),
            "median": round(float(np.median(max_edges)), 3),
            "p90": round(float(np.percentile(max_edges, 90)), 3),
            "max": round(float(np.max(max_edges)), 3),
        },
        "method": tin_method,
        "method_note": tin_method_note,
    }

    new_step_stats = {k: v for k, v in state.step_stats.items() if k <= 3}
    new_step_stats[4] = stats
    completed = [s for s in state.completed_steps if s < 4] + [4]

    new_state = replace(
        state,
        tin_vertices_local=verts_xyz,
        tin_point_ids=pt_ids,
        tin_point_codes=pt_codes,
        tin_triangles=simplices,
        tin_method=tin_method,
        tin_method_note=tin_method_note,
        breakline_edges=constrained_edges,
        filtered_triangles=simplices,
        triangle_mask=mask_all,
        completed_steps=completed,
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=4)
    return (new_state, stats, viewer_payload)
