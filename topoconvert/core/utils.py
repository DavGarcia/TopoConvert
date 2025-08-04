"""Common utility functions for TopoConvert."""
import click
from pathlib import Path
from typing import Union, Callable, Optional
import numpy as np


def validate_file_path(path: Union[str, Path], must_exist: bool = True) -> Path:
    """Validate and return a Path object.
    
    Args:
        path: File path to validate
        must_exist: Whether the file must exist
        
    Returns:
        Path object
        
    Raises:
        FileNotFoundError: If must_exist=True and file doesn't exist
        ValueError: If path is invalid
    """
    try:
        path_obj = Path(path)
    except Exception as e:
        raise ValueError(f"Invalid path: {path}") from e
    
    if must_exist and not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    return path_obj


def ensure_file_extension(path: Union[str, Path], extension: str) -> Path:
    """Ensure file has the specified extension.
    
    Args:
        path: File path
        extension: Extension to ensure (with or without dot)
        
    Returns:
        Path with correct extension
    """
    path_obj = Path(path)
    if not extension.startswith('.'):
        extension = '.' + extension
    
    if path_obj.suffix.lower() != extension.lower():
        path_obj = path_obj.with_suffix(extension)
    
    return path_obj


def convert_elevation_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert elevation between meters and feet.
    
    Args:
        value: Elevation value
        from_unit: Source unit ('meters' or 'feet')
        to_unit: Target unit ('meters' or 'feet')
        
    Returns:
        Converted value
        
    Raises:
        ValueError: If units are invalid
    """
    if from_unit == to_unit:
        return value
    
    valid_units = {'meters', 'feet'}
    if from_unit not in valid_units or to_unit not in valid_units:
        raise ValueError(f"Invalid units. Must be one of: {valid_units}")
    
    if from_unit == 'meters' and to_unit == 'feet':
        return value * 3.28084
    elif from_unit == 'feet' and to_unit == 'meters':
        return value / 3.28084
    
    return value


def create_progress_callback(
    label: str = "Processing",
    length: Optional[int] = None,
    show: bool = True
) -> Callable:
    """Create a progress callback for long operations.
    
    Args:
        label: Progress bar label
        length: Total number of items (None for indeterminate)
        show: Whether to show progress
        
    Returns:
        Progress callback function
    """
    if not show:
        # Return a no-op function
        no_op = lambda *args, **kwargs: None
        no_op.close = lambda: None
        return no_op
    
    # For simple percentage-based progress updates
    def callback(message: str = "", percent: int = 0):
        """Update progress with a message and percentage."""
        # This is a placeholder - the actual implementation should use
        # the progress tracking from the core modules
        pass
    
    callback.close = lambda: None
    
    return callback


def meters_to_feet(meters: float) -> float:
    """Convert meters to feet."""
    return meters * 3.28084


def feet_to_meters(feet: float) -> float:
    """Convert feet to meters."""
    return feet / 3.28084


def parse_color_string(color: str) -> tuple:
    """Parse AABBGGRR color string to RGBA tuple.
    
    Args:
        color: Color in AABBGGRR format
        
    Returns:
        Tuple of (r, g, b, a) values 0-255
    """
    if len(color) != 8:
        raise ValueError("Color must be 8 characters (AABBGGRR)")
    
    try:
        aa = int(color[0:2], 16)
        bb = int(color[2:4], 16)
        gg = int(color[4:6], 16)
        rr = int(color[6:8], 16)
        return (rr, gg, bb, aa)
    except ValueError:
        raise ValueError("Invalid color format. Use AABBGGRR hex format")


def format_coordinates(x: float, y: float, precision: int = 6) -> str:
    """Format coordinates for display.
    
    Args:
        x: X coordinate
        y: Y coordinate
        precision: Decimal places
        
    Returns:
        Formatted coordinate string
    """
    return f"({x:.{precision}f}, {y:.{precision}f})"


def calculate_bounds(points: list) -> tuple:
    """Calculate bounding box of points.
    
    Args:
        points: List of (x, y) or (x, y, z) tuples
        
    Returns:
        Tuple of (min_x, min_y, max_x, max_y)
    """
    if not points:
        raise ValueError("No points provided")
    
    points_array = np.array(points)
    min_x = np.min(points_array[:, 0])
    max_x = np.max(points_array[:, 0])
    min_y = np.min(points_array[:, 1])
    max_y = np.max(points_array[:, 1])
    
    return (min_x, min_y, max_x, max_y)