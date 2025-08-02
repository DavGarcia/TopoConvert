"""Generate 3D TIN mesh from KML point data.

Adapted from GPSGrid kml_to_mesh_dxf.py
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Callable

import click
import ezdxf
import numpy as np
from pyproj import Transformer
from scipy.spatial import Delaunay

from topoconvert.core.exceptions import FileFormatError, ProcessingError
from topoconvert.core.utils import validate_file_path, ensure_file_extension


NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084
FT_TO_M = 0.3048


def generate_mesh(
    input_file: Path,
    output_file: Path,
    elevation_units: str = 'meters',
    translate_to_origin: bool = True,
    use_reference_point: bool = False,
    layer_name: str = 'TIN_MESH',
    mesh_color: int = 8,
    add_wireframe: bool = False,
    wireframe_color: int = 7,
    progress_callback: Optional[Callable] = None
) -> None:
    """Generate 3D TIN mesh from KML point data.
    
    Args:
        input_file: Path to input KML file
        output_file: Path to output DXF file
        elevation_units: Units of elevation in KML ('meters' or 'feet')
        translate_to_origin: Whether to translate coordinates
        use_reference_point: Use first point as reference
        layer_name: Layer name for mesh faces
        mesh_color: AutoCAD color index for mesh faces
        add_wireframe: Whether to add wireframe edges
        wireframe_color: AutoCAD color index for wireframe
        progress_callback: Optional callback for progress updates
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        FileFormatError: If file format is invalid
        ValueError: If parameters are invalid
        ProcessingError: If processing fails
    """
    # Validate inputs
    input_file = validate_file_path(input_file, must_exist=True)
    output_file = ensure_file_extension(output_file, '.dxf')
    
    # Validate parameters
    if elevation_units not in ['meters', 'feet']:
        raise ValueError("elevation_units must be 'meters' or 'feet'")
    
    if mesh_color < 0 or wireframe_color < 0:
        raise ValueError("Color indices must be non-negative")
    
    try:
        _process_mesh_generation(
            input_file=input_file,
            output_file=output_file,
            elevation_units=elevation_units,
            translate_to_origin=translate_to_origin,
            use_reference_point=use_reference_point,
            layer_name=layer_name,
            mesh_color=mesh_color,
            add_wireframe=add_wireframe,
            wireframe_color=wireframe_color,
            progress_callback=progress_callback
        )
    except Exception as e:
        raise ProcessingError(f"Mesh generation failed: {str(e)}") from e


def _parse_coordinates(coord_text: str) -> Optional[Tuple[float, float, float]]:
    """Parse KML coordinate string (lon,lat,elev)"""
    parts = coord_text.strip().split(",")
    if len(parts) >= 2:
        lon = float(parts[0])
        lat = float(parts[1])
        elev = float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0
        return (lon, lat, elev)
    return None


def _extract_kml_points(kml_path: Path) -> List[Tuple[float, float, float]]:
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


def _create_mesh_dxf(points_3d: List[Tuple[float, float, float]], 
                    output_file: Path, layer_name: str, mesh_color: int,
                    add_wireframe: bool, wireframe_color: int,
                    progress_callback: Optional[Callable]) -> Tuple[int, int]:
    """Create DXF file with 3D mesh"""
    
    if progress_callback:
        progress_callback("Creating triangulation", 60)
    
    # Create Delaunay triangulation (only X,Y coordinates for 2D triangulation)
    points_2d = np.array([(x, y) for x, y, z in points_3d])
    
    # Check for duplicate points or colinear points
    if len(points_2d) < 3:
        raise ProcessingError(f"Need at least 3 points for triangulation, have {len(points_2d)}")
    
    try:
        tri = Delaunay(points_2d)
    except Exception as e:
        raise ProcessingError(f"Error creating triangulation: {e}")
    
    click.echo(f"Created triangulation with {len(tri.simplices)} triangles")
    
    if progress_callback:
        progress_callback("Writing DXF file", 80)
    
    # Create DXF
    doc = ezdxf.new('R2010')
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
    
    # Create layers
    if layer_name not in doc.layers:
        doc.layers.add(layer_name, color=mesh_color)
    
    wireframe_layer = None
    if add_wireframe:
        wireframe_layer = f"{layer_name}_WIREFRAME"
        if wireframe_layer not in doc.layers:
            doc.layers.add(wireframe_layer, color=wireframe_color)
    
    # Add mesh faces to DXF
    face_count = 0
    edge_set = set()  # For wireframe edges
    
    for simplex in tri.simplices:
        # Get the three vertices of the triangle
        i1, i2, i3 = simplex
        
        x1, y1, z1 = points_3d[i1]
        x2, y2, z2 = points_3d[i2]
        x3, y3, z3 = points_3d[i3]
        
        # Add 3D face
        msp.add_3dface([
            (x1, y1, z1),
            (x2, y2, z2),
            (x3, y3, z3),
            (x3, y3, z3)  # repeat last point for triangle
        ], dxfattribs={'layer': layer_name})
        
        face_count += 1
        
        # Collect edges for wireframe
        if add_wireframe:
            edges = [
                (min(i1, i2), max(i1, i2)),
                (min(i2, i3), max(i2, i3)),
                (min(i3, i1), max(i3, i1))
            ]
            edge_set.update(edges)
    
    # Add wireframe edges if requested
    edge_count = 0
    if add_wireframe and wireframe_layer:
        for i1, i2 in edge_set:
            x1, y1, z1 = points_3d[i1]
            x2, y2, z2 = points_3d[i2]
            
            msp.add_line((x1, y1, z1), (x2, y2, z2), 
                        dxfattribs={'layer': wireframe_layer})
            edge_count += 1
    
    # Save DXF
    doc.saveas(str(output_file))
    
    return face_count, edge_count


def _process_mesh_generation(
    input_file: Path,
    output_file: Path,
    elevation_units: str,
    translate_to_origin: bool,
    use_reference_point: bool,
    layer_name: str,
    mesh_color: int,
    add_wireframe: bool,
    wireframe_color: int,
    progress_callback: Optional[Callable]
) -> None:
    """Process mesh generation - internal implementation."""
    
    # Initialize progress
    if progress_callback:
        progress_callback("Extracting points from KML", 0)
    
    # Extract points from KML
    kml_points = _extract_kml_points(input_file)
    
    if not kml_points:
        raise ProcessingError(f"No points found in {input_file}")
    
    if len(kml_points) < 3:
        raise ProcessingError(f"Need at least 3 points for triangulation, found {len(kml_points)}")
    
    click.echo(f"Found {len(kml_points)} points in KML")
    
    if progress_callback:
        progress_callback("Projecting coordinates", 20)
    
    # Setup projection: WGS84 -> NAD83 / UTM Zone 14N
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:26914", always_xy=True)
    
    # Convert points to local coordinates
    x_vals_ft = []
    y_vals_ft = []
    z_vals_ft = []
    
    for lon, lat, elev in kml_points:
        # Project to UTM (meters)
        x_m, y_m = transformer.transform(lon, lat)
        
        # Convert to feet
        x_ft = x_m * M_TO_FT
        y_ft = y_m * M_TO_FT
        
        # Handle elevation units
        if elevation_units == "meters":
            z_ft = elev * M_TO_FT
        else:  # already in feet
            z_ft = elev
            
        x_vals_ft.append(x_ft)
        y_vals_ft.append(y_ft)
        z_vals_ft.append(z_ft)
    
    if progress_callback:
        progress_callback("Applying coordinate transformation", 40)
    
    # Determine reference point for translation
    if not translate_to_origin:
        ref_x, ref_y, ref_z = 0.0, 0.0, 0.0
        x_local = x_vals_ft
        y_local = y_vals_ft
        z_local = z_vals_ft
    elif use_reference_point:
        # Use first point as reference (like latlong_to_dxf.py)
        ref_x, ref_y, ref_z = x_vals_ft[0], y_vals_ft[0], z_vals_ft[0]
        # Translate all points (including reference point for mesh generation)
        x_local = [x - ref_x for x in x_vals_ft]
        y_local = [y - ref_y for y in y_vals_ft]
        z_local = [z - ref_z for z in z_vals_ft]
    else:
        # Use center of bounds as reference
        ref_x = (min(x_vals_ft) + max(x_vals_ft)) / 2.0
        ref_y = (min(y_vals_ft) + max(y_vals_ft)) / 2.0
        ref_z = min(z_vals_ft)  # Use minimum elevation as reference
        # Translate to local coordinates
        x_local = [x - ref_x for x in x_vals_ft]
        y_local = [y - ref_y for y in y_vals_ft]
        z_local = [z - ref_z for z in z_vals_ft]
    
    # Check if we have enough points for triangulation
    if len(x_local) < 3:
        raise ProcessingError(f"Need at least 3 points for triangulation, have {len(x_local)}")
    
    points_3d = list(zip(x_local, y_local, z_local))
    
    # Create mesh DXF
    face_count, edge_count = _create_mesh_dxf(
        points_3d, output_file, layer_name, mesh_color,
        add_wireframe, wireframe_color, progress_callback
    )
    
    # Print summary
    click.echo(f"\nCreated 3D TIN mesh DXF: {output_file}")
    click.echo(f"- {face_count} triangular faces")
    click.echo(f"- {len(points_3d)} vertices")
    click.echo(f"- Layer: {layer_name}")
    
    if add_wireframe:
        wireframe_layer = f"{layer_name}_WIREFRAME"
        click.echo(f"- {edge_count} wireframe edges")
        click.echo(f"- Wireframe layer: {wireframe_layer}")
    
    if translate_to_origin:
        if use_reference_point:
            click.echo(f"- Reference point (excluded): ({ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)")
            click.echo(f"- First point translated to origin")
        else:
            click.echo(f"- Translated to origin (reference: {ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)")
    
    click.echo(f"- Coordinates in feet (NAD83 / UTM Zone 14N projected)")
    
    # Print coordinate ranges
    if x_local and y_local and z_local:
        click.echo(f"- X range: {min(x_local):.1f} to {max(x_local):.1f} ft")
        click.echo(f"- Y range: {min(y_local):.1f} to {max(y_local):.1f} ft")
        click.echo(f"- Z range: {min(z_local):.1f} to {max(z_local):.1f} ft")
    
    if progress_callback:
        progress_callback("Complete", 100)