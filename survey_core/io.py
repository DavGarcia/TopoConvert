"""Step 1 (`io.py`): Parse, validate, and auto-detect total-station / GNSS survey files."""

from __future__ import annotations

import math
import re
from dataclasses import replace
from typing import Any

import numpy as np
from pyproj import CRS

from survey_core.models import CodeConfig, LocalOrigin, SurveyPoint, SurveyState

# Palette for codes (high-contrast engineering colors)
DEFAULT_CODE_PALETTE = [
    "#38bdf8",  # sky blue
    "#f59e0b",  # amber
    "#10b981",  # emerald
    "#f43f5e",  # rose
    "#a855f7",  # purple
    "#22d3ee",  # cyan
    "#eab308",  # yellow
    "#ec4899",  # pink
]


def _detect_delimiter(
    lines: list[str], user_delimiter: str | None = None
) -> tuple[str, str]:
    """Auto-detect delimiter from non-empty sample lines."""
    if user_delimiter and user_delimiter != "auto":
        mapping = {
            ",": (",", "comma"),
            "comma": (",", "comma"),
            "\t": ("\t", "tab"),
            "tab": ("\t", "tab"),
            ";": (";", "semicolon"),
            "semicolon": (";", "semicolon"),
            " ": ("space", "space"),
            "space": ("space", "space"),
        }
        if user_delimiter in mapping:
            return mapping[user_delimiter]

    sample = [
        ln.strip() for ln in lines[:30] if ln.strip() and not ln.strip().startswith("#")
    ]
    if not sample:
        return (",", "comma")

    candidates = [
        (",", "comma"),
        ("\t", "tab"),
        (";", "semicolon"),
    ]
    for char, name in candidates:
        counts = [ln.count(char) for ln in sample]
        if min(counts) >= 2 and max(counts) - min(counts) <= 2:
            return (char, name)

    # Check whitespace-separated
    ws_counts = [len(re.split(r"\s+", ln)) - 1 for ln in sample]
    if min(ws_counts) >= 2:
        return ("space", "space")

    return (",", "comma")


def _split_line(line: str, delimiter: str) -> list[str]:
    """Split a single line using the detected delimiter."""
    if delimiter == "space":
        return [tok.strip() for tok in re.split(r"\s+", line.strip()) if tok.strip()]
    return [tok.strip() for tok in line.strip().split(delimiter)]


def _is_float(val: str) -> bool:
    """Return True if string can be parsed as a finite float."""
    try:
        f = float(val)
        return math.isfinite(f)
    except (ValueError, TypeError):
        return False


def _detect_header_and_columns(tokens: list[str]) -> tuple[bool, str | None]:
    """Detect whether the first row is a header and if it hints at N/E order."""
    if not tokens:
        return (False, None)
    # In data rows, the last 3 columns (N, E, Z) are numeric floats
    if len(tokens) >= 3 and all(_is_float(tok) for tok in tokens[-3:]):
        return (False, None)

    lower = [t.lower().strip("\"'") for t in tokens]
    header_order: str | None = None
    # Check if header explicitly names easting/northing or x/y
    if len(lower) >= 5:
        c2, c3 = lower[2], lower[3]
        if c2 in ("easting", "east", "e", "x") and c3 in (
            "northing",
            "north",
            "n",
            "y",
        ):
            header_order = "E_N"
        elif c2 in ("northing", "north", "n", "y") and c3 in (
            "easting",
            "east",
            "e",
            "x",
        ):
            header_order = "N_E"
    elif len(lower) >= 3:
        c0, c1 = lower[-3], lower[-2]
        if c0 in ("easting", "east", "e", "x") and c1 in (
            "northing",
            "north",
            "n",
            "y",
        ):
            header_order = "E_N"
        elif c0 in ("northing", "north", "n", "y") and c1 in (
            "easting",
            "east",
            "e",
            "x",
        ):
            header_order = "N_E"
    return (True, header_order)


