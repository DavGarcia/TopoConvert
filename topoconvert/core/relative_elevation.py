"""Convert KML elevation data to relative elevations with customizable reference methods."""

import xml.etree.ElementTree as ET
import statistics
from pathlib import Path
from typing import List, Tuple, Optional

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension
from topoconvert.core.result_types import RelativeElevationResult

# Unit conversion constants
M_TO_FT = 3.28084
FT_TO_M = 0.3048


def convert_to_relative_elevation(
    input_file: Path,
    output_file: Path,
    elevation_units: str = "meters",
    output_units: str = "feet", 
    reference_method: str = "min",
    label_format: str = "{value:.1f} {unit}",
    apply_style: bool = True,
) -> RelativeElevationResult:
    """Convert KML elevations to relative values based on reference method.
    
    Args:
        input_file: Path to input KML file
        output_file: Path to output KML file
        elevation_units: Input elevation units ('meters' or 'feet')
        output_units: Output elevation units ('meters' or 'feet')
        reference_method: Reference calculation method ('min', 'max', or 'mean')
        label_format: Label format string with {value} and {unit} placeholders
        apply_style: Whether to apply consistent KML styling
        
    Returns:
        RelativeElevationResult with processing details
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        FileFormatError: If KML format is invalid
        ValueError: If parameters are invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    input_file = validate_file_path(input_file, must_exist=True)
    output_file = ensure_file_extension(output_file, ".kml")
    
    # Validate parameters
    valid_units = ["meters", "feet"]
    if elevation_units not in valid_units:
        raise ValueError(f"elevation_units must be one of: {valid_units}")
    if output_units not in valid_units:
        raise ValueError(f"output_units must be one of: {valid_units}")
        
    valid_methods = ["min", "max", "mean"]
    if reference_method not in valid_methods:
        raise ValueError(f"reference_method must be one of: {valid_methods}")
        
    if not isinstance(apply_style, bool):
        raise ValueError("apply_style must be a boolean")
    
    try:
        return _process_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units=elevation_units,
            output_units=output_units,
            reference_method=reference_method,
            label_format=label_format,
            apply_style=apply_style,
        )
    except Exception as e:
        raise ProcessingError(f"Relative elevation conversion failed: {str(e)}") from e


def _extract_elevation_points(kml_file: Path) -> List[Tuple[float, float, float]]:
    """Extract points with elevation data from KML file.
    
    Args:
        kml_file: Path to KML file
        
    Returns:
        List of (longitude, latitude, elevation) tuples
        
    Raises:
        ProcessingError: If no valid points found or file cannot be parsed
    """
    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ProcessingError(f"Invalid KML file format: {e}")
    except Exception as e:
        raise ProcessingError(f"Error reading KML file: {e}")
    
    # Define namespaces
    namespaces = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }
    
    points = []
    
    # Find all placemarks with point coordinates
    placemarks = root.findall('.//kml:Placemark', namespaces)
    
    for placemark in placemarks:
        point = placemark.find('.//kml:Point', namespaces)
        if point is not None:
            coordinates_elem = point.find('kml:coordinates', namespaces)
            if coordinates_elem is not None and coordinates_elem.text:
                coord_text = coordinates_elem.text.strip()
                try:
                    # Parse coordinates: "longitude,latitude,elevation"
                    coord_parts = [float(x) for x in coord_text.split(',')]
                    if len(coord_parts) >= 3:
                        lon, lat, elev = coord_parts[0], coord_parts[1], coord_parts[2]
                        points.append((lon, lat, elev))
                    elif len(coord_parts) == 2:
                        # Skip points without elevation data
                        continue
                except (ValueError, IndexError):
                    # Skip invalid coordinate data
                    continue
    
    if not points:
        raise ProcessingError("No points found in KML file")
    
    # Check if any points have elevation data
    if all(point[2] == 0.0 for point in points):
        raise ProcessingError("No elevation data found in KML points")
    
    return points


def _convert_elevation_units(elevation: float, from_units: str, to_units: str) -> float:
    """Convert elevation between meters and feet.
    
    Args:
        elevation: Elevation value to convert
        from_units: Source units ('meters' or 'feet')
        to_units: Target units ('meters' or 'feet')
        
    Returns:
        Converted elevation value
        
    Raises:
        ValueError: If units are not supported
    """
    if from_units == to_units:
        return elevation
        
    if from_units == "meters" and to_units == "feet":
        return elevation * M_TO_FT
    elif from_units == "feet" and to_units == "meters":
        return elevation * FT_TO_M
    else:
        raise ValueError(f"Unsupported unit conversion from {from_units} to {to_units}")


def _calculate_reference_value(elevations: List[float], method: str) -> float:
    """Calculate reference elevation value based on method.
    
    Args:
        elevations: List of elevation values
        method: Reference calculation method ('min', 'max', or 'mean')
        
    Returns:
        Reference elevation value
        
    Raises:
        ValueError: If method is not supported or elevation list is empty
    """
    if not elevations:
        raise ValueError("No elevation values provided")
        
    if method == "min":
        return min(elevations)
    elif method == "max":
        return max(elevations)
    elif method == "mean":
        return statistics.mean(elevations)
    else:
        raise ValueError(f"Unsupported reference method: {method}")


def _apply_relative_transform(elevations: List[float], reference: float) -> List[float]:
    """Transform elevations to relative values by subtracting reference.
    
    Args:
        elevations: List of elevation values
        reference: Reference value to subtract from each elevation
        
    Returns:
        List of relative elevation values
    """
    return [elev - reference for elev in elevations]


def _update_kml_labels(
    kml_file: Path, 
    output_file: Path,
    relative_elevations: List[float],
    label_format: str,
    output_units: str,
    apply_style: bool
) -> None:
    """Update KML point labels with relative elevation values.
    
    Args:
        kml_file: Path to input KML file
        output_file: Path to output KML file
        relative_elevations: List of relative elevation values
        label_format: Label format string with {value} and {unit} placeholders
        output_units: Units for output labels
        apply_style: Whether to apply elevation styling
    """
    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ProcessingError(f"Invalid KML file format: {e}")
    
    # Define namespaces
    namespaces = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }
    
    # Find document element for style insertion
    document = root.find('.//kml:Document', namespaces)
    if document is None:
        # Create document if it doesn't exist
        document = ET.SubElement(root, 'Document')
        # Move existing elements into document
        for child in list(root):
            if child != document:
                root.remove(child)
                document.append(child)
    
    # Apply elevation style if requested
    if apply_style:
        _apply_elevation_style(document, namespaces)
    
    # Find placemarks with valid elevation points and update their labels
    placemarks = root.findall('.//kml:Placemark', namespaces)
    valid_placemark_index = 0
    
    for placemark in placemarks:
        point = placemark.find('.//kml:Point', namespaces)
        if point is not None:
            coordinates_elem = point.find('kml:coordinates', namespaces)
            if coordinates_elem is not None and coordinates_elem.text:
                coord_text = coordinates_elem.text.strip()
                try:
                    # Parse coordinates to check if valid
                    coord_parts = [float(x) for x in coord_text.split(',')]
                    if len(coord_parts) >= 3:
                        # This placemark has valid elevation data
                        if valid_placemark_index < len(relative_elevations):
                            rel_elev = relative_elevations[valid_placemark_index]
                            
                            # Update name element
                            name_elem = placemark.find('kml:name', namespaces)
                            if name_elem is None:
                                name_elem = ET.SubElement(placemark, 'name')
                            
                            # Format label
                            unit_display = "ft" if output_units == "feet" else "m"
                            formatted_label = label_format.format(value=rel_elev, unit=unit_display)
                            name_elem.text = formatted_label
                            
                            # Set style reference if style applied
                            if apply_style:
                                style_url = placemark.find('kml:styleUrl', namespaces)
                                if style_url is None:
                                    style_url = ET.SubElement(placemark, 'styleUrl')
                                style_url.text = '#elevLabels'
                            
                            valid_placemark_index += 1
                except (ValueError, IndexError):
                    # Skip invalid coordinates
                    continue
    
    # Write updated KML
    try:
        # Register namespace to avoid ns0 prefixes
        ET.register_namespace('', 'http://www.opengis.net/kml/2.2')
        ET.register_namespace('gx', 'http://www.google.com/kml/ext/2.2')
        
        tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    except Exception as e:
        raise ProcessingError(f"Error writing output KML file: {e}")


def _apply_elevation_style(document: ET.Element, namespaces: dict) -> None:
    """Apply consistent styling for elevation labels.
    
    Args:
        document: KML Document element
        namespaces: XML namespaces dictionary
    """
    # Check if style already exists
    existing_style = document.find('.//kml:Style[@id="elevLabels"]', namespaces)
    if existing_style is not None:
        return  # Style already exists
    
    # Create elevation label style
    style = ET.SubElement(document, 'Style')
    style.set('id', 'elevLabels')
    
    # Icon style
    icon_style = ET.SubElement(style, 'IconStyle')
    icon_scale = ET.SubElement(icon_style, 'scale')
    icon_scale.text = '0.5'
    
    # Label style
    label_style = ET.SubElement(style, 'LabelStyle')
    label_scale = ET.SubElement(label_style, 'scale')
    label_scale.text = '0.8'


def _process_relative_elevation(
    input_file: Path,
    output_file: Path,
    elevation_units: str,
    output_units: str,
    reference_method: str,
    label_format: str,
    apply_style: bool,
) -> RelativeElevationResult:
    """Internal processing function for relative elevation conversion."""
    
    # Extract elevation points from KML
    points = _extract_elevation_points(input_file)
    elevations = [point[2] for point in points]
    
    # Convert elevations to output units
    converted_elevations = [
        _convert_elevation_units(elev, elevation_units, output_units) 
        for elev in elevations
    ]
    
    # Calculate reference value
    reference_value = _calculate_reference_value(converted_elevations, reference_method)
    
    # Apply relative transformation
    relative_elevations = _apply_relative_transform(converted_elevations, reference_value)
    
    # Update KML with new labels
    _update_kml_labels(
        input_file, output_file, relative_elevations, 
        label_format, output_units, apply_style
    )
    
    # Calculate ranges
    original_range = (min(converted_elevations), max(converted_elevations))
    relative_range = (min(relative_elevations), max(relative_elevations))
    
    # Build result
    return RelativeElevationResult(
        success=True,
        output_file=str(output_file),
        point_count=len(points),
        input_elevation_units=elevation_units,
        output_elevation_units=output_units,
        reference_method=reference_method,
        reference_value=reference_value,
        elevation_range=original_range,
        relative_range=relative_range,
        label_format=label_format,
        style_applied=apply_style,
        details={
            "points_processed": len(points),
            "original_elevations_range": f"{original_range[0]:.1f} to {original_range[1]:.1f} {output_units}",
            "relative_elevations_range": f"{relative_range[0]:.1f} to {relative_range[1]:.1f} {output_units}",
            "reference_calculation": f"{reference_method} = {reference_value:.1f} {output_units}",
            "unit_conversion": f"{elevation_units} -> {output_units}",
        },
    )