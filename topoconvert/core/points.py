"""Extract points from KML and save in various formats.

Adapted from GPSGrid kml_to_points_dxf.py and kml_points_to_csv.py
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional

import ezdxf

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer
from topoconvert.core.result_types import PointExtractionResult


NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084
FT_TO_M = 0.3048


def extract_points(
    input_file: Path,
    output_file: Path,
    output_format: str = "dxf",
    elevation_units: str = "meters",
    translate_to_origin: bool = True,
    use_reference_point: bool = False,
    layer_name: str = "GPS_POINTS",
    point_color: int = 7,
    target_epsg: Optional[int] = None,
    wgs84: bool = False,
) -> PointExtractionResult:
    """Extract points from KML and save in specified format.

    Args:
        input_file: Path to input KML file
        output_file: Path to output file
        output_format: Output format ('dxf', 'csv', 'json', 'txt')
        elevation_units: Units of elevation in KML ('meters' or 'feet')
        translate_to_origin: Whether to translate coordinates
        use_reference_point: Use first point as reference
        layer_name: Layer name for DXF output
        point_color: AutoCAD color index for DXF points
        target_epsg: Target EPSG code for projection (DXF only)
        wgs84: Keep coordinates in WGS84 (DXF only)

    Raises:
        FileNotFoundError: If input file doesn't exist
        FileFormatError: If file format is invalid
        ValueError: If parameters are invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    input_file = validate_file_path(input_file, must_exist=True)

    # Validate parameters
    if elevation_units not in ["meters", "feet"]:
        raise ValueError("elevation_units must be 'meters' or 'feet'")

    valid_formats = ["dxf", "csv", "json", "txt"]
    if output_format not in valid_formats:
        raise ValueError(f"output_format must be one of: {valid_formats}")

    if output_format == "dxf" and point_color < 0:
        raise ValueError("point_color must be non-negative")

    # Set output file extension based on format
    extensions = {"dxf": ".dxf", "csv": ".csv", "json": ".json", "txt": ".txt"}
    output_file = ensure_file_extension(output_file, extensions[output_format])

    try:
        return _process_points_extraction(
            input_file=input_file,
            output_file=output_file,
            output_format=output_format,
            elevation_units=elevation_units,
            translate_to_origin=translate_to_origin,
            use_reference_point=use_reference_point,
            layer_name=layer_name,
            point_color=point_color,
            target_epsg=target_epsg,
            wgs84=wgs84,
        )
    except Exception as e:
        raise ProcessingError(f"Point extraction failed: {str(e)}") from e


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


def _write_dxf_points(
    points_3d: List[Tuple[float, float, float]],
    output_file: Path,
    layer_name: str,
    point_color: int,
) -> None:
    """Write points to DXF format"""
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

    # Create layer
    if layer_name not in doc.layers:
        doc.layers.add(layer_name, color=point_color)

    # Add points to DXF
    for x, y, z in points_3d:
        msp.add_point((x, y, z), dxfattribs={"layer": layer_name})

    # Save DXF
    doc.saveas(str(output_file))


def _write_csv_points(
    points: List[Tuple[float, float, float]], output_file: Path, elevation_units: str
) -> None:
    """Write points to CSV format"""
    with open(output_file, "w") as f:
        f.write("Latitude,Longitude,Elevation\n")

        for lon, lat, elev in points:
            # Convert elevation to meters for CSV output
            if elevation_units == "feet":
                elev_m = elev * FT_TO_M
            else:
                elev_m = elev

            f.write(f"{lat},{lon},{elev_m}\n")


def _write_json_points(
    points: List[Tuple[float, float, float]], output_file: Path, elevation_units: str
) -> None:
    """Write points to JSON format"""
    data = {
        "format": "KML Points Export",
        "elevation_units": elevation_units,
        "count": len(points),
        "points": [],
    }

    for i, (lon, lat, elev) in enumerate(points):
        point_data = {
            "id": i + 1,
            "longitude": lon,
            "latitude": lat,
            "elevation": elev,
            "elevation_units": elevation_units,
        }
        data["points"].append(point_data)

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)


def _write_txt_points(
    points: List[Tuple[float, float, float]], output_file: Path, elevation_units: str
) -> None:
    """Write points to TXT format"""
    with open(output_file, "w") as f:
        f.write("KML Points Export\n")
        f.write(f"Elevation units: {elevation_units}\n")
        f.write(f"Total points: {len(points)}\n")
        f.write("Format: Longitude, Latitude, Elevation\n")
        f.write("-" * 50 + "\n")

        for i, (lon, lat, elev) in enumerate(points):
            f.write(f"{i+1:3d}: {lon:11.6f}, {lat:10.6f}, {elev:8.2f}\n")


