"""Step 3 (`codes.py`): Survey code classification table (point / breakline / boundary / ignore)."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from survey_core.io import DEFAULT_CODE_PALETTE, build_viewer_payload_from_state
from survey_core.models import CodeConfig, SurveyPoint, SurveyState

VALID_ROLES = {"point", "breakline", "boundary", "ignore"}


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 3: Apply user-selected code roles and construct breaklines / boundary polygon.

    Parameters in `params`:
        code_roles (dict[str, str]): Mapping of code -> role ('point' | 'breakline' | 'boundary' | 'ignore').
        code_colors (dict[str, str]): Optional mapping of code -> hex color string.
        max_breakline_gap (float): Maximum distance (m) between consecutive same-code points
            in a single breakline segment before splitting into a new polyline (default: 80.0 m).
        explicit_breaklines (list[list[int]]): Optional explicit vertex index chains in active_points.
        explicit_boundary_local (list[tuple[float, float]]): Optional explicit boundary polygon in local XY.
        explicit_holes_local (list[list[tuple[float, float]]]): Optional interior hole polygons in local XY.
    """
    pts = state.cleaned_points if state.cleaned_points else state.raw_points
    if not pts:
        raise ValueError("ابتدا باید مراحل بارگذاری و پاک‌سازی اجرا شوند.")

    params = params or {}
    role_updates: dict[str, str] = params.get("code_roles") or {}
    color_updates: dict[str, str] = params.get("code_colors") or {}
    max_breakline_gap = float(params.get("max_breakline_gap", 80.0))

    # Count codes in cleaned points
    code_counts: dict[str, int] = {}
    for p in pts:
        code_counts[p.code] = code_counts.get(p.code, 0) + 1

    new_configs: dict[str, CodeConfig] = {}
    for idx, (code, count) in enumerate(code_counts.items()):
        prev = state.code_configs.get(code)
        role = role_updates.get(code, prev.role if prev else "point")
        if role not in VALID_ROLES:
            raise ValueError(
                f"نقش نامعتبر '{role}' برای کد '{code}'. مقادیر مجاز: {sorted(VALID_ROLES)}"
            )
        color = color_updates.get(
            code,
            (
                prev.color
                if prev
                else DEFAULT_CODE_PALETTE[idx % len(DEFAULT_CODE_PALETTE)]
            ),
        )
        new_configs[code] = CodeConfig(code=code, count=count, role=role, color=color)

    # Filter active points (exclude 'ignore')
    active_points: list[SurveyPoint] = [
        p for p in pts if new_configs[p.code].role != "ignore"
    ]
    if len(active_points) < 3:
        raise ValueError(
            f"تعداد نقاط فعال پس از اعمال کدها ({len(active_points)} نقطه) کمتر از ۳ نقطه است."
        )

    # Map SurveyPoint.index -> position in active_points
    orig_idx_to_active_idx: dict[int, int] = {
        p.index: active_idx for active_idx, p in enumerate(active_points)
    }

    # Construct breaklines from codes marked as 'breakline'
    breaklines_local: list[dict[str, Any]] = []
    for code, cfg in new_configs.items():
        if cfg.role != "breakline":
            continue
        code_pts = [p for p in active_points if p.code == code]
        if len(code_pts) < 2:
            continue

        # Split into contiguous sub-polylines when gap > max_breakline_gap
        current_chain: list[SurveyPoint] = [code_pts[0]]
        for p_next in code_pts[1:]:
            p_prev = current_chain[-1]
            dist = math.hypot(
                p_next.x_local - p_prev.x_local, p_next.y_local - p_prev.y_local
            )
            if dist <= max_breakline_gap:
                current_chain.append(p_next)
            else:
                if len(current_chain) >= 2:
                    breaklines_local.append(
                        {
                            "code": code,
                            "color": cfg.color,
                            "point_ids": [cp.id for cp in current_chain],
                            "vertex_indices": [
                                orig_idx_to_active_idx[cp.index] for cp in current_chain
                            ],
                            "coords": [
                                [
                                    round(cp.x_local, 3),
                                    round(cp.y_local, 3),
                                    round(cp.z_local, 3),
                                ]
                                for cp in current_chain
                            ],
                        }
                    )
                current_chain = [p_next]

        if len(current_chain) >= 2:
            breaklines_local.append(
                {
                    "code": code,
                    "color": cfg.color,
                    "point_ids": [cp.id for cp in current_chain],
                    "vertex_indices": [
                        orig_idx_to_active_idx[cp.index] for cp in current_chain
                    ],
                    "coords": [
                        [
                            round(cp.x_local, 3),
                            round(cp.y_local, 3),
                            round(cp.z_local, 3),
                        ]
                        for cp in current_chain
                    ],
                }
            )

    # Also support explicit_breaklines (vertex index chains into active_points)
    explicit_bls = params.get("explicit_breaklines") or []
    for bl_idx, chain in enumerate(explicit_bls):
        valid_chain = [int(i) for i in chain if 0 <= int(i) < len(active_points)]
        if len(valid_chain) >= 2:
            breaklines_local.append(
                {
                    "code": f"BL_{bl_idx + 1}",
                    "color": "#f59e0b",
                    "point_ids": [active_points[i].id for i in valid_chain],
                    "vertex_indices": valid_chain,
                    "coords": [
                        [
                            round(active_points[i].x_local, 3),
                            round(active_points[i].y_local, 3),
                            round(active_points[i].z_local, 3),
                        ]
                        for i in valid_chain
                    ],
                }
            )

    # Construct boundary polygon from codes marked as 'boundary'
    boundary_pts = [p for p in active_points if new_configs[p.code].role == "boundary"]
    boundary_poly_local: list[tuple[float, float]] | None = None
    if params.get("explicit_boundary_local"):
        boundary_poly_local = [
            (float(pt[0]), float(pt[1])) for pt in params["explicit_boundary_local"]
        ]
        if (
            len(boundary_poly_local) >= 3
            and boundary_poly_local[0] != boundary_poly_local[-1]
        ):
            boundary_poly_local.append(boundary_poly_local[0])
    elif len(boundary_pts) >= 3:
        boundary_poly_local = [(p.x_local, p.y_local) for p in boundary_pts]
        if boundary_poly_local[0] != boundary_poly_local[-1]:
            boundary_poly_local.append(boundary_poly_local[0])

    holes_local: list[list[tuple[float, float]]] = []
    if params.get("explicit_holes_local"):
        for hole in params["explicit_holes_local"]:
            h_coords = [(float(pt[0]), float(pt[1])) for pt in hole]
            if len(h_coords) >= 3:
                if h_coords[0] != h_coords[-1]:
                    h_coords.append(h_coords[0])
                holes_local.append(h_coords)

    ignored_count = len(pts) - len(active_points)
    breakline_segment_count = sum(
        len(bl["vertex_indices"]) - 1 for bl in breaklines_local
    )

    stats: dict[str, Any] = {
        "step": 3,
        "codes": [cfg.to_dict() for cfg in new_configs.values()],
        "active_point_count": len(active_points),
        "ignored_point_count": ignored_count,
        "breakline_polyline_count": len(breaklines_local),
        "breakline_segment_count": breakline_segment_count,
        "has_boundary_code": boundary_poly_local is not None,
        "boundary_vertex_count": len(boundary_poly_local) if boundary_poly_local else 0,
        "hole_count": len(holes_local),
        "codes_meaning_note": "معنی کدهای برداشت‌شده (مانند AF، J، END) هرگز به صورت خودکار حدس زده نمی‌شود؛ نقش هر کد توسط کاربر تعیین می‌گردد.",
    }

    new_step_stats = {k: v for k, v in state.step_stats.items() if k <= 2}
    new_step_stats[3] = stats
    completed = [s for s in state.completed_steps if s < 3] + [3]

    new_state = replace(
        state,
        code_configs=new_configs,
        active_points=active_points,
        breaklines_local=breaklines_local,
        boundary_codes_polygon_local=boundary_poly_local,
        holes_local=holes_local,
        completed_steps=completed,
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=3)
    return (new_state, stats, viewer_payload)
