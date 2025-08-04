"""Generate GPS grid points within property boundaries.

Adapted from GPSGrid flexible_gps_grid.py
"""
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Callable

import click
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, Point
from scipy.spatial import ConvexHull
import alphashape
import concave_hull

from topoconvert.core.exceptions import ProcessingError, FileFormatError


NS = {"kml": "http://www.opengis.net/kml/2.2"}


def generate_gps_grid(
    input_file: Path,
    output_file: Path,
    input_type: str = 'auto',
    spacing: float = 40.0,
    buffer: float = 0.0,
    boundary_type: str = 'convex',
    alpha: float = 0.1,
    point_style: str = 'circle',
    point_color: str = 'ff00ff00',
    grid_name: str = 'GPS Grid',
    progress_callback: Optional[Callable] = None
) -> None:
    """
    Generate GPS grid points within property boundaries.
    
    Args:
        input_file: Input file (KML with polygons or CSV with points)
        output_file: Output KML file with grid points
        input_type: Input type ('auto', 'kml-polygon', 'csv-boundary', 'csv-extent')
        spacing: Grid spacing in feet
        buffer: Buffer distance in feet for csv-extent mode
        boundary_type: Boundary type for csv-boundary mode ('convex', 'concave')
        alpha: Alpha parameter for concave hull (smaller = more detailed)
        point_style: Point style in output KML
        point_color: Point color in AABBGGRR format
        grid_name: Name for the grid in output KML
        progress_callback: Optional progress callback
    """
    # Validate input
    input_file = Path(input_file)
    if not input_file.exists():
        raise FileFormatError(f"Input file not found: {input_file}")
    
    output_file = Path(output_file)
    
    # Auto-detect input type if needed
    if input_type == 'auto':
        if input_file.suffix.lower() == '.kml':
            input_type = 'kml-polygon'
        elif input_file.suffix.lower() == '.csv':
            # Try to detect CSV type by reading first few lines
            try:
                df = pd.read_csv(input_file, nrows=5)
                if 'Latitude' in df.columns and 'Longitude' in df.columns:
                    input_type = 'csv-boundary'
                else:
                    input_type = 'csv-extent'
            except:
                input_type = 'csv-boundary'
        else:
            raise FileFormatError(f"Cannot auto-detect input type for {input_file.suffix}")
    
    if progress_callback:
        progress_callback("Loading input data", 10)
    
    # Load boundary based on input type
    if input_type == 'kml-polygon':
        boundary_coords = _extract_polygon_from_kml(input_file)
        if not boundary_coords:
            raise ProcessingError("No polygon found in KML file")
    elif input_type == 'csv-boundary':
        boundary_coords = _create_boundary_from_csv(input_file, boundary_type, alpha)
    elif input_type == 'csv-extent':
        boundary_coords = _create_extent_boundary_from_csv(input_file, buffer)
    else:
        raise ValueError(f"Unknown input type: {input_type}")
    
    if len(boundary_coords) < 3:
        raise ProcessingError("Need at least 3 points to create a boundary")
    
    if progress_callback:
        progress_callback("Creating grid points", 40)
    
    # Generate grid points
    grid_points = _generate_grid_within_polygon(boundary_coords, spacing)
    
    if not grid_points:
        raise ProcessingError("No grid points generated within boundary")
    
    if progress_callback:
        progress_callback("Writing KML output", 80)
    
    # Write output KML
    _write_grid_kml(output_file, grid_points, boundary_coords, grid_name, 
                    point_style, point_color, spacing)
    
    # Summary
    click.echo(f"\nCreated GPS grid: {output_file}")
    click.echo(f"- {len(grid_points)} grid points")
    click.echo(f"- {spacing} ft spacing")
    click.echo(f"- Boundary type: {input_type}")
    if input_type == 'csv-extent' and buffer > 0:
        click.echo(f"- Buffer: {buffer} ft")
    
    if progress_callback:
        progress_callback("Complete", 100)


def _parse_coordinates_kml(coord_text: str) -> List[Tuple[float, float]]:
    """Parse KML coordinate string and return list of (lon, lat) pairs"""
    coords = []
    for token in coord_text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            lon = float(parts[0])
            lat = float(parts[1])
            coords.append((lon, lat))
    return coords


