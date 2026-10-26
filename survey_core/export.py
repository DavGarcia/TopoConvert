"""`survey_core/export.py`: CAD-ready DXF (ezdxf) and CSV export with local-to-global origin restoration."""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import bbox, zoom
from ezdxf.enums import TextEntityAlignment

from survey_core.models import SurveyState

REQUIRED_DXF_LAYERS = [
    ("POINTS", 2),  # Yellow
    ("PT_NO", 3),  # Green
    ("PT_ELEV", 4),  # Cyan
    ("TIN", 8),  # Dark Gray
    ("CONTOUR_MAJOR", 1),  # Red
    ("CONTOUR_MINOR", 9),  # Light Gray
    ("BREAKLINES", 30),  # Orange
    ("BOUNDARY", 5),  # Blue
]


def get_dxf_local_origin_offset(
    state: SurveyState, shift_to_local_origin: bool = False
) -> tuple[float, float]:
    """Return (offset_x, offset_y) rounded to thousands when `shift_to_local_origin` is True, else (0.0, 0.0).

    Only X (Easting) and Y (Northing) are shifted; Z (Elevation) is never shifted.
    """
    if not shift_to_local_origin:
        return (0.0, 0.0)

    active_pts = state.active_points or state.cleaned_points or state.raw_points
    if active_pts:
        origin = state.origin
        min_x = min(
            origin.to_global(p.x_local, p.y_local, p.z_local)[0] for p in active_pts
        )
        min_y = min(
            origin.to_global(p.x_local, p.y_local, p.z_local)[1] for p in active_pts
        )
    else:
        min_x = float(state.origin.e0)
        min_y = float(state.origin.n0)

    offset_x = float(math.floor(min_x / 1000.0) * 1000.0)
    offset_y = float(math.floor(min_y / 1000.0) * 1000.0)
    return (offset_x, offset_y)


