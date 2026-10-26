"""Step 7 (`metrics.py`): Engineering surface metrics, prism volumes, per-layer breakdown, and longitudinal profile."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np

from survey_core.contour import _compute_triangle_slopes
from survey_core.filt import _compute_triangle_geometry
from survey_core.io import build_viewer_payload_from_state
from survey_core.models import SurveyState


def _polyline_length_2d(pts: list[tuple[float, float]] | list[list[float]]) -> float:
    """Compute 2D polyline length in meters."""
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        total += math.hypot(
            float(pts[i + 1][0]) - float(pts[i][0]),
            float(pts[i + 1][1]) - float(pts[i][1]),
        )
    return total


def _compute_longitudinal_profile(
    verts_xyz: np.ndarray,
    origin_e0: float,
    origin_n0: float,
    origin_z0: float,
    num_bins: int = 35,
) -> dict[str, Any]:
    """Compute longitudinal profile along the principal axis / corridor centerline of the survey."""
    if len(verts_xyz) < 2:
        return {"stations": [], "path_length_m": 0.0, "straight_span_m": 0.0}

    xy = verts_xyz[:, :2]
    z_global = verts_xyz[:, 2] + origin_z0

    # Principal component (SVD) gives the primary survey corridor axis
    center = np.mean(xy, axis=0)
    centered = xy - center
    cov = np.cov(centered.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    principal_dir = eigvecs[:, int(np.argmax(eigvals))]

    # Orient axis from first survey point toward last survey point
    delta_first_last = xy[-1] - xy[0]
    if float(np.dot(delta_first_last, principal_dir)) < 0.0:
        principal_dir = -principal_dir

    proj_s = centered @ principal_dir
    s_min = float(np.min(proj_s))
    s_max = float(np.max(proj_s))
    s_shifted = proj_s - s_min

    # Bin points along corridor stations to build a smooth centerline path and elevation profile
    n_bins = min(max(10, num_bins), max(10, len(verts_xyz) // 3))
    bin_edges = np.linspace(
        0.0, max(s_shifted[-1], float(np.max(s_shifted)), 1e-6), n_bins + 1
    )

    stations: list[dict[str, Any]] = []
    centerline_pts: list[tuple[float, float, float]] = []

    for b in range(n_bins):
        low = bin_edges[b]
        high = bin_edges[b + 1]
        if b == n_bins - 1:
            in_bin = (s_shifted >= low) & (s_shifted <= high + 1e-9)
        else:
            in_bin = (s_shifted >= low) & (s_shifted < high)

        if not np.any(in_bin):
            continue

        cx = float(np.mean(xy[in_bin, 0]))
        cy = float(np.mean(xy[in_bin, 1]))
        cz_mean = float(np.mean(z_global[in_bin]))
        cz_min = float(np.min(z_global[in_bin]))
        cz_max = float(np.max(z_global[in_bin]))
        centerline_pts.append((cx, cy, cz_mean))
        stations.append(
            {
                "x_local": round(cx, 3),
                "y_local": round(cy, 3),
                "easting": round(cx + origin_e0, 3),
                "northing": round(cy + origin_n0, 3),
                "z_mean": round(cz_mean, 3),
                "z_min": round(cz_min, 3),
                "z_max": round(cz_max, 3),
                "point_count": int(np.sum(in_bin)),
            }
        )

    # Calculate cumulative path distance along centerline stations
    cum_dist = 0.0
    for idx, st in enumerate(stations):
        if idx > 0:
            prev = stations[idx - 1]
            step_d = math.hypot(
                st["x_local"] - prev["x_local"], st["y_local"] - prev["y_local"]
            )
            cum_dist += step_d
        st["distance_m"] = round(cum_dist, 3)

    return {
        "stations": stations,
        "path_length_m": round(cum_dist, 3),
        "straight_span_m": round(s_max - s_min, 3),
        "centerline_local": [
            [st["x_local"], st["y_local"], round(st["z_mean"] - origin_z0, 3)]
            for st in stations
        ],
    }


def _compute_code_and_layer_breakdown(
    state: SurveyState,
    verts: np.ndarray,
    filt_tris: np.ndarray,
    filt_plan_areas: np.ndarray,
    filt_3d_areas: np.ndarray,
    prism_vols: np.ndarray,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute per-code (survey layer) volume/area breakdown and CAD layer summary."""
    active_pts = state.active_points or state.cleaned_points or state.raw_points
    origin_z0 = state.origin.z0

    # Map each vertex index to its survey code (vertices 0..len(active_pts)-1 correspond to active_pts;
    # any densified breakline vertices inherit the nearest/breakline code)
    n_verts = len(verts)
    vert_codes: list[str] = []
    default_code = active_pts[0].code if active_pts else "DEFAULT"
    for vi in range(n_verts):
        if vi < len(active_pts):
            vert_codes.append(active_pts[vi].code)
        else:
            vert_codes.append(default_code)

    # Accumulate 1/3 of each triangle's plan area, 3D area, cut, fill, and net volume to each of its 3 vertex codes
    code_plan_area: dict[str, float] = {}
    code_3d_area: dict[str, float] = {}
    code_vol_net: dict[str, float] = {}
    code_vol_cut: dict[str, float] = {}
    code_vol_fill: dict[str, float] = {}
    code_tri_touch: dict[str, int] = {}

    for ti in range(len(filt_tris)):
        t = filt_tris[ti]
        pa_third = float(filt_plan_areas[ti]) / 3.0
        a3_third = float(filt_3d_areas[ti]) / 3.0
        vol_val = float(prism_vols[ti])
        vn_third = vol_val / 3.0
        vc_third = (vol_val / 3.0) if vol_val > 0.0 else 0.0
        vf_third = (abs(vol_val) / 3.0) if vol_val < 0.0 else 0.0

        touched_codes_in_tri: set[str] = set()
        for corner in range(3):
            v_idx = int(t[corner])
            c_name = vert_codes[v_idx] if 0 <= v_idx < n_verts else default_code
            code_plan_area[c_name] = code_plan_area.get(c_name, 0.0) + pa_third
            code_3d_area[c_name] = code_3d_area.get(c_name, 0.0) + a3_third
            code_vol_net[c_name] = code_vol_net.get(c_name, 0.0) + vn_third
            code_vol_cut[c_name] = code_vol_cut.get(c_name, 0.0) + vc_third
            code_vol_fill[c_name] = code_vol_fill.get(c_name, 0.0) + vf_third
            touched_codes_in_tri.add(c_name)

        for c_name in touched_codes_in_tri:
            code_tri_touch[c_name] = code_tri_touch.get(c_name, 0) + 1

    # Group point elevations by code
    pts_by_code: dict[str, list[float]] = {}
    for p in state.cleaned_points or state.raw_points:
        pts_by_code.setdefault(p.code, []).append(p.z_local + origin_z0)

    code_breakdown: list[dict[str, Any]] = []
    all_codes = list(state.code_configs.keys()) or list(pts_by_code.keys())
    for code in all_codes:
        cfg = state.code_configs.get(code)
        zs = pts_by_code.get(code, [])
        z_min_c = round(min(zs), 3) if zs else 0.0
        z_max_c = round(max(zs), 3) if zs else 0.0
        z_mean_c = round(sum(zs) / len(zs), 3) if zs else 0.0
        safe_code = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in code)
        code_breakdown.append(
            {
                "code": code,
                "dxf_layer": f"CODE_{safe_code}",
                "role": cfg.role if cfg else "point",
                "color": cfg.color if cfg else "#38bdf8",
                "point_count": len(zs),
                "triangle_count": int(code_tri_touch.get(code, 0)),
                "plan_area_m2": round(code_plan_area.get(code, 0.0), 2),
                "surface_area_3d_m2": round(code_3d_area.get(code, 0.0), 2),
                "volume_net_m3": round(code_vol_net.get(code, 0.0), 2),
                "volume_cut_m3": round(code_vol_cut.get(code, 0.0), 2),
                "volume_fill_m3": round(code_vol_fill.get(code, 0.0), 2),
                "z_min": z_min_c,
                "z_mean": z_mean_c,
                "z_max": z_max_c,
            }
        )

    # Compute CAD layer summary
    major_contours = [c for c in state.contours if c.is_major]
    minor_contours = [c for c in state.contours if not c.is_major]
    major_len = sum(_polyline_length_2d(c.points_local) for c in major_contours)
    minor_len = sum(_polyline_length_2d(c.points_local) for c in minor_contours)
    bl_len = sum(
        _polyline_length_2d(bl.get("coords", [])) for bl in state.breaklines_local
    )
    boundary_loc = state.boundary_polygon_local or state.boundary_codes_polygon_local
    bnd_len = _polyline_length_2d(boundary_loc) if boundary_loc else 0.0

    layer_breakdown: list[dict[str, Any]] = [
        {
            "layer": "POINTS",
            "title_fa": "نقاط برداشت (POINTS)",
            "entity_type": "POINT",
            "count": len(active_pts),
            "length_m": 0.0,
            "area_m2": 0.0,
            "volume_m3": 0.0,
        },
        {
            "layer": "PT_NO / PT_ELEV",
            "title_fa": "برچسب شماره و کد ارتفاعی نقاط",
            "entity_type": "TEXT",
            "count": len(active_pts) * 2,
            "length_m": 0.0,
            "area_m2": 0.0,
            "volume_m3": 0.0,
        },
        {
            "layer": "TIN",
            "title_fa": "شبکه مثلثی سطح (TIN 3DFACE)",
            "entity_type": "3DFACE",
            "count": len(filt_tris),
            "length_m": 0.0,
            "area_m2": round(float(np.sum(filt_plan_areas)), 2),
            "volume_m3": round(float(np.sum(prism_vols)), 2),
        },
        {
            "layer": "CONTOUR_MAJOR",
            "title_fa": "منحنی‌های میزان اصلی (Major)",
            "entity_type": "POLYLINE3D",
            "count": len(major_contours),
            "length_m": round(major_len, 1),
            "area_m2": 0.0,
            "volume_m3": 0.0,
        },
        {
            "layer": "CONTOUR_MINOR",
            "title_fa": "منحنی‌های میزان فرعی (Minor)",
            "entity_type": "POLYLINE3D",
            "count": len(minor_contours),
            "length_m": round(minor_len, 1),
            "area_m2": 0.0,
            "volume_m3": 0.0,
        },
        {
            "layer": "BREAKLINES",
            "title_fa": "خطوط شکست (Breaklines)",
            "entity_type": "POLYLINE3D",
            "count": len(state.breaklines_local),
            "length_m": round(bl_len, 1),
            "area_m2": 0.0,
            "volume_m3": 0.0,
        },
        {
            "layer": "BOUNDARY",
            "title_fa": "مرز محدوده (Boundary)",
            "entity_type": "POLYLINE3D",
            "count": 1 if boundary_loc and len(boundary_loc) >= 3 else 0,
            "length_m": round(bnd_len, 1),
            "area_m2": round(float(np.sum(filt_plan_areas)), 2),
            "volume_m3": 0.0,
        },
    ]

    return (code_breakdown, layer_breakdown)


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 7: Compute comprehensive planimetric/3D areas, prism volumes, slopes, and profile.

    Parameters in `params`:
        reference_elevation (float | None): Reference Z (global meters) for prism volume calculation.
            Defaults to minimum elevation of active points (`origin.z0`).
    """
    verts = state.tin_vertices_local
    all_tris = state.tin_triangles
    filt_tris = (
        state.filtered_triangles
        if len(state.filtered_triangles) > 0
        else state.tin_triangles
    )

    if len(verts) == 0 or len(filt_tris) == 0:
        raise ValueError("ابتدا باید مثلث‌بندی TIN تشکیل شود.")

    params = params or {}
    z_global_verts = verts[:, 2] + state.origin.z0
    min_z = float(np.min(z_global_verts))
    max_z = float(np.max(z_global_verts))
    mean_z = float(np.mean(z_global_verts))
    median_z = float(np.median(z_global_verts))
    std_z = float(np.std(z_global_verts))

    ref_elev_param = params.get("reference_elevation")
    reference_elevation = float(ref_elev_param) if ref_elev_param is not None else min_z
    ref_z_local = reference_elevation - state.origin.z0

    # Unfiltered TIN geometry
    _, _, unfilt_plan_areas, unfilt_3d_areas = _compute_triangle_geometry(
        verts, all_tris
    )
    unfiltered_plan_area = float(np.sum(unfilt_plan_areas))
    unfiltered_3d_area = float(np.sum(unfilt_3d_areas))

    # Filtered TIN geometry
    _max_edges, _min_angles, filt_plan_areas, filt_3d_areas = (
        _compute_triangle_geometry(verts, filt_tris)
    )
    filtered_plan_area = float(np.sum(filt_plan_areas))
    filtered_3d_area = float(np.sum(filt_3d_areas))

    # Prism volume vs reference elevation across filtered triangles:
    # V_i = A_plan_i * ((z0 + z1 + z2)/3 - z_ref)
    tri_mean_z_local = (
        verts[filt_tris[:, 0], 2]
        + verts[filt_tris[:, 1], 2]
        + verts[filt_tris[:, 2], 2]
    ) / 3.0
    dz_rel = tri_mean_z_local - ref_z_local
    prism_vols = filt_plan_areas * dz_rel
    net_volume_m3 = float(np.sum(prism_vols))
    cut_volume_m3 = float(np.sum(prism_vols[prism_vols > 0.0]))
    fill_volume_m3 = float(np.abs(np.sum(prism_vols[prism_vols < 0.0])))

    # Slopes on filtered triangles
    slopes_deg, slopes_pct = _compute_triangle_slopes(verts, filt_tris)
    if len(slopes_deg) > 0 and filtered_plan_area > 1e-9:
        mean_slope_deg = float(
            np.sum(slopes_deg * filt_plan_areas) / filtered_plan_area
        )
        mean_slope_pct = float(
            np.sum(slopes_pct * filt_plan_areas) / filtered_plan_area
        )
        max_slope_deg = float(np.max(slopes_deg))
        max_slope_pct = float(np.max(slopes_pct))
        min_slope_deg = float(np.min(slopes_deg))
    else:
        mean_slope_deg = 0.0
        mean_slope_pct = 0.0
        max_slope_deg = 0.0
        max_slope_pct = 0.0
        min_slope_deg = 0.0

    profile_data = _compute_longitudinal_profile(
        verts, state.origin.e0, state.origin.n0, state.origin.z0
    )

    code_breakdown, layer_breakdown = _compute_code_and_layer_breakdown(
        state, verts, filt_tris, filt_plan_areas, filt_3d_areas, prism_vols
    )

    # Physical interpretation note explaining unfiltered vs filtered narrow-strip triangulation
    area_ratio = unfiltered_plan_area / max(filtered_plan_area, 1e-6)
    strip_explanation = (
        f"مساحت افقی مثلث‌بندی خام دلونی برابر {unfiltered_plan_area:.2f} مترمربع و مساحت سه‌بعدی آن "
        f"{unfiltered_3d_area:.2f} مترمربع است. از آنجا که نقاط برداشت‌شده در یک نوار طولی باریک "
        f"(به طول تقریبی {profile_data['path_length_m']:.1f} متر) با انحنا قرار گرفته‌اند، پوسته محدب دلونی خام "
        f"مثلث‌های کشیده و کاذب در فضای بیرون از مسیر ایجاد می‌کند. با اعمال فیلتر حداکثر طول ضلع "
        f"({state.filter_params.get('max_edge_length', 10.0)} متر)، مثلث‌های کاذب مرزی حذف شده و مساحت افقی واقعی "
        f"محدوده برداشت به {filtered_plan_area:.2f} مترمربع (و مساحت سه‌بعدی به {filtered_3d_area:.2f} مترمربع) می‌رسد."
    )

    metrics: dict[str, Any] = {
        "step": 7,
        "point_count_raw": len(state.raw_points),
        "point_count_cleaned": len(state.cleaned_points),
        "point_count_active": len(state.active_points),
        "triangle_count_unfiltered": len(all_tris),
        "triangle_count_filtered": len(filt_tris),
        "planimetric_area_m2": round(filtered_plan_area, 3),
        "surface_area_3d_m2": round(filtered_3d_area, 3),
        "unfiltered_planimetric_area_m2": round(unfiltered_plan_area, 3),
        "unfiltered_surface_area_3d_m2": round(unfiltered_3d_area, 3),
        "surface_to_plan_ratio": round(
            filtered_3d_area / max(filtered_plan_area, 1e-9), 5
        ),
        "reference_elevation_m": round(reference_elevation, 3),
        "prism_volume_net_m3": round(net_volume_m3, 3),
        "prism_volume_cut_m3": round(cut_volume_m3, 3),
        "prism_volume_fill_m3": round(fill_volume_m3, 3),
        "elevation_m": {
            "min": round(min_z, 3),
            "max": round(max_z, 3),
            "mean": round(mean_z, 3),
            "median": round(median_z, 3),
            "std": round(std_z, 3),
            "range": round(max_z - min_z, 3),
        },
        "slope": {
            "min_deg": round(min_slope_deg, 2),
            "mean_deg": round(mean_slope_deg, 2),
            "max_deg": round(max_slope_deg, 2),
            "mean_pct": round(mean_slope_pct, 2),
            "max_pct": round(max_slope_pct, 2),
        },
        "path_length_m": profile_data["path_length_m"],
        "straight_span_m": profile_data["straight_span_m"],
        "contour_count": len(state.contours),
        "code_breakdown": code_breakdown,
        "layer_breakdown": layer_breakdown,
        "strip_geometry_explanation": strip_explanation,
        "area_inflation_factor_unfiltered": round(area_ratio, 2),
    }

    new_step_stats = dict(state.step_stats)
    new_step_stats[7] = metrics
    completed = [s for s in state.completed_steps if s < 7] + [7]

    new_state = replace(
        state,
        metrics=metrics,
        profile_data=profile_data,
        completed_steps=completed,
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=7)
    return (new_state, metrics, viewer_payload)
