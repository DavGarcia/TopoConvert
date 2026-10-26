"""Step 2 (`clean.py`): KD-tree duplicate removal and local z-score outlier detection."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from survey_core.io import build_viewer_payload_from_state
from survey_core.models import CodeConfig, RemovedPoint, SurveyState


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 2: Remove spatial duplicates (KD-tree) and elevation outliers (local z-score).

    Parameters in `params`:
        duplicate_tolerance (float): 2D distance threshold in meters for duplicate points (default: 0.001 m).
        outlier_z_threshold (float): Local z-score threshold for elevation outliers (default: 4.0).
        outlier_k_neighbors (int): Number of spatial neighbors for local elevation stats (default: 12).
        min_elevation_residual (float): Minimum absolute Z residual (m) to flag as outlier (default: 0.45 m).
    """
    if not state.raw_points:
        raise ValueError("ابتدا باید مرحله ۱ (بارگذاری فایل) اجرا شود.")

    params = params or {}
    duplicate_tolerance = float(params.get("duplicate_tolerance", 0.001))
    outlier_z_threshold = float(params.get("outlier_z_threshold", 4.0))
    outlier_k_neighbors = int(params.get("outlier_k_neighbors", 12))
    min_elev_residual = float(params.get("min_elevation_residual", 0.45))

    if duplicate_tolerance < 0:
        raise ValueError("تلرانس نقاط تکراری نمی‌تواند منفی باشد.")
    if outlier_z_threshold <= 0:
        raise ValueError("آستانه z-score باید بزرگ‌تر از صفر باشد.")

    pts = state.raw_points
    n_total = len(pts)

    xy = np.array([[p.x_local, p.y_local] for p in pts], dtype=np.float64)
    z_arr = np.array([p.z_local for p in pts], dtype=np.float64)

    removed_points: list[RemovedPoint] = []
    removed_indices: set[int] = set()

    # 1. Duplicate removal using 2D cKDTree in local meter coordinates (vectorized query_pairs)
    if duplicate_tolerance > 0 and n_total > 1:
        tree_dup = cKDTree(xy)
        pairs = tree_dup.query_pairs(r=duplicate_tolerance, output_type="ndarray")
        if len(pairs) > 0:
            # Sort pairs by (i, j) so greedy first-kept behavior is identical
            order = np.lexsort((pairs[:, 1], pairs[:, 0]))
            for idx_pair in order:
                i = int(pairs[idx_pair, 0])
                j = int(pairs[idx_pair, 1])
                if i in removed_indices or j in removed_indices:
                    continue
                dist = float(np.linalg.norm(xy[j] - xy[i]))
                removed_indices.add(j)
                removed_points.append(
                    RemovedPoint(
                        point=pts[j],
                        reason="duplicate",
                        metric_value=dist,
                        detail=f"فاصله افقی {dist:.4f}m نسبت به نقطه شماره {pts[i].id} (کمتر از تلرانس {duplicate_tolerance:.4f}m)",
                    )
                )

    surviving_after_dup = [i for i in range(n_total) if i not in removed_indices]
    duplicate_removed_count = len(removed_indices)

    # 2. Local z-score elevation outlier removal on surviving points (vectorized over (N, k) neighbor matrix)
    outlier_removed_count = 0
    max_observed_zscore = 0.0
    if len(surviving_after_dup) >= 4:
        surv_idx = np.array(surviving_after_dup, dtype=np.int32)
        surv_xy = xy[surv_idx]
        surv_z = z_arr[surv_idx]
        k_query = min(max(4, outlier_k_neighbors + 1), len(surv_idx))
        tree_out = cKDTree(surv_xy)
        _, nbr_positions = tree_out.query(surv_xy, k=k_query)

        # Compute robust local elevation statistics using neighbors (excluding self at col 0)
        nbr_z_mat = surv_z[nbr_positions[:, 1:]]  # shape (N_surv, k-1)
        med_z_vec = np.median(nbr_z_mat, axis=1)
        mad_vec = np.median(np.abs(nbr_z_mat - med_z_vec[:, None]), axis=1)
        std_vec = np.std(nbr_z_mat, axis=1)
        robust_sigma_vec = np.maximum(np.maximum(1.4826 * mad_vec, std_vec * 0.5), 0.05)
        residual_vec = np.abs(surv_z - med_z_vec)
        min_nbr_dz_vec = np.min(np.abs(nbr_z_mat - surv_z[:, None]), axis=1)
        z_score_vec = residual_vec / robust_sigma_vec
        max_observed_zscore = (
            float(np.max(z_score_vec)) if len(z_score_vec) > 0 else 0.0
        )

        outlier_mask = (
            (z_score_vec > outlier_z_threshold)
            & (residual_vec >= min_elev_residual)
            & (min_nbr_dz_vec >= min_elev_residual)
        )
        for local_pos in np.flatnonzero(outlier_mask):
            orig_idx = int(surv_idx[local_pos])
            z_score = float(z_score_vec[local_pos])
            residual = float(residual_vec[local_pos])
            removed_indices.add(orig_idx)
            outlier_removed_count += 1
            removed_points.append(
                RemovedPoint(
                    point=pts[orig_idx],
                    reason="outlier",
                    metric_value=z_score,
                    detail=f"اختلاف ارتفاع محلی {residual:.3f}m (امتیاز z={z_score:.2f} > {outlier_z_threshold:.2f})",
                )
            )

    cleaned_points = [pts[i] for i in range(n_total) if i not in removed_indices]
    if len(cleaned_points) < 3:
        raise ValueError(
            f"پس از پاک‌سازی تنها {len(cleaned_points)} نقطه باقی ماند. لطفاً تلرانس را کاهش دهید."
        )

    # Update code counts in code_configs
    code_counts: dict[str, int] = {}
    for p in cleaned_points:
        code_counts[p.code] = code_counts.get(p.code, 0) + 1

    updated_code_configs: dict[str, CodeConfig] = {}
    for code, cfg in state.code_configs.items():
        updated_code_configs[code] = replace(cfg, count=code_counts.get(code, 0))

    # Nearest-neighbor summary on raw points for UI slider guidance
    if n_total >= 2:
        raw_tree = cKDTree(xy)
        d2, _ = raw_tree.query(xy, k=2)
        nn_dists = d2[:, 1]
        min_nn_dist = float(np.min(nn_dists))
        median_nn_dist = float(np.median(nn_dists))
    else:
        min_nn_dist = 0.0
        median_nn_dist = 0.0

    clean_params_used = {
        "duplicate_tolerance": duplicate_tolerance,
        "outlier_z_threshold": outlier_z_threshold,
        "outlier_k_neighbors": outlier_k_neighbors,
        "min_elevation_residual": min_elev_residual,
    }

    stats: dict[str, Any] = {
        "step": 2,
        "before_count": n_total,
        "after_count": len(cleaned_points),
        "removed_total": len(removed_points),
        "duplicates_removed": duplicate_removed_count,
        "outliers_removed": outlier_removed_count,
        "min_nearest_neighbor_m": round(min_nn_dist, 4),
        "median_nearest_neighbor_m": round(median_nn_dist, 3),
        "max_observed_zscore": round(max_observed_zscore, 2),
        "params": clean_params_used,
        "removed_points": [rp.to_dict() for rp in removed_points],
    }

    # Invalidate downstream steps > 2
    new_step_stats = {k: v for k, v in state.step_stats.items() if k <= 1}
    new_step_stats[2] = stats
    completed = [s for s in state.completed_steps if s < 2] + [2]

    new_state = replace(
        state,
        cleaned_points=cleaned_points,
        removed_points=removed_points,
        clean_params=clean_params_used,
        code_configs=updated_code_configs,
        active_points=[
            p
            for p in cleaned_points
            if updated_code_configs.get(p.code, CodeConfig(p.code, 1)).role != "ignore"
        ],
        completed_steps=completed,
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=2)
    return (new_state, stats, viewer_payload)
