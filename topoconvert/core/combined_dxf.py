"""Merge multiple CSV files into a single DXF with 3D points.

Adapted from GPSGrid combined_dxf.py
"""
import os
from pathlib import Path
from typing import List, Optional, Callable

import click
import ezdxf
import pandas as pd
from pyproj import Transformer

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer


M_TO_FT = 3.28084


def merge_csv_to_dxf(
    csv_files: List[Path],
    output_file: Path,
    target_epsg: Optional[int] = None,
    wgs84: bool = False,
    progress_callback: Optional[Callable] = None
) -> None:
    """Merge multiple CSV files into a single DXF with 3D points.
    
    Each CSV file is expected to have Latitude, Longitude, and Elevation columns.
    Points from each CSV will be placed on separate layers with different colors.
    
    Args:
        csv_files: List of paths to input CSV files
        output_file: Path to output DXF file
        target_epsg: Target EPSG code for projection (default: auto-detect UTM)
        wgs84: Keep coordinates in WGS84 (no projection)
        progress_callback: Optional callback for progress updates
    
    Raises:
        FileNotFoundError: If any input file doesn't exist
        FileFormatError: If file format is invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    validated_files = []
    for csv_file in csv_files:
        validated_files.append(validate_file_path(csv_file, must_exist=True))
    
    output_file = ensure_file_extension(output_file, '.dxf')
    
    if not validated_files:
        raise ValueError("At least one CSV file is required")
    
    try:
        _process_csv_merge(
            csv_files=validated_files,
            output_file=output_file,
            target_epsg=target_epsg,
            wgs84=wgs84,
            progress_callback=progress_callback
        )
    except Exception as e:
        raise ProcessingError(f"CSV merge failed: {str(e)}") from e


def _read_and_transform_csv(csv_file: Path, transformer: Transformer, wgs84: bool = False) -> pd.DataFrame:
    """Read CSV file and transform coordinates to feet"""
    try:
        df = pd.read_csv(str(csv_file))
    except Exception as e:
        raise FileFormatError(f"Error reading CSV file {csv_file}: {e}")
    
    # Check for required columns
    required_columns = ['Latitude', 'Longitude', 'Elevation']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise FileFormatError(f"Missing columns in {csv_file}: {missing_columns}")
    
    x_vals_ft = []
    y_vals_ft = []
    z_vals_ft = []
    
    for lat, lon, elev_m in zip(df["Latitude"], df["Longitude"], df["Elevation"]):
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
    
    return df


def _process_csv_merge(
    csv_files: List[Path],
    output_file: Path,
    target_epsg: Optional[int],
    wgs84: bool,
    progress_callback: Optional[Callable]
) -> None:
    """Process CSV merge - internal implementation."""
    
    # Initialize progress
    if progress_callback:
        progress_callback("Setting up coordinate transformation", 0)
    
    # Determine target CRS using first CSV file's first point
    sample_df = pd.read_csv(str(csv_files[0]))
    if 'Latitude' in sample_df.columns and 'Longitude' in sample_df.columns and len(sample_df) > 0:
        sample_point = (sample_df['Longitude'].iloc[0], sample_df['Latitude'].iloc[0])
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
    total_files = len(csv_files)
    for i, csv_file in enumerate(csv_files):
        if progress_callback:
            progress_callback(f"Processing {csv_file.name}", int(20 + (i / total_files) * 40))
        
        df = _read_and_transform_csv(csv_file, transformer, wgs84)
        
        # Accumulate for global min
        all_x.extend(df["X_ft"])
        all_y.extend(df["Y_ft"])
        all_z.extend(df["Z_ft"])
        
        basename = csv_file.stem
        datasets.append((basename, df))
        
        click.echo(f"Processed {csv_file.name}: {len(df)} points")
    
    if progress_callback:
        progress_callback("Computing coordinate bounds", 60)
    
    # Compute global min corner
    global_min_x = min(all_x) if all_x else 0.0
    global_min_y = min(all_y) if all_y else 0.0
    global_min_z = min(all_z) if all_z else 0.0
    
    if progress_callback:
        progress_callback("Creating DXF file", 70)
    
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
    for i, (basename, df) in enumerate(datasets):
        if progress_callback:
            progress_callback(f"Adding layer {basename}", int(70 + (i / len(datasets)) * 25))
        
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
        click.echo(f"Added layer {layer_name}: {len(df)} points (color {color_idx})")
    
    if progress_callback:
        progress_callback("Saving DXF file", 95)
    
    # Save the combined file
    doc.saveas(str(output_file))
    
    # Print summary
    click.echo(f"\nCreated merged DXF: {output_file}")
    click.echo(f"- {len(datasets)} input files")
    click.echo(f"- {total_points} total points")
    if wgs84:
        click.echo(f"- Global reference point: ({global_min_x:.6f}, {global_min_y:.6f}, {global_min_z:.2f})")
    else:
        click.echo(f"- Global reference point: ({global_min_x:.2f}, {global_min_y:.2f}, {global_min_z:.2f} ft)")
    # Output coordinate system info
    if wgs84:
        click.echo("- Coordinates in degrees (WGS84)")
    elif target_epsg:
        click.echo(f"- Coordinates in feet (EPSG:{target_epsg})")
    else:
        click.echo("- Coordinates in feet (auto-detected UTM zone)")
    
    # Print coordinate ranges after translation
    if all_x and all_y and all_z:
        x_range = max(all_x) - global_min_x
        y_range = max(all_y) - global_min_y
        z_range = max(all_z) - global_min_z
        if wgs84:
            click.echo(f"- X range: 0.0 to {x_range:.6f} degrees")
            click.echo(f"- Y range: 0.0 to {y_range:.6f} degrees")
            click.echo(f"- Z range: 0.0 to {z_range:.1f} m")  # CSV elevations are always in meters
        else:
            click.echo(f"- X range: 0.0 to {x_range:.1f} ft")
            click.echo(f"- Y range: 0.0 to {y_range:.1f} ft")
            click.echo(f"- Z range: 0.0 to {z_range:.1f} ft")
    
    if progress_callback:
        progress_callback("Complete", 100)