def _extract_polygon_from_kml(kml_path: Path) -> Optional[List[Tuple[float, float]]]:
    """Extract first polygon coordinates from KML file"""
    try:
        tree = ET.parse(str(kml_path))
        root = tree.getroot()
        
        # Look for Polygon in Placemarks
        for pm in root.findall(".//kml:Placemark", NS):
            # Check for Polygon
            polygon_elem = pm.find(".//kml:Polygon", NS)
            if polygon_elem is not None:
                # Get outer boundary
                outer_boundary = polygon_elem.find(".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", NS)
                if outer_boundary is not None and outer_boundary.text:
                    coords = _parse_coordinates_kml(outer_boundary.text)
                    if len(coords) >= 3:
                        return coords
                        
            # Also check for LineString (might be a boundary line)
            linestring_elem = pm.find(".//kml:LineString", NS)
            if linestring_elem is not None:
                coord_elem = linestring_elem.find("kml:coordinates", NS)
                if coord_elem is not None and coord_elem.text:
                    coords = _parse_coordinates_kml(coord_elem.text)
                    if len(coords) >= 3:
                        # Close the polygon if not already closed
                        if coords[0] != coords[-1]:
                            coords.append(coords[0])
                        return coords
        
        return None
    except Exception as e:
        raise ProcessingError(f"Error reading KML file: {e}")


def _read_csv_points(csv_path: Path) -> List[Tuple[float, float]]:
    """Read lat/lon points from CSV file"""
    try:
        df = pd.read_csv(csv_path)
        
        # Check for required columns
        if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
            raise FileFormatError("CSV must have 'Latitude' and 'Longitude' columns")
        
        # Extract coordinates
        points = []
        for _, row in df.iterrows():
            lat = float(row['Latitude'])
            lon = float(row['Longitude'])
            points.append((lon, lat))
        
        return points
    except Exception as e:
        raise ProcessingError(f"Error reading CSV file: {e}")


def _create_boundary_from_csv(csv_path: Path, boundary_type: str, alpha: float) -> List[Tuple[float, float]]:
    """Create boundary polygon from CSV points"""
    points = _read_csv_points(csv_path)
    
    if len(points) < 3:
        raise ProcessingError("Need at least 3 points to create boundary")
    
    if boundary_type == 'convex':
        # Create convex hull
        points_array = np.array(points)
        hull = ConvexHull(points_array)
        boundary_coords = [points[i] for i in hull.vertices]
        # Close the polygon
        boundary_coords.append(boundary_coords[0])
    else:
        # Create concave hull using alphashape
        points_array = np.array(points)
        
        # Create alpha shape
        alpha_shape = alphashape.alphashape(points_array, alpha)
        
        # Extract boundary coordinates
        if hasattr(alpha_shape, 'exterior'):
            boundary_coords = list(alpha_shape.exterior.coords)
        else:
            # Fallback to convex hull if alphashape fails
            hull = ConvexHull(points_array)
            boundary_coords = [points[i] for i in hull.vertices]
            boundary_coords.append(boundary_coords[0])
    
    return boundary_coords


def _create_extent_boundary_from_csv(csv_path: Path, buffer_ft: float) -> List[Tuple[float, float]]:
    """Create rectangular boundary from CSV points extent with buffer"""
    points = _read_csv_points(csv_path)
    
    if not points:
        raise ProcessingError("No points found in CSV")
    
    # Find extent
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    
    min_lon = min(lons)
    max_lon = max(lons)
    min_lat = min(lats)
    max_lat = max(lats)
    
    # Convert buffer from feet to approximate degrees
    # At mid-latitudes, 1 degree longitude ≈ 288,200 feet
    # 1 degree latitude ≈ 364,000 feet
    avg_lat = (min_lat + max_lat) / 2
    lon_buffer = buffer_ft / (288200 * math.cos(math.radians(avg_lat)))
    lat_buffer = buffer_ft / 364000
    
    # Create buffered rectangle
    boundary_coords = [
        (min_lon - lon_buffer, min_lat - lat_buffer),
        (max_lon + lon_buffer, min_lat - lat_buffer),
        (max_lon + lon_buffer, max_lat + lat_buffer),
        (min_lon - lon_buffer, max_lat + lat_buffer),
        (min_lon - lon_buffer, min_lat - lat_buffer)  # Close
    ]
    
    return boundary_coords