def _detect_ne_order(
    col_a: np.ndarray,
    col_b: np.ndarray,
    header_order: str | None = None,
) -> tuple[bool, bool, str]:
    """Heuristic detection of whether Col A (standard Northing) and Col B (standard Easting) are swapped.

    Standard format: ID,Code,Northing,Easting,Elevation -> Col A = Northing (Y), Col B = Easting (X).
    Returns:
        (swapped_heuristic, order_uncertain, reason)
    """
    if len(col_a) == 0:
        return (False, True, "هیچ نقطه‌ای یافت نشد")

    med_a = float(np.median(np.abs(col_a)))
    med_b = float(np.median(np.abs(col_b)))

    # UTM heuristic: Northing in mid-latitudes (e.g. Iran 25°N-40°N) is ~2,700,000 to 4,500,000 m (7 digits),
    # whereas UTM Easting is ~160,000 to 840,000 m (6 digits).
    a_looks_northing = 1_000_000.0 <= med_a <= 10_000_000.0
    b_looks_easting = 100_000.0 <= med_b < 1_000_000.0

    a_looks_easting = 100_000.0 <= med_a < 1_000_000.0
    b_looks_northing = 1_000_000.0 <= med_b <= 10_000_000.0

    if a_looks_northing and b_looks_easting:
        return (
            False,
            False,
            f"تشخیص خودکار UTM: ستون سوم Northing (~{med_a:,.0f}m) و ستون چهارم Easting (~{med_b:,.0f}m)",
        )

    if a_looks_easting and b_looks_northing:
        return (
            True,
            False,
            f"جابجایی N/E تشخیص داده شد: ستون سوم Easting (~{med_a:,.0f}m) و ستون چهارم Northing (~{med_b:,.0f}m)",
        )

    if header_order == "E_N":
        return (
            True,
            False,
            "بر اساس سرستون فایل، ستون Easting/X قبل از Northing/Y قرار دارد",
        )
    if header_order == "N_E":
        return (
            False,
            False,
            "بر اساس سرستون فایل، ستون Northing/Y قبل از Easting/X قرار دارد",
        )

    return (
        False,
        True,
        "مقادیر دو ستون مختصات در یک بازه عددی هستند؛ ترتیب پیش‌فرض (Northing, Easting) فرض شده است",
    )


def validate_crs(crs_str: str) -> tuple[str, str]:
    """Validate CRS string with pyproj and return normalized code and human-readable name."""
    try:
        crs_obj = CRS.from_user_input(crs_str)
        auth = crs_obj.to_authority()
        code = f"{auth[0]}:{auth[1]}" if auth else crs_str
        return (code, crs_obj.name or code)
    except Exception as exc:
        raise ValueError(f"سیستم تصویر نامعتبر است ({crs_str}): {exc}") from exc


