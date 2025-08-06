"""Generate slope heatmap from elevation data.

Adapted from GPSGrid kml_to_slope_heatmap.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional

import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pyproj import Transformer
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter, binary_closing

from topoconvert.core.exceptions import ProcessingError, FileFormatError
from topoconvert.core.result_types import SlopeHeatmapResult


NS = {"kml": "http://www.opengis.net/kml/2.2"}
M_TO_FT = 3.28084


def compute_slope_from_points(
    points: List[Tuple[float, float, float]],
    elevation_units: str = "meters",
    grid_resolution: int = 200,
    slope_units: str = "degrees",
    run_length: float = 10.0,
    smooth: float = 1.0,
) -> dict:
    """
    Compute slope data from a list of points.

    This is a pure computation function that processes elevation points
    and returns slope data without any matplotlib dependencies.

    Args:
        points: List of (lon, lat, elevation) tuples
        elevation_units: Units of elevation ('meters' or 'feet')
        grid_resolution: Grid resolution for interpolation
        slope_units: Units for slope display ('degrees', 'percent', 'rise-run')
        run_length: Run length for rise:run display
        smooth: Gaussian smoothing sigma (0 = no smoothing)

    Returns:
        Dictionary containing:
        - slope_grid: 2D numpy array of slope values
        - elevation_grid: 2D numpy array of elevation values
        - x_coords: List of projected x coordinates (feet)
        - y_coords: List of projected y coordinates (feet)
        - extent: [x_min, x_max, y_min, y_max] bounds
        - slope_stats: Dictionary with min, max, mean, median slope
        - xi: 1D array of x grid coordinates
        - yi: 1D array of y grid coordinates
    """
    # Validate input
    if not points:
        raise ProcessingError("No points provided")

    if len(points) < 3:
        raise ProcessingError("Need at least 3 points for slope calculation")

    # Validate parameters
    if grid_resolution <= 0:
        raise ValueError(f"Grid resolution must be positive, got {grid_resolution}")

    if slope_units not in ["degrees", "percent", "rise-run"]:
        raise ValueError(
            f"Invalid slope units: {slope_units}. Must be 'degrees', 'percent', or 'rise-run'"
        )

    if elevation_units not in ["meters", "feet"]:
        # Warn but continue, treating as meters
        warnings.warn(
            f"Unknown elevation units: {elevation_units}. Treating as meters.",
            UserWarning,
        )

    if smooth < 0:
        warnings.warn(
            f"Negative smoothing value {smooth} will be treated as 0 (no smoothing)",
            UserWarning,
        )
        smooth = 0.0

    # Extract coordinates and elevations
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    elevs = [p[2] for p in points]

    # Validate coordinates
    for i, (lon, lat) in enumerate(zip(lons, lats)):
        if not -180 <= lon <= 180:
            warnings.warn(
                f"Point {i}: Longitude {lon} is outside valid range [-180, 180]",
                UserWarning,
            )
        if not -90 <= lat <= 90:
            warnings.warn(
                f"Point {i}: Latitude {lat} is outside valid range [-90, 90]",
                UserWarning,
            )

    # Check for duplicate points
    unique_coords = set(zip(lons, lats))
    if len(unique_coords) < len(points):
        warnings.warn(
            f"Duplicate coordinate points detected: {len(points)} points reduced to {len(unique_coords)} unique locations",
            UserWarning,
        )

    # Check if all points are at same location
    if len(unique_coords) == 1:
        raise ValueError(
            "All points are at the same location. Need spatial variation for slope calculation."
        )

    # Convert elevation to feet if needed
    if elevation_units == "meters":
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

    # Create interpolation grid
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    # Check data density
    area = (x_max - x_min) * (y_max - y_min)  # in square feet
    if area > 0:
        points_per_area = len(points) / area
        # Warn if less than 1 point per 10,000 sq ft (roughly 100m x 100m)
        if points_per_area < 1.0 / 10000:
            warnings.warn(
                f"Sparse data detected: {len(points)} points over {area:.0f} sq ft. "
                f"Consider using more points or reducing grid resolution for better results.",
                UserWarning,
            )

    xi = np.linspace(x_min, x_max, grid_resolution)
    yi = np.linspace(y_min, y_max, grid_resolution)
    Xi, Yi = np.meshgrid(xi, yi)

    # Interpolate elevation with fallback chain
    points_xy = list(zip(x_coords, y_coords))

    # Try cubic interpolation first
    try:
        Zi = griddata(points_xy, elevs, (Xi, Yi), method="cubic")
        # Check if cubic produced too many NaNs (more than 50% of grid)
        nan_ratio = np.sum(np.isnan(Zi)) / Zi.size
        if nan_ratio > 0.5:
            raise ValueError("Cubic interpolation produced too many NaN values")
    except (ValueError, Exception):
        # Fall back to linear interpolation
        try:
            Zi = griddata(points_xy, elevs, (Xi, Yi), method="linear")
            # Check if linear still has issues
            nan_ratio = np.sum(np.isnan(Zi)) / Zi.size
            if nan_ratio > 0.8:
                raise ValueError("Linear interpolation produced too many NaN values")
        except (ValueError, Exception):
            # Final fallback to nearest neighbor
            Zi = griddata(points_xy, elevs, (Xi, Yi), method="nearest")

    # Handle NaN values at edges
    mask = ~np.isnan(Zi)

    # Use binary closing to fill small holes in the mask
    # This helps with edge artifacts and small gaps in interpolation
    if np.any(mask):
        # Create a structure element for binary closing (3x3 square)
        from scipy.ndimage import generate_binary_structure

        struct = generate_binary_structure(2, 2)  # 2D with connectivity 2
        # Apply binary closing to fill small holes
        mask_closed = binary_closing(mask, structure=struct, iterations=2)
        # Only fill values where we closed holes, not extend beyond original data
        holes_filled = mask_closed & ~mask
        if np.any(holes_filled):
            # Use nearest neighbor interpolation to fill the holes
            Zi_filled = griddata(
                points_xy, elevs, (Xi[holes_filled], Yi[holes_filled]), method="nearest"
            )
            Zi[holes_filled] = Zi_filled
            mask = mask_closed

    # Calculate slope
    dx = xi[1] - xi[0]
    dy = yi[1] - yi[0]
    slope_grid = _calculate_slope(Zi, dx, dy, slope_units, run_length)

    # Apply smoothing if requested
    if smooth > 0:
        slope_grid = gaussian_filter(slope_grid, sigma=smooth)

    # Apply mask
    slope_grid[~mask] = np.nan

    # Calculate statistics
    valid_slopes = slope_grid[~np.isnan(slope_grid)]
    if len(valid_slopes) > 0:
        slope_stats = {
            "min": float(np.nanmin(valid_slopes)),
            "max": float(np.nanmax(valid_slopes)),
            "mean": float(np.nanmean(valid_slopes)),
            "median": float(np.nanmedian(valid_slopes)),
        }
    else:
        slope_stats = {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0}

    return {
        "slope_grid": slope_grid,
        "elevation_grid": Zi,
        "x_coords": x_coords,
        "y_coords": y_coords,
        "extent": [x_min, x_max, y_min, y_max],
        "slope_stats": slope_stats,
        "xi": xi,
        "yi": yi,
        "mask": mask,
        "utm_zone": utm_zone,
        "epsg_code": epsg_code,
    }


def render_slope_heatmap(
    slope_data: dict,
    output_file: Path,
    input_title: str = "Slope Analysis",
    max_slope: Optional[float] = None,
    colormap: str = "RdYlGn_r",
    dpi: int = 150,
    show_contours: bool = True,
    contour_interval: float = 5.0,
    figsize: Optional[List[float]] = None,
    target_slope: Optional[float] = None,
    stats_position: str = "outside",
    slope_units: str = "degrees",
    run_length: float = 10.0,
) -> None:
    """
    Render slope data to a matplotlib figure.

    Args:
        slope_data: Dictionary from compute_slope_from_points containing:
            - slope_grid: 2D array of slope values
            - elevation_grid: 2D array of elevation values
            - extent: [x_min, x_max, y_min, y_max]
            - slope_stats: Dictionary with min, max, mean, median
            - xi, yi: Grid coordinates
        output_file: Path to save the rendered image
        input_title: Title for the plot
        max_slope: Maximum slope for color scale (auto if None)
        colormap: Matplotlib colormap name
        dpi: Output resolution
        show_contours: Whether to overlay elevation contours (default: True)
        contour_interval: Contour interval in feet
        figsize: Figure size [width, height]
        target_slope: Target slope for yellow color
        stats_position: Position of statistics ('inside', 'outside', 'none')
        slope_units: Units for slope display
        run_length: Run length for rise:run format
    """
    # Extract data from slope_data dictionary
    slope_grid = slope_data["slope_grid"]
    Zi = slope_data["elevation_grid"]
    x_min, x_max, y_min, y_max = slope_data["extent"]
    xi = slope_data["xi"]
    yi = slope_data["yi"]
    Xi, Yi = np.meshgrid(xi, yi)

    # Create figure
    fig_size = figsize or [10, 8]
    fig, ax = plt.subplots(figsize=fig_size)

    # Determine color scale
    if target_slope is not None:
        # Create custom colormap centered on target slope
        vmin = 0
        try:
            vmax = max_slope if max_slope is not None else np.nanmax(slope_grid)
        except (ValueError, RuntimeWarning):  # All NaN case
            vmax = 90.0  # Default max slope for degrees
        custom_cmap, norm = _create_target_colormap(target_slope, vmin, vmax)
        used_colormap = custom_cmap
    else:
        vmin = 0
        try:
            vmax = max_slope if max_slope is not None else np.nanmax(slope_grid)
        except (ValueError, RuntimeWarning):  # All NaN case
            vmax = 90.0  # Default max slope for degrees
        norm = colors.Normalize(vmin=vmin, vmax=vmax)
        used_colormap = colormap

    # Create slope map
    im = ax.imshow(
        slope_grid,
        extent=[x_min, x_max, y_min, y_max],
        origin="lower",
        cmap=used_colormap,
        norm=norm,
        aspect="equal",
    )

    # Add contours if requested
    if show_contours:
        try:
            z_min = np.nanmin(Zi)
            z_max = np.nanmax(Zi)
            if np.isfinite(z_min) and np.isfinite(z_max):
                contour_levels = np.arange(
                    np.floor(z_min / contour_interval) * contour_interval,
                    np.ceil(z_max / contour_interval) * contour_interval
                    + contour_interval,
                    contour_interval,
                )
                if len(contour_levels) > 1:
                    cs = ax.contour(
                        Xi,
                        Yi,
                        Zi,
                        levels=contour_levels,
                        colors="black",
                        linewidths=0.5,
                        alpha=0.5,
                    )
                    ax.clabel(cs, inline=True, fontsize=8, fmt="%g ft")
        except (ValueError, RuntimeWarning):
            # Skip contours if all NaN or other issues
            pass

    # Add colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.1)
    cbar = plt.colorbar(im, cax=cax)

    # Set colorbar label
    if slope_units == "degrees":
        cbar.set_label("Slope (degrees)", rotation=270, labelpad=20)
    elif slope_units == "percent":
        cbar.set_label("Slope (%)", rotation=270, labelpad=20)
    else:
        cbar.set_label(f"Slope (rise:{run_length:.0f})", rotation=270, labelpad=20)

    # Add statistics
    if stats_position != "none":
        stats_text = _create_stats_text_from_data(
            slope_data["slope_stats"], slope_units, run_length
        )

        if stats_position == "inside":
            ax.text(
                0.02,
                0.98,
                stats_text,
                transform=ax.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
                fontsize=10,
            )
        else:  # outside
            fig.text(0.02, 0.02, stats_text, verticalalignment="bottom", fontsize=10)

    # Set labels and title
    ax.set_xlabel("Easting (ft)")
    ax.set_ylabel("Northing (ft)")
    ax.set_title(input_title)

    # Add grid
    ax.grid(True, alpha=0.3)

    # Tight layout
    plt.tight_layout()

    # Save figure
    fig.savefig(str(output_file), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def generate_slope_heatmap(
    input_file: Path,
    output_file: Path,
    elevation_units: str = "meters",
    grid_resolution: int = 200,
    slope_units: str = "degrees",
    run_length: float = 10.0,
    max_slope: Optional[float] = None,
    colormap: str = "RdYlGn_r",
    dpi: int = 150,
    smooth: float = 1.0,
    show_contours: bool = True,
    contour_interval: float = 5.0,
    figsize: Optional[List[float]] = None,
    target_slope: Optional[float] = None,
    stats_position: str = "outside",
) -> SlopeHeatmapResult:
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
        show_contours: Overlay elevation contours on the slope map (default: True)
        contour_interval: Contour interval in feet
        figsize: Figure size in inches [width, height] (defaults to [10, 8])
        target_slope: Target slope for yellow color (in current units)
        stats_position: Position of statistics text ('inside', 'outside', 'none')
    """
    # Validate input
    input_file = Path(input_file)
    if not input_file.exists():
        raise FileFormatError(f"Input file not found: {input_file}")

    output_file = Path(output_file)

    # Extract points from KML
    points = _extract_points(input_file)

    if not points:
        raise ProcessingError("No points found in KML file")

    # Found {len(points)} points in KML

    # Compute slope data using pure computation function
    slope_data = compute_slope_from_points(
        points=points,
        elevation_units=elevation_units,
        grid_resolution=grid_resolution,
        slope_units=slope_units,
        run_length=run_length,
        smooth=smooth,
    )

    # Use the new render function for visualization
    render_slope_heatmap(
        slope_data=slope_data,
        output_file=output_file,
        input_title=f"Slope Analysis - {input_file.stem}",
        max_slope=max_slope,
        colormap=colormap,
        dpi=dpi,
        show_contours=show_contours,
        contour_interval=contour_interval,
        figsize=figsize,
        target_slope=target_slope,
        stats_position=stats_position,
        slope_units=slope_units,
        run_length=run_length,
    )

    # Return result
    return SlopeHeatmapResult(
        success=True,
        output_file=str(output_file),
        grid_resolution=(grid_resolution, grid_resolution),
        slope_units=slope_units,
        smoothing_applied=smooth if smooth > 0 else None,
        output_dpi=dpi,
        point_count=len(points),
        details={
            "elevation_units": elevation_units,
            "run_length": run_length,
            "max_slope": max_slope,
            "colormap": colormap,
            "show_contours": show_contours,
            "contour_interval": contour_interval,
            "figsize": figsize,
            "target_slope": target_slope,
            "stats_position": stats_position,
        },
    )


