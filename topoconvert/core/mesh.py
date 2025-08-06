"""Generate 3D TIN mesh from KML point data.

Adapted from GPSGrid kml_to_mesh_dxf.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional

import ezdxf
import numpy as np
from scipy.spatial import Delaunay

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer
from topoconvert.core.result_types import MeshGenerationResult


NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084
FT_TO_M = 0.3048


def generate_mesh(
    input_file: Path,
    output_file: Path,
    elevation_units: str = "meters",
    translate_to_origin: bool = True,
    use_reference_point: bool = False,
    layer_name: str = "TIN_MESH",
    mesh_color: int = 8,
    add_wireframe: bool = False,
    wireframe_color: int = 7,
    target_epsg: Optional[int] = None,
    wgs84: bool = False,
) -> MeshGenerationResult:
    """Generate 3D TIN mesh from KML point data.

    Args:
        input_file: Path to input KML file
        output_file: Path to output DXF file
        elevation_units: Units of elevation in KML ('meters' or 'feet')
        translate_to_origin: Whether to translate coordinates
        use_reference_point: Use first point as reference
        layer_name: Layer name for mesh faces
        mesh_color: AutoCAD color index for mesh faces
        add_wireframe: Whether to add wireframe edges
        wireframe_color: AutoCAD color index for wireframe
        target_epsg: Target EPSG code for projection (default: auto-detect UTM)
        wgs84: Keep coordinates in WGS84 (no projection)

    Raises:
        FileNotFoundError: If input file doesn't exist
        FileFormatError: If file format is invalid
        ValueError: If parameters are invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    input_file = validate_file_path(input_file, must_exist=True)
    output_file = ensure_file_extension(output_file, ".dxf")

    # Validate parameters
    if elevation_units not in ["meters", "feet"]:
        raise ValueError("elevation_units must be 'meters' or 'feet'")

    if mesh_color < 0 or wireframe_color < 0:
        raise ValueError("Color indices must be non-negative")

    try:
        return _process_mesh_generation(
            input_file=input_file,
            output_file=output_file,
            elevation_units=elevation_units,
            translate_to_origin=translate_to_origin,
            use_reference_point=use_reference_point,
            layer_name=layer_name,
            mesh_color=mesh_color,
            add_wireframe=add_wireframe,
            wireframe_color=wireframe_color,
            target_epsg=target_epsg,
            wgs84=wgs84,
        )
    except Exception as e:
        raise ProcessingError(f"Mesh generation failed: {str(e)}") from e


def _parse_coordinates(coord_text: str) -> Optional[Tuple[float, float, float]]:
    """Parse KML coordinate string (lon,lat,elev)"""
    parts = coord_text.strip().split(",")
    if len(parts) >= 2:
        lon = float(parts[0])
        lat = float(parts[1])
        elev = float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0
        return (lon, lat, elev)
    return None


def _extract_kml_points(kml_path: Path) -> List[Tuple[float, float, float]]:
    """Extract all Point coordinates from KML"""
    try:
        tree = ET.parse(str(kml_path))
    except ET.ParseError as e:
        raise FileFormatError(f"Invalid KML file: {e}")

    root = tree.getroot()
    points = []

    # Find all Placemarks with Points
    for pm in root.findall(".//kml:Placemark", NS):
        point_elem = pm.find(".//kml:Point", NS)
        if point_elem is not None:
            coord_elem = point_elem.find("kml:coordinates", NS)
            if coord_elem is not None and coord_elem.text:
                coord = _parse_coordinates(coord_elem.text)
                if coord:
                    points.append(coord)

    return points


def _create_mesh_dxf(
    points_3d: List[Tuple[float, float, float]],
    output_file: Path,
    layer_name: str,
    mesh_color: int,
    add_wireframe: bool,
    wireframe_color: int,
) -> Tuple[int, int]:
    """Create DXF file with 3D mesh"""

    # Create Delaunay triangulation (only X,Y coordinates for 2D triangulation)
    points_2d = np.array([(x, y) for x, y, z in points_3d])

    # Check for duplicate points or colinear points
    if len(points_2d) < 3:
        raise ProcessingError(
            f"Need at least 3 points for triangulation, have {len(points_2d)}"
        )

    try:
        tri = Delaunay(points_2d)
    except Exception as e:
        raise ProcessingError(f"Error creating triangulation: {e}")

    # Create DXF
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Set units to feet
    try:
        from ezdxf import units as _ez_units

        if hasattr(_ez_units, "FOOT"):
            doc.units = _ez_units.FOOT
        else:
            doc.header["$INSUNITS"] = 2  # Feet
    except Exception:
        doc.header["$INSUNITS"] = 2

    # Create layers
    if layer_name not in doc.layers:
        doc.layers.add(layer_name, color=mesh_color)

    wireframe_layer = None
    if add_wireframe:
        wireframe_layer = f"{layer_name}_WIREFRAME"
        if wireframe_layer not in doc.layers:
            doc.layers.add(wireframe_layer, color=wireframe_color)

    # Add mesh faces to DXF
    face_count = 0
    edge_set = set()  # For wireframe edges

    for simplex in tri.simplices:
        # Get the three vertices of the triangle
        i1, i2, i3 = simplex

        x1, y1, z1 = points_3d[i1]
        x2, y2, z2 = points_3d[i2]
        x3, y3, z3 = points_3d[i3]

        # Add 3D face
        msp.add_3dface(
            [
                (x1, y1, z1),
                (x2, y2, z2),
                (x3, y3, z3),
                (x3, y3, z3),  # repeat last point for triangle
            ],
            dxfattribs={"layer": layer_name},
        )

        face_count += 1

        # Collect edges for wireframe
        if add_wireframe:
            edges = [
                (min(i1, i2), max(i1, i2)),
                (min(i2, i3), max(i2, i3)),
                (min(i3, i1), max(i3, i1)),
            ]
            edge_set.update(edges)

    # Add wireframe edges if requested
    edge_count = 0
    if add_wireframe and wireframe_layer:
        for i1, i2 in edge_set:
            x1, y1, z1 = points_3d[i1]
            x2, y2, z2 = points_3d[i2]

            msp.add_line(
                (x1, y1, z1), (x2, y2, z2), dxfattribs={"layer": wireframe_layer}
            )
            edge_count += 1

    # Save DXF
    doc.saveas(str(output_file))

    return face_count, edge_count


