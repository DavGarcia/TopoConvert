"""Coordinate projection utilities for TopoConvert."""
from typing import List, Tuple, Union, Optional
from pyproj import CRS, Transformer


def get_target_crs(target_epsg: Optional[int], 
                   wgs84: bool, 
                   sample_point: Tuple[float, float]) -> CRS:
    """Determine the target coordinate reference system based on user options.
    
    Args:
        target_epsg: Explicit EPSG code from --target-epsg option
        wgs84: Flag from --wgs84 option to keep coordinates in WGS84
        sample_point: (longitude, latitude) tuple for auto-detection
        
    Returns:
        pyproj.CRS object for the target coordinate system
        
    Raises:
        ValueError: If both target_epsg and wgs84 are specified
    """
    if target_epsg and wgs84:
        raise ValueError("--target-epsg and --wgs84 are mutually exclusive")
    
    if wgs84:
        return CRS.from_epsg(4326)
    
    if target_epsg:
        return CRS.from_epsg(target_epsg)
    
    # Auto-detect UTM zone
    lon, lat = sample_point
    zone = detect_utm_zone(lon, lat)
    hemisphere = "north" if lat >= 0 else "south"
    
    # Create UTM CRS using proj4 string
    proj4_string = f"+proj=utm +zone={zone} +datum=WGS84 +units=m +no_defs"
    if hemisphere == "south":
        proj4_string += " +south"
    
    return CRS.from_proj4(proj4_string)


def detect_utm_zone(longitude: float, latitude: float) -> int:
    """Calculate appropriate UTM zone from geographic coordinates.
    
    Args:
        longitude: Longitude in degrees (-180 to 180)
        latitude: Latitude in degrees (-90 to 90)
        
    Returns:
        UTM zone number (1-60)
    """
    # Handle edge case at 180/-180 degrees
    if longitude == 180.0:
        longitude = -180.0
    
    # Calculate zone: 6-degree bands starting at -180
    zone = int((longitude + 180) / 6) + 1
    
    # Ensure zone is in valid range
    zone = max(1, min(60, zone))
    
    return zone


def get_transformer(source_crs: Union[int, CRS], 
                    target_crs: Union[int, CRS]) -> Transformer:
    """Create a coordinate transformer between two CRS.
    
    Args:
        source_crs: Source coordinate system (EPSG code or CRS object)
        target_crs: Target coordinate system (EPSG code or CRS object)
        
    Returns:
        pyproj.Transformer object configured with always_xy=True
    """
    # Convert to CRS objects if needed
    if isinstance(source_crs, int):
        source_crs = CRS.from_epsg(source_crs)
    if isinstance(target_crs, int):
        target_crs = CRS.from_epsg(target_crs)
    
    # Create transformer with consistent coordinate ordering
    return Transformer.from_crs(source_crs, target_crs, always_xy=True)


def transform_coordinates(points: List[Tuple[float, float]], 
                         from_crs: Union[str, int],
                         to_crs: Union[str, int]) -> List[Tuple[float, float]]:
    """Transform a list of coordinates between coordinate reference systems.
    
    Args:
        points: List of (x, y) or (lon, lat) tuples
        from_crs: Source CRS (EPSG code or proj string)
        to_crs: Target CRS (EPSG code or proj string)
        
    Returns:
        List of transformed coordinate tuples
    """
    if not points:
        return []
    
    # Create transformer
    transformer = get_transformer(from_crs, to_crs)
    
    # Transform all points
    transformed = []
    for x, y in points:
        tx, ty = transformer.transform(x, y)
        transformed.append((tx, ty))
    
    return transformed


# Deprecated functions for backward compatibility
def get_utm_zone(lon: float, lat: float) -> str:
    """Determine UTM zone from longitude and latitude.
    
    DEPRECATED: Use detect_utm_zone() instead.
    
    Args:
        lon: Longitude in degrees
        lat: Latitude in degrees
        
    Returns:
        UTM zone string (e.g., '33N')
    """
    zone = detect_utm_zone(lon, lat)
    hemisphere = 'N' if lat >= 0 else 'S'
    return f"{zone}{hemisphere}"


def create_local_projection(center_lon: float, 
                           center_lat: float) -> CRS:
    """Create a local projection centered at given coordinates.
    
    DEPRECATED: Use get_target_crs() with auto-detection instead.
    
    Args:
        center_lon: Center longitude
        center_lat: Center latitude
        
    Returns:
        CRS object for local UTM projection
    """
    return get_target_crs(None, False, (center_lon, center_lat))