"""Merge multiple CSV files into a single DXF with 3D points.

Adapted from GPSGrid combined_dxf.py
"""

from pathlib import Path
from typing import List, Optional, Tuple

import ezdxf
import pandas as pd
from pyproj import Transformer

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer
from topoconvert.core.result_types import CombinedDXFResult


M_TO_FT = 3.28084


def merge_csv_to_dxf(
    csv_files: List[Path],
    output_file: Path,
    target_epsg: Optional[int] = None,
    wgs84: bool = False,
) -> CombinedDXFResult:
    """Merge multiple CSV files into a single DXF with 3D points.

    Each CSV file is expected to have Latitude, Longitude, and Elevation columns.
    Points from each CSV will be placed on separate layers with different colors.

    Args:
        csv_files: List of paths to input CSV files
        output_file: Path to output DXF file
        target_epsg: Target EPSG code for projection (default: auto-detect UTM)
        wgs84: Keep coordinates in WGS84 (no projection)

    Raises:
        FileNotFoundError: If any input file doesn't exist
        FileFormatError: If file format is invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    validated_files = []
    for csv_file in csv_files:
        validated_files.append(validate_file_path(csv_file, must_exist=True))

    output_file = ensure_file_extension(output_file, ".dxf")

    if not validated_files:
        raise ValueError("At least one CSV file is required")

    try:
        return _process_csv_merge(
            csv_files=validated_files,
            output_file=output_file,
            target_epsg=target_epsg,
            wgs84=wgs84,
        )
    except Exception as e:
        raise ProcessingError(f"CSV merge failed: {str(e)}") from e


def _read_and_transform_csv(
    csv_file: Path, transformer: Transformer, wgs84: bool = False
) -> Tuple[pd.DataFrame, bool]:
    """Read CSV file and transform coordinates to feet"""
    try:
        df = pd.read_csv(str(csv_file))
    except Exception as e:
        raise FileFormatError(f"Error reading CSV file {csv_file}: {e}")

    # Check for required columns
    required_columns = ["Latitude", "Longitude"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise FileFormatError(f"Missing columns in {csv_file}: {missing_columns}")

    # Check if elevation column exists
    has_elevation = "Elevation" in df.columns

    x_vals_ft = []
    y_vals_ft = []
    z_vals_ft = []

    # Handle elevation data if available, otherwise use 0.0
    if has_elevation:
        elevation_data = df["Elevation"]
    else:
        elevation_data = [0.0] * len(df)

    for lat, lon, elev_m in zip(df["Latitude"], df["Longitude"], elevation_data):
        # Transform coordinates
        x_proj, y_proj = transformer.transform(lon, lat)

        # Convert to feet if projected (UTM is in meters)
        if not wgs84:
            x_ft = x_proj * M_TO_FT
            y_ft = y_proj * M_TO_FT
            z_ft = elev_m * M_TO_FT
        else:
            # Keep in degrees for WGS84
            x_ft = x_proj
            y_ft = y_proj
            z_ft = elev_m

        x_vals_ft.append(x_ft)
        y_vals_ft.append(y_ft)
        z_vals_ft.append(z_ft)

    df["X_ft"] = x_vals_ft
    df["Y_ft"] = y_vals_ft
    df["Z_ft"] = z_vals_ft

    return df, has_elevation


def _process_csv_merge(
    csv_files: List[Path], output_file: Path, target_epsg: Optional[int], wgs84: bool
) -> CombinedDXFResult:
    """Process CSV merge - internal implementation."""

    # Determine target CRS using first CSV file's first point
    sample_df = pd.read_csv(str(csv_files[0]))
    if (
        "Latitude" in sample_df.columns
        and "Longitude" in sample_df.columns
        and len(sample_df) > 0
    ):
        sample_point = (sample_df["Longitude"].iloc[0], sample_df["Latitude"].iloc[0])
        target_crs = get_target_crs(target_epsg, wgs84, sample_point)
    else:
        raise ProcessingError("No valid coordinates found in first CSV file")

    # Setup transformer
    transformer = get_transformer(4326, target_crs)

    # We'll accumulate all X/Y/Z values to find the global min corner
    all_x, all_y, all_z = [], [], []

    # Keep track of data for each CSV
    datasets = []

    # Read & transform each CSV
    for i, csv_file in enumerate(csv_files):
        df, has_elevation = _read_and_transform_csv(csv_file, transformer, wgs84)

        # Accumulate for global min
        all_x.extend(df["X_ft"])
        all_y.extend(df["Y_ft"])
        all_z.extend(df["Z_ft"])

        basename = csv_file.stem
        # Line moved above

        elevation_msg = (
            " (with elevation)" if has_elevation else " (elevation set to 0.0)"
        )
        # Store for result reporting
        datasets.append((basename, df, elevation_msg))

    # Compute global min corner
    global_min_x = min(all_x) if all_x else 0.0
    global_min_y = min(all_y) if all_y else 0.0
    global_min_z = min(all_z) if all_z else 0.0

    # Create a single DXF
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

    # Color list for different layers
    color_list = [1, 2, 3, 4, 5, 6, 7, 140, 141, 42, 43, 180, 210]

    # For each CSV, create a new layer, shift coords, add points
    total_points = 0
    layers_created = []
    for i, (basename, df, _) in enumerate(datasets):
        color_idx = color_list[i % len(color_list)]
        layer_name = f"{basename}_POINTS"

        # Create a new layer
        doc.layers.new(name=layer_name, dxfattribs={"color": color_idx})

        # Shift coords so global min corner is (0,0,0)
        df["X_local"] = df["X_ft"] - global_min_x
        df["Y_local"] = df["Y_ft"] - global_min_y
        df["Z_local"] = df["Z_ft"] - global_min_z

        # Add points
        for x, y, z in zip(df["X_local"], df["Y_local"], df["Z_local"]):
            msp.add_point((x, y, z), dxfattribs={"layer": layer_name})

        total_points += len(df)
        layers_created.append(layer_name)

    # Save the combined file
    doc.saveas(str(output_file))

    # Build coordinate system description
    if wgs84:
        coord_system = "WGS84 (degrees)"
    elif target_epsg:
        coord_system = f"EPSG:{target_epsg} (feet)"
    else:
        coord_system = "Auto-detected UTM zone (feet)"

    # Build result details
    details = {
        "datasets": [(basename, len(df), msg) for basename, df, msg in datasets],
        "coordinate_ranges": {},
    }

    # Add coordinate ranges if available
    if all_x and all_y and all_z:
        x_range = max(all_x) - global_min_x
        y_range = max(all_y) - global_min_y
        z_range = max(all_z) - global_min_z

        if wgs84:
            details["coordinate_ranges"] = {
                "x": (0.0, x_range),
                "y": (0.0, y_range),
                "z": (0.0, z_range),
                "units": {"x": "degrees", "y": "degrees", "z": "meters"},
            }
        else:
            details["coordinate_ranges"] = {
                "x": (0.0, x_range),
                "y": (0.0, y_range),
                "z": (0.0, z_range),
                "units": {"x": "feet", "y": "feet", "z": "feet"},
            }

    # Return structured result
    return CombinedDXFResult(
        success=True,
        output_file=str(output_file),
        input_file_count=len(datasets),
        total_points=total_points,
        layers_created=layers_created,
        coordinate_system=coord_system,
        reference_point=(global_min_x, global_min_y, global_min_z),
        translated_to_origin=True,
        details=details,
    )