def _process_mesh_generation(
    input_file: Path,
    output_file: Path,
    elevation_units: str,
    translate_to_origin: bool,
    use_reference_point: bool,
    layer_name: str,
    mesh_color: int,
    add_wireframe: bool,
    wireframe_color: int,
    target_epsg: Optional[int],
    wgs84: bool,
) -> MeshGenerationResult:
    """Process mesh generation - internal implementation."""

    # Extract points from KML
    kml_points = _extract_kml_points(input_file)

    if not kml_points:
        raise ProcessingError(f"No points found in {input_file}")

    if len(kml_points) < 3:
        raise ProcessingError(
            f"Need at least 3 points for triangulation, found {len(kml_points)}"
        )

    # Store for result reporting
    point_count = len(kml_points)

    # Determine target CRS
    if kml_points:
        sample_point = (kml_points[0][0], kml_points[0][1])
        target_crs = get_target_crs(target_epsg, wgs84, sample_point)
    else:
        raise ProcessingError("No points found in KML file")

    # Setup projection
    transformer = get_transformer(4326, target_crs)

    # Convert points to local coordinates
    x_vals_ft = []
    y_vals_ft = []
    z_vals_ft = []

    for lon, lat, elev in kml_points:
        # Project coordinates
        x_proj, y_proj = transformer.transform(lon, lat)

        # Convert to feet if projected (UTM is in meters)
        if not wgs84:
            x_ft = x_proj * M_TO_FT
            y_ft = y_proj * M_TO_FT
        else:
            # Keep in degrees for WGS84
            x_ft = x_proj
            y_ft = y_proj

        # Handle elevation units
        if elevation_units == "meters":
            z_ft = elev * M_TO_FT
        else:  # already in feet
            z_ft = elev

        x_vals_ft.append(x_ft)
        y_vals_ft.append(y_ft)
        z_vals_ft.append(z_ft)

    # Determine reference point for translation
    if not translate_to_origin:
        ref_x, ref_y, ref_z = 0.0, 0.0, 0.0
        x_local = x_vals_ft
        y_local = y_vals_ft
        z_local = z_vals_ft
    elif use_reference_point:
        # Use first point as reference (like latlong_to_dxf.py)
        ref_x, ref_y, ref_z = x_vals_ft[0], y_vals_ft[0], z_vals_ft[0]
        # Translate all points (including reference point for mesh generation)
        x_local = [x - ref_x for x in x_vals_ft]
        y_local = [y - ref_y for y in y_vals_ft]
        z_local = [z - ref_z for z in z_vals_ft]
    else:
        # Use center of bounds as reference
        ref_x = (min(x_vals_ft) + max(x_vals_ft)) / 2.0
        ref_y = (min(y_vals_ft) + max(y_vals_ft)) / 2.0
        ref_z = min(z_vals_ft)  # Use minimum elevation as reference
        # Translate to local coordinates
        x_local = [x - ref_x for x in x_vals_ft]
        y_local = [y - ref_y for y in y_vals_ft]
        z_local = [z - ref_z for z in z_vals_ft]

    # Check if we have enough points for triangulation
    if len(x_local) < 3:
        raise ProcessingError(
            f"Need at least 3 points for triangulation, have {len(x_local)}"
        )

    points_3d = list(zip(x_local, y_local, z_local))

    # Create mesh DXF
    face_count, edge_count = _create_mesh_dxf(
        points_3d, output_file, layer_name, mesh_color, add_wireframe, wireframe_color
    )

    # Build coordinate system description
    if wgs84:
        coord_system = "WGS84 (degrees)"
    elif target_epsg:
        coord_system = f"EPSG:{target_epsg} (feet)"
    else:
        coord_system = "Auto-detected UTM zone (feet)"

    # Build result details
    details = {
        "coordinate_ranges": {},
        "wireframe_layer": f"{layer_name}_WIREFRAME" if add_wireframe else None,
        "mesh_color": mesh_color,
        "wireframe_color": wireframe_color if add_wireframe else None,
        "triangulation_info": {
            "points_found": point_count,
            "triangles_created": face_count,
        },
    }

    # Add coordinate ranges if available
    if x_local and y_local and z_local:
        details["coordinate_ranges"] = {
            "x": (min(x_local), max(x_local)),
            "y": (min(y_local), max(y_local)),
            "z": (min(z_local), max(z_local)),
            "units": "feet" if not wgs84 else "degrees",
        }

    # Return structured result
    return MeshGenerationResult(
        success=True,
        output_file=str(output_file),
        face_count=face_count,
        vertex_count=len(points_3d),
        edge_count=edge_count,
        mesh_type="TIN",
        has_wireframe=add_wireframe,
        layer_name=layer_name,
        coordinate_system=coord_system,
        reference_point=(ref_x, ref_y, ref_z) if translate_to_origin else None,
        translated_to_origin=translate_to_origin,
        details=details,
    )
