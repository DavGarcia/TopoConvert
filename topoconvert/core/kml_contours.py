"""Convert KML contour LineStrings to DXF format.

Adapted from GPSGrid kml_contours_to_dxf.py
"""

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ezdxf
from ezdxf.enums import TextEntityAlignment
from pyproj import Transformer

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.result_types import KMLContoursResult
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer


M_TO_FT = 3.28084
NS = {"kml": "http://www.opengis.net/kml/2.2"}


def convert_kml_contours_to_dxf(
    input_file: Path,
    output_file: Path,
    z_source: str = "auto",
    z_units: str = "meters",
    target_epsg: Optional[int] = None,
    add_labels: bool = False,
    layer_prefix: str = "CT_",
    decimals: int = 1,
    z_field: Optional[str] = None,
    altitude_tolerance: float = 1e-6,
    translate_to_origin: bool = True,
    target_epsg_feet: bool = False,
    label_height: float = 6.0,
    wgs84: bool = False,
) -> KMLContoursResult:
    """Convert KML contour LineStrings to DXF format.

    Args:
        input_file: Path to input KML file
        output_file: Path to output DXF file
        z_source: Where to read contour elevation ('auto', 'altitude', 'extended')
        z_units: Units of Z in KML ('meters' or 'feet')
        target_epsg: EPSG code for projection (default: auto-detect UTM)
        add_labels: Add text labels with elevation
        layer_prefix: Prefix for per-elevation layers
        decimals: Decimal places for elevation text and layer names
        z_field: ExtendedData field name to prefer for elevation
        altitude_tolerance: Tolerance for constant altitude along contour
        translate_to_origin: Translate coordinates to origin
        target_epsg_feet: Whether target EPSG coordinates are in feet
        label_height: Height of text labels in drawing units
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
    if z_source not in ["auto", "altitude", "extended"]:
        raise ValueError("z_source must be 'auto', 'altitude', or 'extended'")

    if z_units not in ["meters", "feet"]:
        raise ValueError("z_units must be 'meters' or 'feet'")

    try:
        return _process_kml_contours_conversion(
            input_file=input_file,
            output_file=output_file,
            z_source=z_source,
            z_units=z_units,
            target_epsg=target_epsg,
            add_labels=add_labels,
            layer_prefix=layer_prefix,
            decimals=decimals,
            z_field=z_field,
            altitude_tolerance=altitude_tolerance,
            translate_to_origin=translate_to_origin,
            target_epsg_feet=target_epsg_feet,
            label_height=label_height,
            wgs84=wgs84,
        )
    except Exception as e:
        raise ProcessingError(f"KML contours conversion failed: {str(e)}") from e


def _get_text(el: Optional[ET.Element]) -> str:
    """Get text content from XML element"""
    return (el.text or "").strip() if el is not None else ""


def _parse_coordinates(coord_text: str) -> List[Tuple[float, float, Optional[float]]]:
    """Parse KML coordinate string"""
    pts = []
    for token in coord_text.strip().split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        x = float(parts[0])
        y = float(parts[1])
        z = float(parts[2]) if len(parts) >= 3 and parts[2] else None
        pts.append((x, y, z))
    return pts


def _placemark_extended_data(pm: ET.Element) -> Dict[str, str]:
    """Extract ExtendedData from placemark"""
    data: Dict[str, str] = {}
    for data_el in pm.findall(".//kml:ExtendedData/kml:Data", NS):
        name = data_el.get("name") or ""
        val = _get_text(data_el.find("kml:value", NS))
        if name:
            data[name] = val
    for sdata in pm.findall(".//kml:ExtendedData/kml:SchemaData/kml:SimpleData", NS):
        name = sdata.get("name") or ""
        val = _get_text(sdata)
        if name:
            data[name] = val
    return data


def _detect_constant_altitude(
    points: List[Tuple[float, float, Optional[float]]], tol: float
) -> Optional[float]:
    """Check if all points have same altitude within tolerance"""
    zs = [p[2] for p in points if p[2] is not None]
    if not zs:
        return None
    z0 = zs[0]
    for z in zs[1:]:
        if abs(z - z0) > tol:
            return None  # varies too much; not a true contour
    return z0


def _pick_extended_z(
    data: Dict[str, str], prefer: Optional[str] = None
) -> Optional[float]:
    """Pick elevation value from ExtendedData"""
    keys = []
    if prefer:
        keys.append(prefer)
    # Common field names
    keys += ["elev", "elevation", "Elevation", "contour", "Contour", "Z", "z"]
    for k in keys:
        if k in data:
            try:
                return float(str(data[k]).strip())
            except ValueError:
                continue
    return None


def _as_feet(z_value: float, input_units: str) -> float:
    """Convert elevation to feet"""
    if input_units == "meters":
        return z_value * M_TO_FT
    return z_value


def _midpoint_xy(points_xy: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Calculate length-weighted midpoint along polyline"""
    if len(points_xy) < 2:
        return points_xy[0] if points_xy else (0.0, 0.0)

    seg_lengths = []
    cum = [0.0]
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points_xy, points_xy[1:]):
        d = math.hypot(x2 - x1, y2 - y1)
        seg_lengths.append(d)
        total += d
        cum.append(total)

    target = total / 2.0
    # Find segment containing the midpoint
    for i, (d, cstart) in enumerate(zip(seg_lengths, cum[:-1])):
        cend = cstart + d
        if target <= cend and d > 0:
            t = (target - cstart) / d
            x1, y1 = points_xy[i]
            x2, y2 = points_xy[i + 1]
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    return points_xy[len(points_xy) // 2]


def _collect_linestrings(
    pm: ET.Element,
) -> List[List[Tuple[float, float, Optional[float]]]]:
    """Collect all LineString coordinates from placemark"""
    lines: List[List[Tuple[float, float, Optional[float]]]] = []
    # Direct LineString(s)
    for ls in pm.findall(".//kml:LineString", NS):
        coords = _get_text(ls.find("kml:coordinates", NS))
        if coords:
            lines.append(_parse_coordinates(coords))
    return lines


def _build_transformer(target_epsg: Optional[int]) -> Optional[Transformer]:
    """Build coordinate transformer"""
    if target_epsg is None:
        return None
    # WGS84 lon/lat to target EPSG
    return Transformer.from_crs("EPSG:4326", f"EPSG:{target_epsg}", always_xy=True)


def _project_xy(
    transformer: Optional[Transformer],
    lon: float,
    lat: float,
    to_feet: bool = False,
    wgs84: bool = False,
) -> Tuple[float, float]:
    """Project coordinates using transformer"""
    if transformer is None:
        return (lon, lat)
    x, y = transformer.transform(lon, lat)
    if to_feet and not wgs84:
        # Convert from meters to feet only for projected coordinates
        x *= M_TO_FT
        y *= M_TO_FT
    return (x, y)


def _process_kml_contours_conversion(
    input_file: Path,
    output_file: Path,
    z_source: str,
    z_units: str,
    target_epsg: Optional[int],
    add_labels: bool,
    layer_prefix: str,
    decimals: int,
    z_field: Optional[str],
    altitude_tolerance: float,
    translate_to_origin: bool,
    target_epsg_feet: bool,
    label_height: float = 6.0,
    wgs84: bool = False,
) -> KMLContoursResult:
    """Process KML contours conversion - internal implementation."""

    try:
        tree = ET.parse(str(input_file))
    except ET.ParseError as e:
        raise FileFormatError(f"Invalid KML file: {e}")

    root = tree.getroot()

    # Find first coordinate to determine UTM zone if needed
    sample_point = None
    if not wgs84 and target_epsg is None:
        for pm in root.findall(".//kml:Placemark", NS):
            lines = _collect_linestrings(pm)
            if lines and lines[0]:
                lon, lat, _ = lines[0][0]
                sample_point = (lon, lat)
                break

    # Determine target CRS
    if wgs84:
        target_crs = get_target_crs(None, True, (0, 0))  # WGS84
        transformer = None  # No transformation needed
    else:
        target_crs = get_target_crs(target_epsg, False, sample_point or (0, 0))
        transformer = get_transformer(4326, target_crs)

    # Create DXF document
    doc = ezdxf.new(setup=True)
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

    # First pass: collect all points to find bounds/reference point
    all_points = []
    if translate_to_origin:
        for pm in root.findall(".//kml:Placemark", NS):
            lines = _collect_linestrings(pm)
            for pts in lines:
                for lon, lat, _z in pts:
                    x, y = _project_xy(transformer, lon, lat, target_epsg_feet, wgs84)
                    all_points.append((x, y))

    # Determine reference point (use center of bounds)
    ref_x, ref_y = 0.0, 0.0
    if translate_to_origin and all_points:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        ref_x = (min(xs) + max(xs)) / 2.0
        ref_y = (min(ys) + max(ys)) / 2.0

    # Iterate placemarks
    pms = root.findall(".//kml:Placemark", NS)
    count = 0
    missing_z = 0

    for i, pm in enumerate(pms):
        lines = _collect_linestrings(pm)
        if not lines:
            continue

        # Determine Z once per placemark
        z_ft: Optional[float] = None

        if z_source in ("altitude", "auto"):
            # Require constant altitude along LineString
            z_alt: Optional[float] = None
            for pts in lines:
                zc = _detect_constant_altitude(pts, altitude_tolerance)
                if zc is not None:
                    z_alt = zc
                    break
            if z_alt is not None:
                z_ft = _as_feet(z_alt, z_units)

        if z_ft is None and z_source in ("extended", "auto"):
            data = _placemark_extended_data(pm)
            z_ext = _pick_extended_z(data, prefer=z_field)
            if z_ext is not None:
                z_ft = _as_feet(z_ext, z_units)

        if z_ft is None:
            missing_z += 1
            continue

        layer_name = f"{layer_prefix}{round(z_ft, decimals):.{decimals}f}ft"
        if layer_name not in doc.layers:
            doc.layers.add(layer_name)

        # Create geometry
        for pts in lines:
            # Project XY and translate to local origin
            xy = []
            for lon, lat, _z in pts:
                x, y = _project_xy(transformer, lon, lat, target_epsg_feet, wgs84)
                # Translate to local origin
                x_local = x - ref_x
                y_local = y - ref_y
                xy.append((x_local, y_local))

            # LWPOLYLINE supports constant elevation component
            lw = msp.add_lwpolyline(xy, dxfattribs={"layer": layer_name})
            lw.dxf.elevation = z_ft  # constant Z
            count += 1

            if add_labels and xy:
                mx, my = _midpoint_xy(xy)
                label = msp.add_text(
                    f"{round(z_ft, decimals):.{decimals}f} ft",
                    dxfattribs={"layer": layer_name, "height": label_height},
                )
                label.set_placement(
                    (mx, my, z_ft), align=TextEntityAlignment.MIDDLE_CENTER
                )

    doc.saveas(str(output_file))

    # Determine coordinate system and units
    if wgs84:
        coord_system = "lon/lat degrees (WGS84)"
        xy_units = "degrees"
    elif target_epsg:
        coord_system = f"EPSG:{target_epsg}"
        xy_units = "feet" if target_epsg_feet else "target CRS units"
    else:
        coord_system = "auto-detected UTM zone"
        xy_units = "feet"

    # Return result
    return KMLContoursResult(
        success=True,
        output_file=str(output_file),
        contour_count=count,
        missing_elevations=missing_z,
        coordinate_system=coord_system,
        xy_units=xy_units,
        z_units="feet",
        reference_point=(ref_x, ref_y) if translate_to_origin and all_points else None,
        translated_to_origin=translate_to_origin and all_points,
        details={
            "z_source": z_source,
            "z_units_input": z_units,
            "add_labels": add_labels,
            "layer_prefix": layer_prefix,
            "decimals": decimals,
            "z_field": z_field,
            "target_epsg": target_epsg,
            "wgs84": wgs84,
        },
    )