def _parse_coordinates(coord_text: str) -> Optional[Tuple[float, float, float]]:
    """Parse KML coordinate string (lon,lat,elev)"""
    parts = coord_text.strip().split(",")
    if len(parts) >= 2:
        try:
            lon = float(parts[0])
            lat = float(parts[1])
            elev = float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0
            return (lon, lat, elev)
        except ValueError:
            # Handle empty strings or non-numeric values
            if any(
                part.strip() for part in parts
            ):  # If any non-empty parts, it's an error
                raise
            return None
    return None


def _extract_points(kml_path: Path) -> List[Tuple[float, float, float]]:
    """Extract all Point coordinates from KML"""
    try:
        tree = ET.parse(str(kml_path))
        root = tree.getroot()

        points = []
        placemark_count = 0

        # Find all Placemarks with Points
        for pm in root.findall(".//kml:Placemark", NS):
            placemark_count += 1
            point_elem = pm.find(".//kml:Point", NS)
            if point_elem is not None:
                coord_elem = point_elem.find("kml:coordinates", NS)
                if coord_elem is not None and coord_elem.text:
                    try:
                        coord = _parse_coordinates(coord_elem.text)
                        if coord:
                            points.append(coord)
                    except ValueError as ve:
                        warnings.warn(
                            f"Skipping invalid coordinates in Placemark {placemark_count}: {ve}",
                            UserWarning,
                        )

        # Provide helpful error messages
        if placemark_count == 0:
            raise ProcessingError(
                "No Placemarks found in KML file. Expected KML file with Point placemarks."
            )
        elif len(points) == 0:
            raise ProcessingError(
                f"Found {placemark_count} Placemarks but no valid Point coordinates. Check that Placemarks contain Point elements with coordinates."
            )

        return points
    except ET.ParseError as e:
        raise ProcessingError(
            f"Invalid KML file format: {e}. Ensure the file is valid XML."
        )
    except ProcessingError:
        raise  # Re-raise our own errors
    except Exception as e:
        raise ProcessingError(f"Unexpected error reading KML file: {e}")