def _process_points_extraction(
    input_file: Path,
    output_file: Path,
    output_format: str,
    elevation_units: str,
    translate_to_origin: bool,
    use_reference_point: bool,
    layer_name: str,
    point_color: int,
    target_epsg: Optional[int],
    wgs84: bool,
) -> PointExtractionResult:
    """Process point extraction - internal implementation."""

    # Extract points from KML
    kml_points = _extract_kml_points(input_file)

    if not kml_points:
        raise ProcessingError(f"No points found in {input_file}")

    # Found {len(kml_points)} points in KML

    # For CSV, JSON, and TXT formats, we can output directly without projection
    if output_format in ["csv", "json", "txt"]:
        if output_format == "csv":
            _write_csv_points(kml_points, output_file, elevation_units)
        elif output_format == "json":
            _write_json_points(kml_points, output_file, elevation_units)
        elif output_format == "txt":
            _write_txt_points(kml_points, output_file, elevation_units)

        # Return result for CSV, JSON, TXT formats
        return PointExtractionResult(
            success=True,
            output_file=str(output_file),
            point_count=len(kml_points),
            format=output_format.upper(),
            elevation_units=elevation_units,
            coordinate_system="WGS84 (Lat/Lon)",
            details={"kml_points_found": len(kml_points)},
        )

    # For DXF format, we need to project coordinates
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
        if wgs84:
            # Keep elevation in original units when using WGS84
            z_ft = elev
        elif elevation_units == "meters":
            z_ft = elev * M_TO_FT
        else:  # already in feet
            z_ft = elev

        x_vals_ft.append(x_ft)
        y_vals_ft.append(y_ft)
        z_vals_ft.append(z_ft)

    # Determine reference point for translation
    if not translate_to_origin:
        ref_x, ref_y, ref_z = 0.0, 0.0, 0.0
    elif use_reference_point:
        # Use first point as reference (like latlong_to_dxf.py)
        ref_x, ref_y, ref_z = x_vals_ft[0], y_vals_ft[0], z_vals_ft[0]
        # Remove first point from output (like latlong_to_dxf.py)
        x_vals_ft = x_vals_ft[1:]
        y_vals_ft = y_vals_ft[1:]
        z_vals_ft = z_vals_ft[1:]
    else:
        # Use center of bounds as reference
        ref_x = (min(x_vals_ft) + max(x_vals_ft)) / 2.0
        ref_y = (min(y_vals_ft) + max(y_vals_ft)) / 2.0
        ref_z = min(z_vals_ft)  # Use minimum elevation as reference

    # Translate to local coordinates
    x_local = [x - ref_x for x in x_vals_ft]
    y_local = [y - ref_y for y in y_vals_ft]
    z_local = [z - ref_z for z in z_vals_ft]

    points_3d = list(zip(x_local, y_local, z_local))

    # Write DXF
    _write_dxf_points(points_3d, output_file, layer_name, point_color)

    # Determine coordinate system string
    if wgs84:
        coord_system = "degrees (WGS84)"
    elif target_epsg:
        coord_system = f"feet (EPSG:{target_epsg})"
    else:
        coord_system = "feet (auto-detected UTM zone)"

    # Build coordinate ranges
    coord_ranges = None
    if x_local and y_local and z_local:
        coord_ranges = {
            "x": (min(x_local), max(x_local)),
            "y": (min(y_local), max(y_local)),
            "z": (min(z_local), max(z_local)),
            "units": "degrees" if wgs84 else "ft",
        }

    # Build reference point if translated
    reference_point = None
    if translate_to_origin:
        reference_point = (ref_x, ref_y, ref_z)

    # Return result for DXF format
    return PointExtractionResult(
        success=True,
        output_file=str(output_file),
        point_count=len(points_3d),
        format="DXF",
        elevation_units=elevation_units,
        coordinate_system=coord_system,
        coordinate_ranges=coord_ranges,
        reference_point=reference_point,
        translated_to_origin=translate_to_origin,
        details={
            "kml_points_found": len(kml_points),
            "layer_name": layer_name,
            "point_color": point_color,
            "use_reference_point": use_reference_point,
            "wgs84": wgs84,
            "target_epsg": target_epsg,
        },
    )
