"""Generate slope heatmap from elevation data.

Adapted from GPSGrid kml_to_slope_heatmap.py
"""
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional, Callable

import click
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.patches import Polygon as MplPolygon
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pyproj import Transformer
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

from topoconvert.core.exceptions import ProcessingError, FileFormatError


NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084


def generate_slope_heatmap(
    input_file: Path,
    output_file: Path,
    elevation_units: str = 'meters',
    grid_resolution: int = 200,
    slope_units: str = 'degrees',
    run_length: float = 10.0,
    max_slope: Optional[float] = None,
    colormap: str = 'RdYlGn_r',
    dpi: int = 150,
    smooth: float = 1.0,
    show_contours: bool = False,
    contour_interval: float = 5.0,
    figsize: List[float] = [10, 8],
    target_slope: Optional[float] = None,
    stats_position: str = 'outside',
    progress_callback: Optional[Callable] = None
) -> None:
    """
    Generate a slope heatmap from KML point data.
    
    Args:
        input_file: Input KML file with points
        output_file: Output PNG file
        elevation_units: Units of elevation in KML ('meters' or 'feet')
        grid_resolution: Grid resolution for interpolation
        slope_units: Units for slope display ('degrees', 'percent', 'rise-run')
        run_length: Run length for rise:run display
        max_slope: Maximum slope for color scale (auto if None)
        colormap: Matplotlib colormap
        dpi: Output image DPI
        smooth: Gaussian smoothing sigma (0 = no smoothing)
        show_contours: Overlay elevation contours on the slope map
        contour_interval: Contour interval in feet
        figsize: Figure size in inches [width, height]
        target_slope: Target slope for yellow color (in current units)
        stats_position: Position of statistics text ('inside', 'outside', 'none')
        progress_callback: Optional progress callback
    """
    # Validate input
    input_file = Path(input_file)
    if not input_file.exists():
        raise FileFormatError(f"Input file not found: {input_file}")
    
    output_file = Path(output_file)
    
    if progress_callback:
        progress_callback("Extracting points from KML", 10)
    
    # Extract points from KML
    points = _extract_points(input_file)
    
    if not points:
        raise ProcessingError("No points found in KML file")
    
    if len(points) < 3:
        raise ProcessingError("Need at least 3 points for slope calculation")
    
    click.echo(f"Found {len(points)} points in KML")
    
    if progress_callback:
        progress_callback("Projecting coordinates", 20)
    
    # Project to local coordinate system
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    elevs = [p[2] for p in points]
    
    # Convert elevation to feet if needed
    if elevation_units == 'meters':
        elevs = [e * M_TO_FT for e in elevs]
    
    # Project to UTM
    avg_lon = sum(lons) / len(lons)
    avg_lat = sum(lats) / len(lats)
    utm_zone = int((avg_lon + 180) / 6) + 1
    epsg_code = 32600 + utm_zone if avg_lat >= 0 else 32700 + utm_zone
    
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)
    
    x_coords = []
    y_coords = []
    for lon, lat in zip(lons, lats):
        x, y = transformer.transform(lon, lat)
        x_coords.append(x)
        y_coords.append(y)
    
    # Convert to feet
    x_coords = [x * M_TO_FT for x in x_coords]
    y_coords = [y * M_TO_FT for y in y_coords]
    
    if progress_callback:
        progress_callback("Creating interpolation grid", 40)
    
    # Create interpolation grid
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    xi = np.linspace(x_min, x_max, grid_resolution)
    yi = np.linspace(y_min, y_max, grid_resolution)
    Xi, Yi = np.meshgrid(xi, yi)
    
    # Interpolate elevation
    points_xy = list(zip(x_coords, y_coords))
    Zi = griddata(points_xy, elevs, (Xi, Yi), method='cubic')
    
    # Handle NaN values at edges
    mask = ~np.isnan(Zi)
    
    if progress_callback:
        progress_callback("Calculating slope", 60)
    
    # Calculate slope
    dx = xi[1] - xi[0]
    dy = yi[1] - yi[0]
    slope_grid = _calculate_slope(Zi, dx, dy, slope_units, run_length)
    
    # Apply smoothing if requested
    if smooth > 0:
        slope_grid = gaussian_filter(slope_grid, sigma=smooth)
    
    # Apply mask
    slope_grid[~mask] = np.nan
    
    if progress_callback:
        progress_callback("Creating visualization", 80)
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Determine color scale
    if target_slope is not None:
        # Create custom colormap centered on target slope
        vmin = 0
        vmax = max_slope if max_slope is not None else np.nanmax(slope_grid)
        norm = _create_target_colormap(target_slope, vmin, vmax)
    else:
        vmin = 0
        vmax = max_slope if max_slope is not None else np.nanmax(slope_grid)
        norm = colors.Normalize(vmin=vmin, vmax=vmax)
    
    # Create slope map
    im = ax.imshow(slope_grid, 
                   extent=[x_min, x_max, y_min, y_max],
                   origin='lower',
                   cmap=colormap,
                   norm=norm,
                   aspect='equal')
    
    # Add contours if requested
    if show_contours:
        contour_levels = np.arange(
            np.floor(np.nanmin(Zi) / contour_interval) * contour_interval,
            np.ceil(np.nanmax(Zi) / contour_interval) * contour_interval + contour_interval,
            contour_interval
        )
        cs = ax.contour(Xi, Yi, Zi, levels=contour_levels, colors='black', 
                       linewidths=0.5, alpha=0.5)
        ax.clabel(cs, inline=True, fontsize=8, fmt='%g ft')
    
    # Add colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.1)
    cbar = plt.colorbar(im, cax=cax)
    
    # Set colorbar label
    if slope_units == 'degrees':
        cbar.set_label('Slope (degrees)', rotation=270, labelpad=20)
    elif slope_units == 'percent':
        cbar.set_label('Slope (%)', rotation=270, labelpad=20)
    else:
        cbar.set_label(f'Slope (rise:{run_length:.0f})', rotation=270, labelpad=20)
    
    # Add statistics
    if stats_position != 'none':
        stats_text = _create_stats_text(slope_grid, slope_units, run_length)
        
        if stats_position == 'inside':
            ax.text(0.02, 0.98, stats_text,
                   transform=ax.transAxes,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                   fontsize=10)
        else:  # outside
            fig.text(0.02, 0.02, stats_text,
                    verticalalignment='bottom',
                    fontsize=10)
    
    # Set labels and title
    ax.set_xlabel('Easting (ft)')
    ax.set_ylabel('Northing (ft)')
    ax.set_title(f'Slope Analysis - {input_file.stem}')
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Tight layout
    plt.tight_layout()
    
    if progress_callback:
        progress_callback("Saving image", 95)
    
    # Save figure
    plt.savefig(str(output_file), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    # Summary
    click.echo(f"\nCreated slope heatmap: {output_file}")
    click.echo(f"- Grid resolution: {grid_resolution}x{grid_resolution}")
    click.echo(f"- Slope units: {slope_units}")
    if smooth > 0:
        click.echo(f"- Smoothing applied: sigma={smooth}")
    click.echo(f"- Output resolution: {dpi} DPI")
    
    if progress_callback:
        progress_callback("Complete", 100)


def _parse_coordinates(coord_text: str) -> Optional[Tuple[float, float, float]]:
    """Parse KML coordinate string (lon,lat,elev)"""
    parts = coord_text.strip().split(",")
    if len(parts) >= 2:
        lon = float(parts[0])
        lat = float(parts[1])
        elev = float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0
        return (lon, lat, elev)
    return None


def _extract_points(kml_path: Path) -> List[Tuple[float, float, float]]:
    """Extract all Point coordinates from KML"""
    try:
        tree = ET.parse(str(kml_path))
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
    except Exception as e:
        raise ProcessingError(f"Error reading KML file: {e}")


def _calculate_slope(Z, dx, dy, units='degrees', run_length=10.0):
    """
    Calculate slope from elevation grid.
    
    Args:
        Z: Elevation grid
        dx, dy: Grid spacing
        units: 'degrees', 'percent', or 'rise-run'
        run_length: Run length for rise:run calculation
    
    Returns:
        Slope grid in specified units
    """
    # Calculate gradients
    dz_dy, dz_dx = np.gradient(Z, dy, dx)
    
    # Calculate slope magnitude
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    
    # Convert to desired units
    if units == 'degrees':
        slope = np.degrees(slope_rad)
    elif units == 'percent':
        slope = np.tan(slope_rad) * 100
    else:  # rise-run
        slope = np.tan(slope_rad) * run_length
    
    return slope


def _create_target_colormap(target_value, vmin, vmax):
    """Create a colormap with yellow at the target value"""
    # Normalize target position
    target_norm = (target_value - vmin) / (vmax - vmin)
    
    # Create custom colormap
    # Green (low) -> Yellow (target) -> Red (high)
    cmap = colors.LinearSegmentedColormap.from_list(
        'target_slope',
        [(0, 'green'), (target_norm, 'yellow'), (1, 'red')]
    )
    
    return colors.Normalize(vmin=vmin, vmax=vmax)


def _create_stats_text(slope_grid, slope_units, run_length):
    """Create statistics text for the plot"""
    valid_slopes = slope_grid[~np.isnan(slope_grid)]
    
    if len(valid_slopes) == 0:
        return "No valid slope data"
    
    min_slope = np.min(valid_slopes)
    max_slope = np.max(valid_slopes)
    mean_slope = np.mean(valid_slopes)
    median_slope = np.median(valid_slopes)
    
    if slope_units == 'degrees':
        unit_str = '°'
        fmt = '.1f'
    elif slope_units == 'percent':
        unit_str = '%'
        fmt = '.1f'
    else:
        unit_str = f':{run_length:.0f}'
        fmt = '.2f'
    
    stats = f"Slope Statistics:\n"
    stats += f"Min: {min_slope:{fmt}}{unit_str}\n"
    stats += f"Max: {max_slope:{fmt}}{unit_str}\n"
    stats += f"Mean: {mean_slope:{fmt}}{unit_str}\n"
    stats += f"Median: {median_slope:{fmt}}{unit_str}"
    
    return stats