def build_dxf_document(
    state: SurveyState, shift_to_local_origin: bool = False
) -> ezdxf.document.Drawing:
    """Create a CAD-ready DXF R2010 document with valid extents, active VPORT, and visible points."""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 6  # Meters
    doc.header["$PDMODE"] = 35
    doc.header["$PDSIZE"] = 0.4

    for layer_name, color_aci in REQUIRED_DXF_LAYERS:
        if layer_name not in doc.layers:
            doc.layers.add(layer_name, color=color_aci)

    msp = doc.modelspace()
    origin = state.origin
    active_pts = state.active_points or state.cleaned_points or state.raw_points

    offset_x, offset_y = get_dxf_local_origin_offset(
        state, shift_to_local_origin=shift_to_local_origin
    )

    def to_dxf_xyz(
        x_loc: float, y_loc: float, z_loc: float
    ) -> tuple[float, float, float]:
        eg, ng, zg = origin.to_global(x_loc, y_loc, z_loc)
        return (eg - offset_x, ng - offset_y, zg)

    # Compute map largest dimension first so TEXT height is ~0.15% of largest dimension
    if active_pts:
        xs = [p.x_local for p in active_pts]
        ys = [p.y_local for p in active_pts]
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        max_dim = max(span_x, span_y, 1.0)
    else:
        max_dim = 100.0

    text_height = max(round(max_dim * 0.0015, 4), 0.05)
    label_dx = text_height * 0.6
    label_dy_no = text_height * 0.6
    label_dy_elev = -text_height * 1.0

    # 1. POINTS, PT_NO, PT_ELEV
    for pt in active_pts:
        x_dxf, y_dxf, z_dxf = to_dxf_xyz(pt.x_local, pt.y_local, pt.z_local)

        msp.add_point((x_dxf, y_dxf, z_dxf), dxfattribs={"layer": "POINTS"})

        no_txt = msp.add_text(
            str(pt.id),
            dxfattribs={"layer": "PT_NO", "height": text_height},
        )
        no_txt.set_placement(
            (x_dxf + label_dx, y_dxf + label_dy_no, z_dxf),
            align=TextEntityAlignment.LEFT,
        )

        elev_txt = msp.add_text(
            f"{z_dxf:.3f}",
            dxfattribs={"layer": "PT_ELEV", "height": text_height},
        )
        elev_txt.set_placement(
            (x_dxf + label_dx, y_dxf + label_dy_elev, z_dxf),
            align=TextEntityAlignment.LEFT,
        )

    # 2. TIN (3DFACE)
    verts = state.tin_vertices_local
    tris = (
        state.filtered_triangles
        if len(state.filtered_triangles) > 0
        else state.tin_triangles
    )
    if len(verts) > 0 and len(tris) > 0:
        for tri in tris:
            v0 = to_dxf_xyz(
                float(verts[tri[0], 0]),
                float(verts[tri[0], 1]),
                float(verts[tri[0], 2]),
            )
            v1 = to_dxf_xyz(
                float(verts[tri[1], 0]),
                float(verts[tri[1], 1]),
                float(verts[tri[1], 2]),
            )
            v2 = to_dxf_xyz(
                float(verts[tri[2], 0]),
                float(verts[tri[2], 1]),
                float(verts[tri[2], 2]),
            )
            msp.add_3dface([v0, v1, v2, v2], dxfattribs={"layer": "TIN"})

    # 3. CONTOUR_MAJOR & CONTOUR_MINOR
    for contour in state.contours:
        layer_name = "CONTOUR_MAJOR" if contour.is_major else "CONTOUR_MINOR"
        pts_3d: list[tuple[float, float, float]] = [
            to_dxf_xyz(px, py, contour.z_local) for px, py in contour.points_local
        ]
        if len(pts_3d) >= 2:
            msp.add_polyline3d(pts_3d, dxfattribs={"layer": layer_name})
            if contour.is_major and contour.label_pos_local is not None:
                lx, ly, l_angle = contour.label_pos_local
                le, ln, lz = to_dxf_xyz(lx, ly, contour.z_local)
                c_txt = msp.add_text(
                    f"{contour.elevation:.2f}",
                    dxfattribs={
                        "layer": "CONTOUR_MAJOR",
                        "height": round(text_height * 1.1, 4),
                        "rotation": float(l_angle),
                    },
                )
                c_txt.set_placement(
                    (le, ln, lz),
                    align=TextEntityAlignment.MIDDLE_CENTER,
                )

    # 4. BREAKLINES
    for bl in state.breaklines_local:
        coords_loc = bl.get("coords", [])
        if len(coords_loc) >= 2:
            bl_pts_3d = [
                to_dxf_xyz(float(c[0]), float(c[1]), float(c[2])) for c in coords_loc
            ]
            msp.add_polyline3d(bl_pts_3d, dxfattribs={"layer": "BREAKLINES"})

    # 5. BOUNDARY
    boundary_loc = state.boundary_polygon_local or state.boundary_codes_polygon_local
    if boundary_loc and len(boundary_loc) >= 3:
        bnd_pts_3d = [to_dxf_xyz(float(bx), float(by), 0.0) for bx, by in boundary_loc]
        msp.add_polyline3d(bnd_pts_3d, dxfattribs={"layer": "BOUNDARY"})

    # Calculate true bounding box extents across all modelspace entities before saving
    ext = bbox.extents(msp)
    if ext.has_data:
        extmin_x, extmin_y, extmin_z = (
            float(ext.extmin.x),
            float(ext.extmin.y),
            float(ext.extmin.z),
        )
        extmax_x, extmax_y, extmax_z = (
            float(ext.extmax.x),
            float(ext.extmax.y),
            float(ext.extmax.z),
        )
        extmin_3d = (extmin_x, extmin_y, extmin_z)
        extmax_3d = (extmax_x, extmax_y, extmax_z)
        limmin_2d = (extmin_x, extmin_y)
        limmax_2d = (extmax_x, extmax_y)

        # Set on both modelspace layout DXF attributes (used by ezdxf update_extents/update_limits on write)
        # and document header variables
        msp.dxf.extmin = extmin_3d
        msp.dxf.extmax = extmax_3d
        msp.dxf.limmin = limmin_2d
        msp.dxf.limmax = limmax_2d
        doc.header["$EXTMIN"] = extmin_3d
        doc.header["$EXTMAX"] = extmax_3d
        doc.header["$LIMMIN"] = limmin_2d
        doc.header["$LIMMAX"] = limmax_2d

        # Configure *Active VPORT centered on data with height = 1.15 * largest XY dimension
        zoom.extents(msp, factor=1.15)
        center_x = 0.5 * (extmin_x + extmax_x)
        center_y = 0.5 * (extmin_y + extmax_y)
        max_span_xy = max(extmax_x - extmin_x, extmax_y - extmin_y, 1.0)
        vport_height = max_span_xy * 1.15

        active_vports = list(doc.viewports.get("*Active"))
        if not active_vports:
            active_vports = [doc.viewports.new("*Active")]
        for vp in active_vports:
            vp.dxf.center = (center_x, center_y)
            vp.dxf.height = vport_height
            vp.dxf.target = (0.0, 0.0, 0.0)
            vp.dxf.direction = (0.0, 0.0, 1.0)

    return doc


