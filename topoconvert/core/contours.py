"""Generate contour lines from KML point data and save as DXF.

Adapted from GPSGrid kml_points_to_contours_dxf.py
"""

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import matplotlib

matplotlib.use("Agg")  # For headless environments
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.enums import TextEntityAlignment
from scipy.interpolate import griddata

from topoconvert.core.exceptions import (
    FileFormatError,
    ProcessingError,
    ContourGenerationError,
)
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer
from topoconvert.core.result_types import ContourGenerationResult


NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084


def generate_contours(
    input_file: Path,
    output_file: Path,
    elevation_units: str = "meters",
    contour_interval: float = 1.0,
    grid_resolution: int = 100,
    add_labels: bool = False,
    label_height: float = 2.0,
    translate_to_origin: bool = True,
    target_epsg: Optional[int] = None,
    wgs84: bool = False,
) -> ContourGenerationResult:
    """Generate contour lines from KML point data.

    Args:
        input_file: Path to input KML file
        output_file: Path to output DXF file
        elevation_units: Units of elevation in KML ('meters' or 'feet')
        contour_interval: Contour interval in feet
        grid_resolution: Grid resolution for interpolation
        add_labels: Whether to add elevation labels
        label_height: Text height for labels
        translate_to_origin: Whether to translate coordinates to origin
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

    if contour_interval <= 0:
        raise ValueError("contour_interval must be positive")

    if grid_resolution <= 0:
        raise ValueError("grid_resolution must be positive")

    if label_height <= 0:
        raise ValueError("label_height must be positive")

    try:
        return _process_contours(
            input_file=input_file,
            output_file=output_file,
            elevation_units=elevation_units,
            contour_interval=contour_interval,
            grid_resolution=grid_resolution,
            add_labels=add_labels,
            label_height=label_height,
            translate_to_origin=translate_to_origin,
            target_epsg=target_epsg,
            wgs84=wgs84,
        )
    except Exception as e:
        raise ProcessingError(f"Contour generation failed: {str(e)}") from e


def _parse_coordinates(coord_text: str) -> Optional[Tuple[float, float, float]]:
    """Parse KML coordinate string (lon,lat,elev)"""
    parts = coord_text.strip().split(",")
    if len(parts) >= 2:
        lon = float(parts[0])
        lat = float(parts[1])
        elev = float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0
        return (lon, lat, elev)
    return None


def _extract_points(kml_path: Path) -> List[Tuple[float, float, float]]:
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


def _split_path_on_jumps(points2d, max_gap):
    """Split a contour path into sub-paths when consecutive points
    are separated by more than max_gap."""
    if len(points2d) < 2:
        return [points2d]

    subpaths = []
    current = [points2d[0]]

    for i in range(1, len(points2d)):
        x0, y0 = points2d[i - 1]
        x1, y1 = points2d[i]
        dist = math.hypot(x1 - x0, y1 - y0)

        if dist <= max_gap:
            current.append(points2d[i])
        else:
            subpaths.append(current)
            current = [points2d[i]]

    if current:
        subpaths.append(current)

    return subpaths


def _process_contours(
    input_file: Path,
    output_file: Path,
    elevation_units: str,
    contour_interval: float,
    grid_resolution: int,
    add_labels: bool,
    label_height: float,
    translate_to_origin: bool,
    target_epsg: Optional[int],
    wgs84: bool,
) -> ContourGenerationResult:
    """Process contours - internal implementation."""

    # Extract points from KML
    kml_points = _extract_points(input_file)

    if not kml_points:
        raise ProcessingError(f"No points found in {input_file}")

    if len(kml_points) < 2:
        raise ProcessingError(
            f"Need at least 2 points for contour generation, found {len(kml_points)}"
        )

    # Found {len(kml_points)} points in KML

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
    else:
        # Use center of bounds as reference
        ref_x = (min(x_vals_ft) + max(x_vals_ft)) / 2.0
        ref_y = (min(y_vals_ft) + max(y_vals_ft)) / 2.0
        ref_z = min(z_vals_ft)  # Use minimum elevation as reference

    # Translate to local coordinates
    x_local = [x - ref_x for x in x_vals_ft]
    y_local = [y - ref_y for y in y_vals_ft]
    z_local = [z - ref_z for z in z_vals_ft]

    # Create interpolation grid
    x_min, x_max = min(x_local), max(x_local)
    y_min, y_max = min(y_local), max(y_local)

    xi = np.linspace(x_min, x_max, grid_resolution)
    yi = np.linspace(y_min, y_max, grid_resolution)
    Xg, Yg = np.meshgrid(xi, yi)

    # Interpolate elevation data
    points = list(zip(x_local, y_local))
    try:
        Zg = griddata(points, z_local, (Xg, Yg), method="cubic")
    except Exception as e:
        raise ContourGenerationError(f"Interpolation failed: {e}")

    # Generate contour levels
    z_min, z_max = min(z_local), max(z_local)
    contour_start = math.floor(z_min / contour_interval) * contour_interval
    contour_end = math.ceil(z_max / contour_interval) * contour_interval
    contour_levels = np.arange(
        contour_start, contour_end + contour_interval, contour_interval
    )

    # Generating contours from {contour_start:.1f} to {contour_end:.1f} ft at {contour_interval} ft intervals

    # Create contours
    cs = plt.contour(Xg, Yg, Zg, levels=contour_levels, colors="black")

    # Prepare distance threshold for splitting paths
    dx = (x_max - x_min) / (grid_resolution - 1)
    dy = (y_max - y_min) / (grid_resolution - 1)
    grid_diag = math.hypot(dx, dy)
    max_gap = 2.0 * grid_diag

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

    # Extract and write contour lines
    contour_count = 0

    # Process each contour level
    for level_idx, level_value in enumerate(cs.levels):
        if level_idx >= len(cs.allsegs):
            continue

        contour_line = cs.allsegs[level_idx]

        # Create layer for this elevation
        layer_name = f"ELEV_{level_value:.0f}FT"
        if layer_name not in doc.layers:
            doc.layers.add(layer_name)

        # Process each segment at this level
        for segment in contour_line:
            if len(segment) < 2:
                continue

            # Convert to list of (x, y) tuples
            points2d = [(float(pt[0]), float(pt[1])) for pt in segment]

            # Split on large jumps
            subpaths = _split_path_on_jumps(points2d, max_gap)

            for subpath in subpaths:
                if len(subpath) < 2:
                    continue

                # Create 3D polyline
                msp.add_polyline3d(
                    [(pt[0], pt[1], level_value) for pt in subpath],
                    dxfattribs={"layer": layer_name},
                )
                contour_count += 1

                # Add label if requested
                if add_labels:
                    mid_idx = len(subpath) // 2
                    mid_x, mid_y = subpath[mid_idx]

                    label = msp.add_text(
                        text=f"{int(level_value)} ft",
                        dxfattribs={
                            "layer": layer_name,
                            "height": label_height,
                        },
                    )
                    label.set_placement(
                        (mid_x, mid_y, level_value),
                        align=TextEntityAlignment.MIDDLE_CENTER,
                    )

    # Save DXF
    doc.saveas(str(output_file))

    # Determine coordinate system string
    if wgs84:
        coord_system = "degrees (WGS84)"
    elif target_epsg:
        coord_system = f"feet (EPSG:{target_epsg})"
    else:
        coord_system = "feet (auto-detected UTM zone)"

    # Build reference point if translated
    reference_point = None
    if translate_to_origin:
        reference_point = (ref_x, ref_y, ref_z)

    # Calculate elevation range
    if z_local:
        elevation_range = (ref_z, ref_z + max(z_local))
    else:
        elevation_range = (ref_z, ref_z)

    # Return result
    return ContourGenerationResult(
        success=True,
        output_file=str(output_file),
        contour_count=contour_count,
        elevation_levels=len(contour_levels),
        contour_interval=contour_interval,
        elevation_range=elevation_range,
        coordinate_system=coord_system,
        reference_point=reference_point,
        translated_to_origin=translate_to_origin,
        details={
            "kml_points_found": len(kml_points),
            "grid_resolution": grid_resolution,
            "add_labels": add_labels,
            "label_height": label_height,
            "wgs84": wgs84,
            "target_epsg": target_epsg,
            "contour_start": contour_start,
            "contour_end": contour_end,
        },
    )
