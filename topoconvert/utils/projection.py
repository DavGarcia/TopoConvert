"""Coordinate projection utilities for TopoConvert."""
from typing import List, Tuple, Union
import pyproj


def transform_coordinates(points: List[Tuple[float, float]], 
                         from_crs: Union[str, int],
                         to_crs: Union[str, int]) -> List[Tuple[float, float]]:
    """Transform coordinates between coordinate reference systems.
    
    Args:
        points: List of (x, y) or (lon, lat) tuples
        from_crs: Source CRS (EPSG code or proj string)
        to_crs: Target CRS (EPSG code or proj string)
        
    Returns:
        Transformed coordinates
    """
    # Implementation will be added later
    raise NotImplementedError("Coordinate transformation not yet implemented")


def get_utm_zone(lon: float, lat: float) -> str:
    """Determine UTM zone from longitude and latitude.
    
    Args:
        lon: Longitude in degrees
        lat: Latitude in degrees
        
    Returns:
        UTM zone string (e.g., '33N')
    """
    # Implementation will be added later
    raise NotImplementedError("UTM zone calculation not yet implemented")


def create_local_projection(center_lon: float, 
                           center_lat: float) -> pyproj.Proj:
    """Create a local projection centered at given coordinates.
    
    Args:
        center_lon: Center longitude
        center_lat: Center latitude
        
    Returns:
        Pyproj projection object
    """
    # Implementation will be added later
    raise NotImplementedError("Local projection creation not yet implemented")