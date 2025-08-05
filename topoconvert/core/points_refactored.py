"""Extract points from KML and save in various formats - Refactored version.

This is a demonstration of how to refactor core modules to return structured results
instead of using click.echo.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Callable

import ezdxf
from pyproj import Transformer

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.utils.projection import get_target_crs, get_transformer
from topoconvert.core.result_types import PointExtractionResult


# Constants remain the same
NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084
FT_TO_M = 0.3048


def extract_points_refactored(
    input_file: Path,
    output_file: Path,
    output_format: str = 'dxf',
    elevation_units: str = 'meters',
    translate_to_origin: bool = True,
    use_reference_point: bool = False,
    layer_name: str = 'GPS_POINTS',
    point_color: int = 7,
    target_epsg: Optional[int] = None,
    wgs84: bool = False,
    progress_callback: Optional[Callable] = None
) -> PointExtractionResult:
    """Extract points from KML and save in specified format.
    
    This refactored version returns a PointExtractionResult instead of 
    printing to console with click.echo.
    
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
        progress_callback: Optional callback for progress updates
        
    Returns:
        PointExtractionResult with details about the extraction
    """
    # Validate inputs (same as original)
    input_file = validate_file_path(input_file, must_exist=True)
    
    if elevation_units not in ['meters', 'feet']:
        raise ValueError("elevation_units must be 'meters' or 'feet'")
    
    valid_formats = ['dxf', 'csv', 'json', 'txt']
    if output_format not in valid_formats:
        raise ValueError(f"output_format must be one of: {valid_formats}")
    
    # Set output file extension based on format
    extensions = {'dxf': '.dxf', 'csv': '.csv', 'json': '.json', 'txt': '.txt'}
    output_file = ensure_file_extension(output_file, extensions[output_format])
    
    # Validate projection options for DXF format
    if output_format == 'dxf' and target_epsg and wgs84:
        raise ValueError("Cannot use both target_epsg and wgs84")
    
    # Initialize progress
    if progress_callback:
        progress_callback("Extracting points from KML", 0)
    
    # Extract points from KML (using same helper function)
    kml_points = _extract_kml_points(input_file)
    
    if not kml_points:
        raise ProcessingError(f"No points found in {input_file}")
    
    # Initialize result
    result = PointExtractionResult(
        success=True,
        output_file=str(output_file),
        point_count=len(kml_points),
        format=output_format,
        elevation_units=elevation_units
    )
    
    if progress_callback:
        progress_callback("Processing coordinates", 20)
    
    # For CSV, JSON, and TXT formats, we can output directly without projection
    if output_format in ['csv', 'json', 'txt']:
        if progress_callback:
            progress_callback(f"Writing {output_format.upper()} file", 80)
        
        # Write output file (using same helper functions)
        if output_format == 'csv':
            _write_csv_points(kml_points, output_file, elevation_units)
        elif output_format == 'json':
            _write_json_points(kml_points, output_file, elevation_units)
        elif output_format == 'txt':
            _write_txt_points(kml_points, output_file, elevation_units)
        
        # Set coordinate system info
        result.coordinate_system = "WGS84 (geographic)"
        
        # Calculate coordinate ranges
        lons = [p[0] for p in kml_points]
        lats = [p[1] for p in kml_points]
        elevs = [p[2] for p in kml_points]
        
        result.coordinate_ranges = {
            "longitude": (min(lons), max(lons)),
            "latitude": (min(lats), max(lats)),
            "elevation": (min(elevs), max(elevs))
        }
        
        if progress_callback:
            progress_callback("Complete", 100)
        
        return result
    
    # For DXF format, we need to project coordinates
    # (This would continue with the same logic as the original,
    # but populating the result object instead of using click.echo)
    
    # ... rest of DXF processing ...
    
    # Example of how to handle the reference point and translation info:
    if translate_to_origin and output_format == 'dxf':
        # After translation logic...
        result.translated_to_origin = True
        result.reference_point = (ref_x, ref_y, ref_z)  # Would come from actual logic
    
    # Set coordinate system info for DXF
    if output_format == 'dxf':
        if wgs84:
            result.coordinate_system = "WGS84 (degrees)"
        elif target_epsg:
            result.coordinate_system = f"EPSG:{target_epsg}"
        else:
            result.coordinate_system = "Auto-detected UTM zone"
    
    return result


# Helper functions remain the same
def _extract_kml_points(kml_path: Path) -> List[Tuple[float, float, float]]:
    """Extract points from KML file."""
    # Same implementation as original
    pass


def _write_csv_points(points: List[Tuple[float, float, float]], 
                     output_file: Path, elevation_units: str) -> None:
    """Write points to CSV format."""
    # Same implementation as original
    pass


def _write_json_points(points: List[Tuple[float, float, float]], 
                      output_file: Path, elevation_units: str) -> None:
    """Write points to JSON format."""
    # Same implementation as original
    pass


def _write_txt_points(points: List[Tuple[float, float, float]], 
                     output_file: Path, elevation_units: str) -> None:
    """Write points to TXT format."""
    # Same implementation as original
    pass