def _calculate_slope(Z, dx, dy, units="degrees", run_length=10.0):
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
    if units == "degrees":
        slope = np.degrees(slope_rad)
    elif units == "percent":
        slope = np.tan(slope_rad) * 100
    else:  # rise-run
        slope = np.tan(slope_rad) * run_length

    return slope


def _create_target_colormap(target_value, vmin, vmax):
    """Create a colormap with yellow at the target value

    Args:
        target_value: The value where yellow should appear
        vmin: Minimum value for the color scale
        vmax: Maximum value for the color scale

    Returns:
        Tuple of (colormap, normalizer)
    """
    # Clamp target value within range
    target_value = max(vmin, min(target_value, vmax))

    # Normalize target position
    target_norm = (target_value - vmin) / (vmax - vmin) if vmax > vmin else 0.5

    # Create custom colormap
    # Green (low) -> Yellow (target) -> Red (high)
    cmap = colors.LinearSegmentedColormap.from_list(
        "target_slope", [(0, "green"), (target_norm, "yellow"), (1, "red")]
    )

    norm = colors.Normalize(vmin=vmin, vmax=vmax)

    return cmap, norm


def _create_stats_text(slope_grid, slope_units, run_length):
    """Create statistics text for the plot (legacy version)"""
    valid_slopes = slope_grid[~np.isnan(slope_grid)]

    if len(valid_slopes) == 0:
        return "No valid slope data"

    min_slope = np.min(valid_slopes)
    max_slope = np.max(valid_slopes)
    mean_slope = np.mean(valid_slopes)
    median_slope = np.median(valid_slopes)

    stats_data = {
        "min": float(min_slope),
        "max": float(max_slope),
        "mean": float(mean_slope),
        "median": float(median_slope),
    }

    return _create_stats_text_from_data(stats_data, slope_units, run_length)


def _create_stats_text_from_data(slope_stats, slope_units, run_length):
    """Create statistics text from pre-computed statistics"""
    if slope_units == "degrees":
        unit_str = "°"
        fmt = ".1f"
    elif slope_units == "percent":
        unit_str = "%"
        fmt = ".1f"
    else:
        unit_str = f":{run_length:.0f}"
        fmt = ".2f"

    stats = f"Slope Statistics:\n"
    stats += f"Min: {slope_stats['min']:{fmt}}{unit_str}\n"
    stats += f"Max: {slope_stats['max']:{fmt}}{unit_str}\n"
    stats += f"Mean: {slope_stats['mean']:{fmt}}{unit_str}\n"
    stats += f"Median: {slope_stats['median']:{fmt}}{unit_str}"

    return stats