def verify_dxf_extents_and_viewport(
    dxf_source: bytes | str | Path,
) -> dict[str, Any]:
    """Read back a saved DXF with ezdxf and verify valid extents and *Active VPORT placement."""
    if isinstance(dxf_source, Path) or (
        isinstance(dxf_source, str)
        and "\n" not in dxf_source
        and Path(dxf_source).exists()
    ):
        reloaded = ezdxf.readfile(str(dxf_source))
    elif isinstance(dxf_source, bytes):
        reloaded = ezdxf.read(io.StringIO(dxf_source.decode("utf-8")))
    else:
        reloaded = ezdxf.read(io.StringIO(str(dxf_source)))

    extmin = reloaded.header.get("$EXTMIN")
    extmax = reloaded.header.get("$EXTMAX")
    limmin = reloaded.header.get("$LIMMIN")
    limmax = reloaded.header.get("$LIMMAX")

    if extmin is None or extmax is None:
        raise ValueError("DXF verification failed: $EXTMIN or $EXTMAX is missing.")

    min_x, min_y, min_z = float(extmin[0]), float(extmin[1]), float(extmin[2])
    max_x, max_y, max_z = float(extmax[0]), float(extmax[1]), float(extmax[2])

    for val in (min_x, min_y, min_z, max_x, max_y, max_z):
        if not math.isfinite(val) or abs(val) >= 1e15:
            raise ValueError(f"DXF verification failed: invalid extent value {val}.")

    if min_x > max_x or min_y > max_y:
        raise ValueError(
            f"DXF verification failed: inverted extents ({extmin} .. {extmax})."
        )

    if limmin is None or limmax is None:
        raise ValueError("DXF verification failed: $LIMMIN or $LIMMAX is missing.")

    active_vports = list(reloaded.viewports.get("*Active"))
    if not active_vports:
        raise ValueError("DXF verification failed: no *Active VPORT found.")

    vp = active_vports[0]
    cx, cy = float(vp.dxf.center[0]), float(vp.dxf.center[1])
    vp_h = float(vp.dxf.height)

    tol_x = max((max_x - min_x) * 0.01, 1e-3)
    tol_y = max((max_y - min_y) * 0.01, 1e-3)
    if not (
        min_x - tol_x <= cx <= max_x + tol_x and min_y - tol_y <= cy <= max_y + tol_y
    ):
        raise ValueError(
            f"DXF verification failed: VPORT center ({cx}, {cy}) is outside data extents "
            f"[{min_x}, {max_x}] x [{min_y}, {max_y}]."
        )

    if vp_h <= 0:
        raise ValueError(f"DXF verification failed: invalid VPORT height {vp_h}.")

    return {
        "extmin": (min_x, min_y, min_z),
        "extmax": (max_x, max_y, max_z),
        "limmin": (float(limmin[0]), float(limmin[1])),
        "limmax": (float(limmax[0]), float(limmax[1])),
        "vport_center": (cx, cy),
        "vport_height": vp_h,
        "pdmode": int(reloaded.header.get("$PDMODE", 0)),
        "pdsize": float(reloaded.header.get("$PDSIZE", 0.0)),
    }


def export_dxf_bytes(
    state: SurveyState,
    output_path: str | Path | None = None,
    shift_to_local_origin: bool = False,
) -> bytes:
    """Export state to DXF bytes with uniform CRLF line endings and post-write ezdxf verification."""
    doc = build_dxf_document(state, shift_to_local_origin=shift_to_local_origin)

    stream = io.StringIO()
    doc.write(stream)
    raw_text = stream.getvalue()
    # Normalize line endings to uniform CRLF (\r\n)
    crlf_text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    dxf_bytes = crlf_text.encode("utf-8")

    if output_path is not None:
        Path(output_path).write_bytes(dxf_bytes)
        verify_dxf_extents_and_viewport(Path(output_path))
    else:
        verify_dxf_extents_and_viewport(dxf_bytes)

    return dxf_bytes


def export_csv_string(state: SurveyState, output_path: str | Path | None = None) -> str:
    """Export active cleaned survey points back to global UTM CSV string."""
    active_pts = state.active_points or state.cleaned_points or state.raw_points
    origin = state.origin

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["ID", "Code", "Northing", "Easting", "Elevation"])

    for pt in active_pts:
        e_glob, n_glob, z_glob = origin.to_global(pt.x_local, pt.y_local, pt.z_local)
        writer.writerow(
            [
                pt.id,
                pt.code,
                f"{n_glob:.3f}",
                f"{e_glob:.3f}",
                f"{z_glob:.3f}",
            ]
        )

    csv_text = buf.getvalue()
    if output_path is not None:
        Path(output_path).write_text(csv_text, encoding="utf-8")
    return csv_text