def _generate_grid_within_polygon(boundary_coords: List[Tuple[float, float]], 
                                 spacing_ft: float) -> List[Tuple[float, float, int]]:
    """Generate regular grid points within polygon boundary"""
    # Create shapely polygon
    polygon = Polygon(boundary_coords)
    
    # Find bounds
    lons = [p[0] for p in boundary_coords]
    lats = [p[1] for p in boundary_coords]
    
    min_lon = min(lons)
    max_lon = max(lons)
    min_lat = min(lats)
    max_lat = max(lats)
    
    # Convert spacing to degrees (approximate)
    avg_lat = (min_lat + max_lat) / 2
    lon_spacing = spacing_ft / (288200 * math.cos(math.radians(avg_lat)))
    lat_spacing = spacing_ft / 364000
    
    # Generate grid
    grid_points = []
    point_id = 1
    
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            point = Point(lon, lat)
            if polygon.contains(point):
                grid_points.append((lon, lat, point_id))
                point_id += 1
            lon += lon_spacing
        lat += lat_spacing
    
    return grid_points


def _write_grid_kml(output_path: Path, 
                   grid_points: List[Tuple[float, float, int]],
                   boundary_coords: List[Tuple[float, float]],
                   grid_name: str,
                   point_style: str,
                   point_color: str,
                   spacing: float) -> None:
    """Write grid points and boundary to KML file"""
    # Create KML structure
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    doc = ET.SubElement(kml, 'Document')
    
    # Add name
    name_elem = ET.SubElement(doc, 'name')
    name_elem.text = grid_name
    
    # Add description
    desc_elem = ET.SubElement(doc, 'description')
    desc_elem.text = f'GPS grid with {len(grid_points)} points, {spacing} ft spacing'
    
    # Add styles
    # Grid point style
    style = ET.SubElement(doc, 'Style', id='gridPointStyle')
    icon_style = ET.SubElement(style, 'IconStyle')
    color_elem = ET.SubElement(icon_style, 'color')
    color_elem.text = point_color
    scale = ET.SubElement(icon_style, 'scale')
    scale.text = '0.8'
    
    icon = ET.SubElement(icon_style, 'Icon')
    href = ET.SubElement(icon, 'href')
    if point_style == 'circle':
        href.text = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
    elif point_style == 'pin':
        href.text = 'http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png'
    else:  # square
        href.text = 'http://maps.google.com/mapfiles/kml/shapes/placemark_square.png'
    
    # Boundary style
    boundary_style = ET.SubElement(doc, 'Style', id='boundaryStyle')
    line_style = ET.SubElement(boundary_style, 'LineStyle')
    line_color = ET.SubElement(line_style, 'color')
    line_color.text = 'ff0000ff'  # Red
    line_width = ET.SubElement(line_style, 'width')
    line_width.text = '2'
    poly_style = ET.SubElement(boundary_style, 'PolyStyle')
    poly_fill = ET.SubElement(poly_style, 'fill')
    poly_fill.text = '0'
    
    # Add boundary folder
    boundary_folder = ET.SubElement(doc, 'Folder')
    folder_name = ET.SubElement(boundary_folder, 'name')
    folder_name.text = 'Property Boundary'
    
    # Add boundary polygon
    pm = ET.SubElement(boundary_folder, 'Placemark')
    pm_name = ET.SubElement(pm, 'name')
    pm_name.text = 'Boundary'
    style_url = ET.SubElement(pm, 'styleUrl')
    style_url.text = '#boundaryStyle'
    
    polygon = ET.SubElement(pm, 'Polygon')
    outer = ET.SubElement(polygon, 'outerBoundaryIs')
    ring = ET.SubElement(outer, 'LinearRing')
    coords = ET.SubElement(ring, 'coordinates')
    coords.text = ' '.join([f"{lon},{lat},0" for lon, lat in boundary_coords])
    
    # Add grid points folder
    grid_folder = ET.SubElement(doc, 'Folder')
    folder_name = ET.SubElement(grid_folder, 'name')
    folder_name.text = 'Grid Points'
    
    # Add each grid point
    for lon, lat, point_id in grid_points:
        pm = ET.SubElement(grid_folder, 'Placemark')
        pm_name = ET.SubElement(pm, 'name')
        pm_name.text = f'Grid {point_id}'
        style_url = ET.SubElement(pm, 'styleUrl')
        style_url.text = '#gridPointStyle'
        
        point = ET.SubElement(pm, 'Point')
        coords = ET.SubElement(point, 'coordinates')
        coords.text = f"{lon},{lat},0"
    
    # Write to file
    tree = ET.ElementTree(kml)
    tree.write(str(output_path), encoding='UTF-8', xml_declaration=True)