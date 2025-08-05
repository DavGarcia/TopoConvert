# Projection System Guide

This guide explains TopoConvert's coordinate system and projection handling.

## Overview

TopoConvert intelligently handles coordinate transformations to ensure accurate geospatial processing. The system automatically detects appropriate projections while allowing manual control when needed.

## Key Concepts

### Geographic vs Projected Coordinates

- **Geographic Coordinates (WGS84)**: Latitude/Longitude in degrees
  - Used by: GPS devices, KML files, web mapping
  - Example: -122.4194° W, 37.7749° N
  
- **Projected Coordinates**: X/Y in meters or feet
  - Used by: CAD software, spatial analysis, accurate measurements
  - Example: 551757.58 E, 4180684.38 N (UTM Zone 10N)

### Why Projections Matter

- **Accuracy**: Distance and area calculations require projected coordinates
- **CAD Compatibility**: DXF files work best with projected coordinates
- **Analysis**: Slope calculations need equal-area projections
- **Visualization**: Contours and meshes require uniform scale

## Automatic UTM Detection

By default, TopoConvert automatically selects the appropriate UTM zone based on your data's location:

```python
# For longitude -122.4° (San Francisco)
# Automatically selects UTM Zone 10N (EPSG:32610)

# For longitude 13.4° (Berlin)  
# Automatically selects UTM Zone 33N (EPSG:32633)
```

This provides optimal local accuracy without manual configuration.

## Manual Projection Control

### Using --target-epsg

Specify exact projections when needed:

```bash
# British National Grid for UK data
topoconvert kml-to-dxf-contours uk_survey.kml --target-epsg 27700

# State Plane for US surveys
topoconvert kml-to-dxf-mesh california.kml --target-epsg 2227

# Web Mercator for web mapping
topoconvert kml-to-points data.kml web_points.csv --target-epsg 3857
```

### Using --wgs84

Keep geographic coordinates when appropriate:

```bash
# Extract points for GPS upload
topoconvert kml-to-points survey.kml gps_waypoints.csv --wgs84

# Create DXF with lat/lon coordinates
topoconvert multi-csv-to-dxf coords.csv --output geographic.dxf --wgs84
```

## Command-Specific Behavior

### Always Projected (Spatial Analysis)

These commands require projected coordinates for accurate calculations:

- `kml-to-dxf-contours` - Contour generation needs equal spacing
- `kml-to-dxf-mesh` - Triangulation requires planar coordinates  
- `slope-heatmap` - Slope calculation needs consistent units
- `gps-grid` - Grid generation uses meter-based spacing

### Flexible Projection (Data Export)

These commands support both projected and geographic output:

- `kml-to-points` - Can output in any coordinate system
- `multi-csv-to-dxf` - Supports WGS84 for compatibility
- `kml-contours-to-dxf` - Can preserve original coordinates

### No Projection Changes (Format Conversion)

These commands preserve original coordinates:

- `csv-to-kml` - Assumes input is already in WGS84
- `kml-to-csv` - Exports coordinates as found
- `multi-csv-to-kml` - Combines without transformation

## Choosing the Right Projection

### For Local Surveys (< 100 km²)

Use automatic UTM detection or local grid:

```bash
# Automatic UTM (recommended)
topoconvert kml-to-dxf-contours survey.kml

# Local grid system
topoconvert kml-to-dxf-contours survey.kml --target-epsg 2227  # California
```

### For Regional Projects

Use appropriate UTM zone or national grid:

```bash
# Specific UTM zone
topoconvert kml-to-dxf-mesh region.kml --target-epsg 32633  # Europe

# National grid
topoconvert kml-to-dxf-contours uk_data.kml --target-epsg 27700  # Britain
```

### For GPS/Web Integration

Keep or convert to WGS84:

```bash
# Extract for GPS upload
topoconvert kml-to-points data.kml waypoints.csv --wgs84

# Web mapping format
topoconvert kml-to-points data.kml web.csv --target-epsg 3857
```

## Common EPSG Codes Reference

### UTM Zones (Northern Hemisphere)

| Zone | Longitude Range | EPSG Code | Common Areas |
|------|----------------|-----------|--------------|
| 10N | 126°W - 120°W | 32610 | Western Canada, US West Coast |
| 11N | 120°W - 114°W | 32611 | Western US |
| 14N | 102°W - 96°W | 32614 | Central US |
| 17N | 84°W - 78°W | 32617 | Eastern US |
| 32N | 6°E - 12°E | 32632 | Central Europe |
| 33N | 12°E - 18°E | 32633 | Eastern Europe |

### National/Regional Grids

| Country/Region | System | EPSG Code | Units |
|----------------|--------|-----------|-------|
| United Kingdom | OSGB 1936 | 27700 | meters |
| France | Lambert-93 | 2154 | meters |
| Germany | ETRS89/UTM | 25832 | meters |
| Netherlands | Amersfoort/RD New | 28992 | meters |
| Australia | GDA94/MGA | 28350-28358 | meters |
| New Zealand | NZGD2000 | 2193 | meters |

### US State Plane (Examples)

| State | Zone | EPSG Code | Units |
|-------|------|-----------|-------|
| California | Zone III | 2227 | feet |
| California | Zone V | 2229 | feet |
| Texas | Central | 2277 | feet |
| New York | Long Island | 2263 | feet |
| Florida | East | 2236 | feet |

## Troubleshooting

### "Cannot use both --target-epsg and --wgs84"

These options are mutually exclusive. Choose one:
- Use `--target-epsg` for specific projected coordinate system
- Use `--wgs84` to keep geographic coordinates

### "Projection required for spatial analysis"

Commands like `slope-heatmap` need projected coordinates. Either:
- Let automatic UTM detection handle it (default)
- Specify projection with `--target-epsg`

### Large Coordinate Values in DXF

DXF files may have large coordinate values in projected systems. Use `--no-translate` to keep original coordinates, or allow translation to origin (default) for CAD compatibility.

## Best Practices

1. **Let UTM Auto-Detection Work**: For most local projects, the automatic UTM selection provides optimal results.

2. **Document Your Projection**: When using specific EPSG codes, document them in your project notes.

3. **Match Existing Data**: When combining datasets, use the same projection as your existing data.

4. **Consider Your Software**: Some CAD programs prefer local coordinates near origin (use default translation).

5. **Preserve Metadata**: When possible, keep projection information with your exported data.