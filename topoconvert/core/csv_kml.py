"""Convert CSV file with lat/lon/elevation data to KML points.

Adapted from GPSGrid csv_to_kml.py
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.core.result_types import CSVToKMLResult


def convert_csv_to_kml(
    input_file: Path,
    output_file: Path,
    elevation_units: str = "meters",
    point_style: str = "circle",
    point_color: str = "ff00ff00",
    point_scale: float = 0.8,
    add_labels: bool = False,
    kml_name: Optional[str] = None,
    x_column: str = "Longitude",
    y_column: str = "Latitude",
    z_column: str = "Elevation",
) -> CSVToKMLResult:
    """Convert CSV survey data to KML format.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output KML file
        elevation_units: Units of elevation in CSV ('meters' or 'feet')
        point_style: Style for KML points ('circle', 'pin', 'square')
        point_color: Color in AABBGGRR format
        point_scale: Scale factor for points
        add_labels: Whether to add labels to points
        kml_name: Name for KML document (defaults to input filename)
        x_column: Column name for X/longitude
        y_column: Column name for Y/latitude
        z_column: Column name for Z/elevation

    Raises:
        FileNotFoundError: If input file doesn't exist
        FileFormatError: If CSV format is invalid
        ValueError: If parameters are invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    input_file = validate_file_path(input_file, must_exist=True)
    output_file = ensure_file_extension(output_file, ".kml")

    # Validate parameters
    if elevation_units not in ["meters", "feet"]:
        raise ValueError("elevation_units must be 'meters' or 'feet'")

    valid_styles = ["circle", "pin", "square"]
    if point_style not in valid_styles:
        raise ValueError(f"point_style must be one of: {valid_styles}")

    if len(point_color) != 8:
        raise ValueError("point_color must be 8 characters (AABBGGRR format)")

    try:
        # Validate color format
        int(point_color, 16)
    except ValueError:
        raise ValueError("point_color must be valid hexadecimal")

    if point_scale <= 0:
        raise ValueError("point_scale must be positive")

    try:
        return _process_csv_to_kml(
            input_file=input_file,
            output_file=output_file,
            elevation_units=elevation_units,
            point_style=point_style,
            point_color=point_color,
            point_scale=point_scale,
            add_labels=add_labels,
            kml_name=kml_name,
            x_column=x_column,
            y_column=y_column,
            z_column=z_column,
        )
    except Exception as e:
        raise ProcessingError(f"CSV to KML conversion failed: {str(e)}") from e


def _get_icon_url(style: str) -> str:
    """Get the appropriate icon URL for the point style"""
    icons = {
        "circle": "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png",
        "pin": "http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png",
        "square": "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png",
    }
    return icons.get(style, icons["circle"])


def _create_kml_header(
    name: str, style_id: str, color: str, scale: float, icon_url: str
) -> str:
    """Create KML header with style definition"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <description>GPS points converted from CSV</description>
    
    <Style id="{style_id}">
      <IconStyle>
        <color>{color}</color>
        <scale>{scale}</scale>
        <Icon>
          <href>{icon_url}</href>
        </Icon>
        <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
      </IconStyle>
      <LabelStyle>
        <scale>0.8</scale>
      </LabelStyle>
    </Style>
"""


def _create_placemark(
    lat: float,
    lon: float,
    elev: float,
    style_id: str,
    point_num: int,
    add_labels: bool,
    elev_units: str,
) -> str:
    """Create a KML Placemark for a single point"""
    elev_label = f"{elev:.1f} {elev_units}" if add_labels else f"Point {point_num}"

    return f"""    <Placemark>
      <name>{elev_label}</name>
      <description>Elevation: {elev:.2f} {elev_units}</description>
      <styleUrl>#{style_id}</styleUrl>
      <Point>
        <coordinates>{lon},{lat},{elev}</coordinates>
      </Point>
    </Placemark>
"""


def _process_csv_to_kml(
    input_file: Path,
    output_file: Path,
    elevation_units: str,
    point_style: str,
    point_color: str,
    point_scale: float,
    add_labels: bool,
    kml_name: Optional[str],
    x_column: str,
    y_column: str,
    z_column: str,
) -> CSVToKMLResult:
    """Process CSV to KML conversion - internal implementation."""

    # Read CSV file
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        raise FileFormatError(f"Error reading CSV file: {e}")

    # Validate required columns (x and y are required, z is optional)
    required_cols = [x_column, y_column]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise FileFormatError(
            f"Missing required columns: {missing_cols}. "
            f"Found columns: {list(df.columns)}"
        )

    # Check if elevation column exists
    has_elevation = z_column in df.columns
    # Track warnings
    warnings = []
    if not has_elevation:
        warnings.append(
            f"Elevation column '{z_column}' not found. Using 0 for all elevations."
        )

    if len(df) == 0:
        raise ProcessingError("CSV file is empty")

    # Found {len(df)} points in CSV

    # Set KML document name
    if kml_name is None:
        kml_name = input_file.stem

    # Get style parameters
    style_id = "gpsPointStyle"
    icon_url = _get_icon_url(point_style)

    # Create output KML
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Write header
            f.write(
                _create_kml_header(
                    kml_name, style_id, point_color, point_scale, icon_url
                )
            )

            # Write points
            valid_points = 0
            for idx, row in df.iterrows():
                lat = row[y_column]
                lon = row[x_column]
                elev = row[z_column] if has_elevation else 0.0

                # Validate coordinates
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    warnings.append(
                        f"Invalid coordinates at row {idx+1}: lat={lat}, lon={lon}"
                    )
                    continue

                placemark = _create_placemark(
                    lat, lon, elev, style_id, idx + 1, add_labels, elevation_units
                )
                f.write(placemark)
                valid_points += 1

            # Write footer
            f.write("  </Document>\n</kml>\n")

    except Exception as e:
        raise ProcessingError(f"Error writing KML file: {e}")

    # Build coordinate bounds
    lat_range = (df[y_column].min(), df[y_column].max())
    lon_range = (df[x_column].min(), df[x_column].max())

    coordinate_bounds = {"latitude": lat_range, "longitude": lon_range}

    if has_elevation:
        elev_range = (df[z_column].min(), df[z_column].max())
        coordinate_bounds["elevation"] = elev_range

    # Return result
    return CSVToKMLResult(
        success=True,
        output_file=str(output_file),
        valid_points=valid_points,
        elevation_units=elevation_units,
        point_style=point_style,
        has_labels=add_labels,
        coordinate_bounds=coordinate_bounds,
        warnings=warnings,
        details={
            "csv_points_found": len(df),
            "kml_name": kml_name,
            "point_color": point_color,
            "point_scale": point_scale,
            "x_column": x_column,
            "y_column": y_column,
            "z_column": z_column,
            "has_elevation": has_elevation,
        },
    )
