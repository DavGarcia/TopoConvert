"""Step 7 (`metrics.py`): Engineering surface metrics, prism volumes, and longitudinal profile."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np

from survey_core.contour import _compute_triangle_slopes
from survey_core.filt import _compute_triangle_geometry
from survey_core.io import build_viewer_payload_from_state
from survey_core.models import SurveyState


def _compute_longitudinal_profile(
    verts_xyz: np.ndarray,
    origin_e0: float,
    origin_n0: float,
    origin_z0: float,
    num_bins: int = 35,
) -> dict[str, Any]:
    """Compute longitudinal profile along the principal axis / corridor centerline of the survey."""
    if len(verts_xyz) < 2:
        return {"stations": [], "path_length_m": 0.0}

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