def build_viewer_payload_from_state(
    state: SurveyState, active_step: int = 1
) -> dict[str, Any]:
    """Build compact viewer payload from current pipeline state."""
    pts_source = (
        state.active_points
        if active_step >= 3 and state.active_points
        else (
            state.cleaned_points
            if active_step >= 2 and state.cleaned_points
            else state.raw_points
        )
    )

    code_colors = {cfg.code: cfg.color for cfg in state.code_configs.values()}

    # For large point clouds (>10k), send full/strided flat Float32-ready array + strided point metadata
    pt_stride = max(1, len(pts_source) // 6000)
    points_payload = [
        {
            "id": p.id,
            "index": p.index,
            "code": p.code,
            "x": round(p.x_local, 3),
            "y": round(p.y_local, 3),
            "z": round(p.z_local, 3),
            "e": round(p.easting, 3),
            "n": round(p.northing, 3),
            "elev": round(p.elevation, 3),
            "color": code_colors.get(p.code, "#38bdf8"),
        }
        for p in pts_source[::pt_stride]
    ]

    flat_stride = max(1, len(pts_source) // 50000)
    points_flat: list[float] = []
    for p in pts_source[::flat_stride]:
        points_flat.extend(
            [round(p.x_local, 2), round(p.y_local, 2), round(p.z_local, 2)]
        )

    removed_payload = (
        [rp.to_dict() for rp in state.removed_points[:2000]] if active_step >= 2 else []
    )

    # TIN vertices and triangles
    tin_Payload: dict[str, Any] | None = None
    if (
        active_step >= 4
        and len(state.tin_vertices_local) > 0
        and len(state.tin_triangles) > 0
    ):
        v_arr = state.tin_vertices_local
        t_arr_full = state.tin_triangles
        tri_stride = max(1, len(t_arr_full) // 15000)
        t_arr = t_arr_full[::tri_stride]

        verts = np.round(v_arr, 3).tolist() if len(v_arr) <= 25000 else []
        all_tris = t_arr.tolist()
        if active_step >= 5 and len(state.triangle_mask) == len(t_arr_full):
            mask_full = state.triangle_mask[::tri_stride]
            mask = mask_full.tolist()
            active_tris = t_arr[mask_full].tolist()
        else:
            mask = [True] * len(all_tris)
            active_tris = all_tris

        # Compute per-triangle max edge and slope for interactive inspection & live slider filtering
        p0 = v_arr[t_arr[:, 0]]
        p1 = v_arr[t_arr[:, 1]]
        p2 = v_arr[t_arr[:, 2]]
        ab = p1 - p0
        ac = p2 - p0
        bc = p2 - p1
        e01 = np.linalg.norm(ab[:, :2], axis=1)
        e02 = np.linalg.norm(ac[:, :2], axis=1)
        e12 = np.linalg.norm(bc[:, :2], axis=1)
        max_edges = np.round(np.maximum(np.maximum(e01, e02), e12), 3).tolist()
        plan_areas = np.round(
            0.5 * np.abs(ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]), 3
        ).tolist()
        cross3d = np.cross(ab, ac)
        norms = np.linalg.norm(cross3d, axis=1)
        areas_3d = np.round(0.5 * norms, 3).tolist()
        nz = np.abs(cross3d[:, 2])
        cos_theta = np.clip(np.where(norms > 1e-12, nz / norms, 1.0), 0.0, 1.0)
        slopes_deg = np.round(np.degrees(np.arccos(cos_theta)), 2).tolist()

        # Minimum interior angle per triangle
        def _min_angles(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> list[float]:
            a2 = np.maximum(a * a, 1e-12)
            b2 = np.maximum(b * b, 1e-12)
            c2 = np.maximum(c * c, 1e-12)
            cos_a = np.clip((b2 + c2 - a2) / (2.0 * np.sqrt(b2 * c2)), -1.0, 1.0)
            cos_b = np.clip((a2 + c2 - b2) / (2.0 * np.sqrt(a2 * c2)), -1.0, 1.0)
            cos_c = np.clip((a2 + b2 - c2) / (2.0 * np.sqrt(a2 * b2)), -1.0, 1.0)
            ang = np.degrees(np.arccos(np.maximum(np.maximum(cos_a, cos_b), cos_c)))
            return np.round(ang, 2).tolist()

        min_angles = _min_angles(e01, e02, e12)

        tin_Payload = {
            "vertices": verts,
            "vertex_ids": state.tin_point_ids if len(v_arr) <= 25000 else [],
            "vertex_codes": state.tin_point_codes if len(v_arr) <= 25000 else [],
            "all_triangles": all_tris if len(v_arr) <= 25000 else [],
            "active_triangles": active_tris if len(v_arr) <= 25000 else [],
            "triangle_mask": mask if len(v_arr) <= 25000 else [],
            "max_edges": max_edges if len(v_arr) <= 25000 else [],
            "min_angles": min_angles if len(v_arr) <= 25000 else [],
            "plan_areas": plan_areas if len(v_arr) <= 25000 else [],
            "areas_3d": areas_3d if len(v_arr) <= 25000 else [],
            "slopes_deg": slopes_deg if len(v_arr) <= 25000 else [],
            "method": state.tin_method,
            "method_note": state.tin_method_note,
            "decimated_for_viewer": len(v_arr) > 25000,
        }

    contours_payload = (
        [c.to_dict(state.origin) for c in state.contours] if active_step >= 6 else []
    )

    boundary_payload = (
        [[round(x, 3), round(y, 3)] for x, y in state.boundary_polygon_local]
        if state.boundary_polygon_local
        else (
            [[round(x, 3), round(y, 3)] for x, y in state.boundary_codes_polygon_local]
            if state.boundary_codes_polygon_local
            else None
        )
    )

    # Compute local bounds
    if pts_source:
        xs = [p.x_local for p in pts_source]
        ys = [p.y_local for p in pts_source]
        zs = [p.z_local for p in pts_source]
        elevs = [p.elevation for p in pts_source]
        bounds_local = {
            "min_x": round(min(xs), 3),
            "max_x": round(max(xs), 3),
            "min_y": round(min(ys), 3),
            "max_y": round(max(ys), 3),
            "min_z": round(min(zs), 3),
            "max_z": round(max(zs), 3),
            "min_elev": round(min(elevs), 3),
            "max_elev": round(max(elevs), 3),
        }
    else:
        bounds_local = {
            "min_x": 0.0,
            "max_x": 1.0,
            "min_y": 0.0,
            "max_y": 1.0,
            "min_z": 0.0,
            "max_z": 1.0,
            "min_elev": 0.0,
            "max_elev": 1.0,
        }

    return {
        "active_step": active_step,
        "origin": state.origin.to_dict(),
        "crs": state.crs,
        "crs_name": state.crs_name,
        "crs_is_assumed": state.crs_is_assumed,
        "bounds_local": bounds_local,
        "points": points_payload,
        "points_flat": points_flat,
        "total_point_count": len(pts_source),
        "removed_points": removed_payload,
        "codes": [cfg.to_dict() for cfg in state.code_configs.values()],
        "breaklines": state.breaklines_local if active_step >= 3 else [],
        "boundary": boundary_payload,
        "holes": [
            [[round(x, 3), round(y, 3)] for x, y in h] for h in state.holes_local
        ],
        "tin": tin_Payload,
        "contours": contours_payload,
        "slope_grid": state.slope_grid_data if active_step >= 6 else None,
        "profile": state.profile_data if active_step >= 7 else None,
    }


def run(
    state: SurveyState, params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run Step 1: Parse, validate, and auto-detect survey input data."""
    params = params or {}
    raw_text = params.get("raw_text", state.raw_text)
    filename = params.get("filename", state.filename)

    if not raw_text or not raw_text.strip():
        raise ValueError(
            "فایل ورودی خالی است. لطفاً یک فایل برداشت معتبر بارگذاری کنید."
        )

    max_points = int(params.get("max_points", 200_000))

    raw_lines = [
        ln.strip()
        for ln in raw_text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not raw_lines:
        raise ValueError("هیچ سطر داده‌ای در فایل یافت نشد.")

    user_delimiter = params.get("delimiter")
    delimiter, delimiter_name = _detect_delimiter(raw_lines, user_delimiter)

    first_tokens = _split_line(raw_lines[0], delimiter)
    detected_header, header_order = _detect_header_and_columns(first_tokens)
    has_header = (
        bool(params["has_header"])
        if "has_header" in params and params["has_header"] is not None
        else detected_header
    )

    data_lines = raw_lines[1:] if has_header else raw_lines
    if len(data_lines) > max_points:
        raise ValueError(
            f"تعداد نقاط فایل ({len(data_lines):,}) بیشتر از حد مجاز ({max_points:,} نقطه) است."
        )

    parsed_rows: list[tuple[str, str, float, float, float]] = []
    warnings: list[str] = []

    for line_idx, line in enumerate(data_lines, start=2 if has_header else 1):
        tokens = _split_line(line, delimiter)
        if len(tokens) < 3:
            warnings.append(
                f"سطر {line_idx}: تعداد ستون‌ها ناکافی است ({len(tokens)} ستون)"
            )
            continue

        try:
            if len(tokens) >= 5:
                pt_id = tokens[0] or str(len(parsed_rows) + 1)
                code = tokens[1] or "PT"
                col_a = float(tokens[2])
                col_b = float(tokens[3])
                elev = float(tokens[4])
            elif len(tokens) == 4:
                pt_id = tokens[0] or str(len(parsed_rows) + 1)
                code = "PT"
                col_a = float(tokens[1])
                col_b = float(tokens[2])
                elev = float(tokens[3])
            else:  # 3 columns: N, E, Z
                pt_id = str(len(parsed_rows) + 1)
                code = "PT"
                col_a = float(tokens[0])
                col_b = float(tokens[1])
                elev = float(tokens[2])

            if not (
                math.isfinite(col_a) and math.isfinite(col_b) and math.isfinite(elev)
            ):
                warnings.append(
                    f"سطر {line_idx}: مقدار غیرمتناهی (NaN/Inf) نادیده گرفته شد"
                )
                continue

            parsed_rows.append((pt_id, code, col_a, col_b, elev))
        except ValueError:
            warnings.append(f"سطر {line_idx}: مقادیر عددی نامعتبر نادیده گرفته شد")

    if len(parsed_rows) < 3:
        raise ValueError(
            f"حداقل ۳ نقطه معتبر برای تشکیل مدل توپوگرافی لازم است (تعداد یافت‌شده: {len(parsed_rows)})."
        )

    col_a_arr = np.array([r[2] for r in parsed_rows], dtype=np.float64)
    col_b_arr = np.array([r[3] for r in parsed_rows], dtype=np.float64)

    swapped_heuristic, order_uncertain, heuristic_reason = _detect_ne_order(
        col_a_arr, col_b_arr, header_order
    )

    # Determine whether to swap Col A and Col B:
    # Standard order: Col A = Northing (Y), Col B = Easting (X)
    # If swapped_heuristic is True, Col A is Easting (X) and Col B is Northing (Y).
    if "swap_ne" in params and params["swap_ne"] is not None:
        swap_applied = bool(params["swap_ne"])
    else:
        swap_applied = swapped_heuristic

    if swap_applied:
        eastings = col_a_arr
        northings = col_b_arr
    else:
        northings = col_a_arr
        eastings = col_b_arr

    elevations = np.array([r[4] for r in parsed_rows], dtype=np.float64)

    # CRS validation
    crs_input = str(params.get("crs", state.crs or "EPSG:32640"))
    crs_code, crs_name = validate_crs(crs_input)
    crs_is_assumed = not bool(params.get("crs_confirmed", False))

    # Shift to local origin before any geometric computation
    origin = LocalOrigin(
        e0=float(np.mean(eastings)),
        n0=float(np.mean(northings)),
        z0=float(np.min(elevations)),
    )

    raw_points: list[SurveyPoint] = []
    code_counts: dict[str, int] = {}

    for idx, (pt_id, code, _, _, elev) in enumerate(parsed_rows):
        e_val = float(eastings[idx])
        n_val = float(northings[idx])
        x_loc, y_loc, z_loc = origin.to_local(e_val, n_val, elev)
        raw_points.append(
            SurveyPoint(
                id=pt_id,
                index=idx,
                code=code,
                easting=e_val,
                northing=n_val,
                elevation=elev,
                x_local=x_loc,
                y_local=y_loc,
                z_local=z_loc,
            )
        )
        code_counts[code] = code_counts.get(code, 0) + 1

    # Build initial code configs (never guessing code meanings; default role = "point")
    code_configs: dict[str, CodeConfig] = {}
    for c_idx, (c_name, c_count) in enumerate(code_counts.items()):
        color = DEFAULT_CODE_PALETTE[c_idx % len(DEFAULT_CODE_PALETTE)]
        code_configs[c_name] = CodeConfig(
            code=c_name,
            count=c_count,
            role="point",
            color=color,
        )

    stats: dict[str, Any] = {
        "step": 1,
        "filename": filename,
        "point_count": len(raw_points),
        "codes": {k: v for k, v in code_counts.items()},
        "code_list": [cfg.to_dict() for cfg in code_configs.values()],
        "extents": {
            "easting_min": round(float(np.min(eastings)), 3),
            "easting_max": round(float(np.max(eastings)), 3),
            "easting_span": round(float(np.max(eastings) - np.min(eastings)), 3),
            "northing_min": round(float(np.min(northings)), 3),
            "northing_max": round(float(np.max(northings)), 3),
            "northing_span": round(float(np.max(northings) - np.min(northings)), 3),
            "z_min": round(float(np.min(elevations)), 3),
            "z_max": round(float(np.max(elevations)), 3),
            "z_mean": round(float(np.mean(elevations)), 3),
            "z_span": round(float(np.max(elevations) - np.min(elevations)), 3),
        },
        "detected_format": {
            "delimiter": delimiter,
            "delimiter_name": delimiter_name,
            "has_header": has_header,
            "ne_swapped_heuristic": swapped_heuristic,
            "ne_swap_applied": swap_applied,
            "ne_order_uncertain": order_uncertain,
            "ne_heuristic_reason": heuristic_reason,
            "columns_order": (
                "ID, Code, Easting, Northing, Z"
                if swap_applied
                else "ID, Code, Northing, Easting, Z"
            ),
        },
        "crs": {
            "code": crs_code,
            "name": crs_name,
            "is_assumed": crs_is_assumed,
            "units": "meters",
        },
        "local_origin": origin.to_dict(),
        "parse_warnings": warnings,
    }

    new_step_stats = {1: stats}
    new_state = replace(
        state,
        raw_text=raw_text,
        filename=filename,
        crs=crs_code,
        crs_name=crs_name,
        crs_is_assumed=crs_is_assumed,
        detected_delimiter=delimiter,
        delimiter_name=delimiter_name,
        has_header=has_header,
        ne_swapped_heuristic=swapped_heuristic,
        ne_swap_applied=swap_applied,
        ne_order_uncertain=order_uncertain,
        ne_heuristic_reason=heuristic_reason,
        origin=origin,
        raw_points=raw_points,
        parse_warnings=warnings,
        cleaned_points=raw_points,
        removed_points=[],
        code_configs=code_configs,
        active_points=raw_points,
        completed_steps=[1],
        step_stats=new_step_stats,
    )

    viewer_payload = build_viewer_payload_from_state(new_state, active_step=1)
    return (new_state, stats, viewer_payload)


def parse_survey_text(
    raw_text: str, filename: str = "survey.txt", params: dict[str, Any] | None = None
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Convenience helper to create a new SurveyState and run Step 1 (`io`)."""
    p = dict(params or {})
    p["raw_text"] = raw_text
    p["filename"] = filename
    initial_state = SurveyState(raw_text=raw_text, filename=filename)
    return run(initial_state, p)
