"""`survey_core/export.py`: CAD-ready DXF (ezdxf) and CSV export with local-to-global origin restoration."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import ezdxf
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


def build_dxf_document(state: SurveyState) -> ezdxf.document.Drawing:
    """Create a CAD-ready DXF R2010 document with all survey layers shifted back to global UTM."""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 6  # Meters

    for layer_name, color_aci in REQUIRED_DXF_LAYERS:
        if layer_name not in doc.layers:
            doc.layers.add(layer_name, color=color_aci)

    msp = doc.modelspace()
    origin = state.origin

    active_pts = state.active_points or state.cleaned_points or state.raw_points

    # Track global extents for CAD $EXTMIN / $EXTMAX header variables
    all_e: list[float] = []
    all_n: list[float] = []
    all_z: list[float] = []

    # 1. POINTS, PT_NO, PT_ELEV
    text_height = 0.25
    for pt in active_pts:
        # Shift back from local to global to verify round-trip precision
        e_glob, n_glob, z_glob = origin.to_global(pt.x_local, pt.y_local, pt.z_local)
        all_e.append(e_glob)
        all_n.append(n_glob)
        all_z.append(z_glob)

        msp.add_point((e_glob, n_glob, z_glob), dxfattribs={"layer": "POINTS"})

        no_txt = msp.add_text(
            str(pt.id),
            dxfattribs={"layer": "PT_NO", "height": text_height},
        )
        no_txt.set_placement(
            (e_glob + 0.15, n_glob + 0.15, z_glob),
            align=TextEntityAlignment.LEFT,
        )

        elev_txt = msp.add_text(
            f"{z_glob:.3f}",
            dxfattribs={"layer": "PT_ELEV", "height": text_height},
        )
        elev_txt.set_placement(
            (e_glob + 0.15, n_glob - 0.25, z_glob),
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
            v0 = origin.to_global(
                float(verts[tri[0], 0]),
                float(verts[tri[0], 1]),
                float(verts[tri[0], 2]),
            )
            v1 = origin.to_global(
                float(verts[tri[1], 0]),
                float(verts[tri[1], 1]),
                float(verts[tri[1], 2]),
            )
            v2 = origin.to_global(
                float(verts[tri[2], 0]),
                float(verts[tri[2], 1]),
                float(verts[tri[2], 2]),
            )
            msp.add_3dface([v0, v1, v2, v2], dxfattribs={"layer": "TIN"})

    # 3. CONTOUR_MAJOR & CONTOUR_MINOR
    for contour in state.contours:
        layer_name = "CONTOUR_MAJOR" if contour.is_major else "CONTOUR_MINOR"
        pts_3d: list[tuple[float, float, float]] = [
            origin.to_global(px, py, contour.z_local) for px, py in contour.points_local
        ]
        if len(pts_3d) >= 2:
            msp.add_polyline3d(pts_3d, dxfattribs={"layer": layer_name})
            if contour.is_major and contour.label_pos_local is not None:
                lx, ly, l_angle = contour.label_pos_local
                le, ln, lz = origin.to_global(lx, ly, contour.z_local)
                c_txt = msp.add_text(
                    f"{contour.elevation:.2f}",
                    dxfattribs={
                        "layer": "CONTOUR_MAJOR",
                        "height": text_height * 1.1,
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
                origin.to_global(float(c[0]), float(c[1]), float(c[2]))
                for c in coords_loc
            ]
            msp.add_polyline3d(bl_pts_3d, dxfattribs={"layer": "BREAKLINES"})

    # 5. BOUNDARY
    boundary_loc = state.boundary_polygon_local or state.boundary_codes_polygon_local
    if boundary_loc and len(boundary_loc) >= 3:
        bnd_pts_3d = [
            origin.to_global(float(bx), float(by), 0.0) for bx, by in boundary_loc
        ]
        msp.add_polyline3d(bnd_pts_3d, dxfattribs={"layer": "BOUNDARY"})

    if all_e and all_n and all_z:
        doc.header["$EXTMIN"] = (min(all_e), min(all_n), min(all_z))
        doc.header["$EXTMAX"] = (max(all_e), max(all_n), max(all_z))

    return doc


def export_dxf_bytes(
    state: SurveyState, output_path: str | Path | None = None
) -> bytes:
    """Export state to DXF bytes (and optionally save to `output_path`)."""
    doc = build_dxf_document(state)
    if output_path is not None:
        doc.saveas(str(output_path))
        return Path(output_path).read_bytes()

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


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
