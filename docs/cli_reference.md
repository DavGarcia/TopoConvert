# CLI Reference

This document provides detailed information about all TopoConvert commands and their options.

## Global Options

These options are available for all commands:

- `--version` - Show the TopoConvert version
- `-h, --help` - Show help message

## Projection System

TopoConvert provides flexible coordinate system handling across all commands:

### Automatic UTM Detection
By default, TopoConvert automatically detects the appropriate UTM zone based on the input data's geographic location. This ensures optimal projection for local accuracy without requiring manual configuration.

### Manual Projection Control
For cases where specific projections are needed:
- `--target-epsg EPSG_CODE` - Specify an exact EPSG code for the target projection
- `--wgs84` - Keep coordinates in WGS84 (lat/lon) format (available only for certain commands)

### Projection Behavior by Command Type

**DXF Output Commands** (require projected coordinates):
- `kml-to-dxf-contours`, `kml-to-dxf-mesh`, `kml-contours-to-dxf`
- Always project to UTM or specified EPSG
- `--wgs84` flag is NOT available (DXF requires projected coordinates)

**Point Extraction Commands** (flexible output):
- `kml-to-points`, `multi-csv-to-dxf`
- Support both projected and geographic coordinates
- `--wgs84` flag available for geographic output
- Cannot use both `--target-epsg` and `--wgs84` together

**Analysis Commands** (require projected coordinates):
- `slope-heatmap`, `gps-grid`
- Always work in projected coordinate space
- No `--wgs84` option (spatial analysis requires projected coordinates)

## Commands

### kml-to-dxf-contours

Generate contour lines from KML point data.

```bash
topoconvert kml-to-dxf-contours INPUT_FILE [OUTPUT_FILE] [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file containing elevation points
- `OUTPUT_FILE` - Path to output DXF file (optional, defaults to input name with .dxf extension)

**Options:**
- `--interval, -i FLOAT` - Contour interval in feet (default: 1.0)
- `--label/--no-label` - Add elevation labels to contours (default: label)
- `--elevation-units [meters|feet]` - Units of elevation in KML (default: meters)
- `--grid-resolution INT` - Grid density for interpolation (default: 100)
- `--label-height FLOAT` - Text size for elevation labels (default: 2.0)
- `--no-translate` - Don't translate coordinates to origin (default: translate)
- `--target-epsg INT` - Target EPSG code for projection (default: auto-detect UTM)

**Example:**
```bash
# Basic usage with auto-detected UTM projection
topoconvert kml-to-dxf-contours terrain.kml contours.dxf --interval 0.5

# Specify projection and elevation units
topoconvert kml-to-dxf-contours terrain.kml --target-epsg 32633 --elevation-units feet

# High-resolution contours with custom labels
topoconvert kml-to-dxf-contours terrain.kml contours.dxf --grid-resolution 200 --label-height 3.0
```

### csv-to-kml

Convert CSV survey data to KML format.

```bash
topoconvert csv-to-kml INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input CSV file
- `OUTPUT_FILE` - Path to output KML file

**Options:**
- `--add-labels/--no-labels` - Add labels to KML placemarks (default: add-labels)
- `--x-column, -x TEXT` - Column name for X coordinates (default: "x")
- `--y-column, -y TEXT` - Column name for Y coordinates (default: "y")
- `--z-column, -z TEXT` - Column name for Z coordinates/elevation (default: "z")

**Example:**
```bash
topoconvert csv-to-kml survey.csv points.kml --x-column lon --y-column lat --z-column elevation
```

### kml-to-points

Extract point data from KML files to various formats.

```bash
topoconvert kml-to-points INPUT_FILE [OUTPUT_FILE] [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file
- `OUTPUT_FILE` - Path to output file (optional, defaults to input name with format extension)

**Options:**
- `--format, -f [csv|json|txt|dxf]` - Output format (default: csv)
- `--elevation-units [meters|feet]` - Convert elevation units (default: meters)
- `--no-translate` - Don't translate coordinates to origin for DXF (default: translate)
- `--layer-name TEXT` - Layer name for DXF output (default: POINTS)
- `--point-color INT` - AutoCAD color index for DXF points (default: 7)
- `--target-epsg INT` - Target EPSG code for projection (default: auto-detect UTM)
- `--wgs84` - Output coordinates in WGS84 lat/lon format (cannot use with --target-epsg)

**Example:**
```bash
# Extract to CSV with automatic UTM projection
topoconvert kml-to-points survey.kml points.csv

# Extract to DXF with specific projection
topoconvert kml-to-points survey.kml points.dxf --format dxf --target-epsg 32614

# Extract to CSV keeping WGS84 coordinates
topoconvert kml-to-points survey.kml geographic.csv --wgs84

# Extract with elevation conversion
topoconvert kml-to-points survey.kml points.csv --elevation-units feet
```

### kml-to-dxf-mesh

Generate triangulated mesh from KML point data.

```bash
topoconvert kml-to-dxf-mesh INPUT_FILE [OUTPUT_FILE] [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file
- `OUTPUT_FILE` - Path to output DXF file (optional, defaults to input name with .dxf extension)

**Options:**
- `--elevation-units [meters|feet]` - Units of elevation in KML (default: meters)
- `--mesh-type [delaunay|grid|concave]` - Type of mesh generation (default: delaunay)
- `--grid-size INT` - Grid size for grid mesh type (default: 50)
- `--alpha FLOAT` - Alpha value for concave hull, 0=convex (default: 0.0)
- `--no-boundaries` - Skip boundary generation (default: include boundaries)
- `--layer-name TEXT` - Base layer name for DXF (default: MESH)
- `--no-translate` - Don't translate coordinates to origin (default: translate)
- `--target-epsg INT` - Target EPSG code for projection (default: auto-detect UTM)

**Example:**
```bash
# Basic Delaunay triangulation
topoconvert kml-to-dxf-mesh points.kml mesh.dxf

# Concave hull mesh with specific projection
topoconvert kml-to-dxf-mesh points.kml --mesh-type concave --alpha 0.5 --target-epsg 32633

# Grid-based mesh
topoconvert kml-to-dxf-mesh points.kml grid_mesh.dxf --mesh-type grid --grid-size 100
```

### multi-csv-to-dxf

Combine multiple CSV files into a single DXF file.

```bash
topoconvert multi-csv-to-dxf CSV_FILES... --output OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `CSV_FILES` - Paths to input CSV files (multiple)

**Required Options:**
- `--output, -o PATH` - Output DXF file path

**Options:**
- `--x-column TEXT` - Column name for X coordinates (default: x)
- `--y-column TEXT` - Column name for Y coordinates (default: y)
- `--z-column TEXT` - Column name for Z coordinates (optional)
- `--layer-prefix TEXT` - Prefix for layer names (default: CSV_)
- `--point-style [point|circle|cross]` - Point representation style (default: point)
- `--target-epsg INT` - Target EPSG code for projection (default: auto-detect UTM)
- `--wgs84` - Keep coordinates in WGS84 format (cannot use with --target-epsg)
- `--no-translate` - Don't translate coordinates to origin (default: translate)

**Example:**
```bash
# Combine CSV files with automatic UTM projection
topoconvert multi-csv-to-dxf survey1.csv survey2.csv survey3.csv --output combined.dxf

# Combine with specific projection and custom columns
topoconvert multi-csv-to-dxf *.csv --output all_points.dxf --x-column lon --y-column lat --target-epsg 32614

# Keep WGS84 coordinates
topoconvert multi-csv-to-dxf data1.csv data2.csv --output geographic.dxf --wgs84
```

### kml-to-csv

Convert KML data to CSV format.

```bash
topoconvert kml-to-csv INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file
- `OUTPUT_FILE` - Path to output CSV file

**Options:**
- `--include-attributes/--no-attributes` - Include KML attributes in CSV (default: include)
- `--coordinate-format, -c [separate|wkt]` - Coordinate format in CSV (default: separate)

**Example:**
```bash
topoconvert kml-to-csv points.kml data.csv --coordinate-format separate
```

### multi-csv-to-kml

Combine multiple CSV files into a single KML file.

```bash
topoconvert multi-csv-to-kml CSV_FILES... --output OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `CSV_FILES` - Paths to input CSV files (multiple)

**Required Options:**
- `--output, -o PATH` - Output KML file path

**Options:**
- `--x-column TEXT` - Column name for X coordinates (default: x)
- `--y-column TEXT` - Column name for Y coordinates (default: y)
- `--z-column TEXT` - Column name for Z coordinates (optional)
- `--name-column TEXT` - Column name for point names (optional)
- `--elevation-units [meters|feet]` - Units of elevation in CSV (default: meters)
- `--point-style [circle|square|triangle|star|pin]` - KML icon style (default: circle)
- `--point-color TEXT` - KML color in aabbggrr hex format (default: ff0000ff)
- `--point-scale FLOAT` - Icon scale factor (default: 1.0)
- `--folder-per-file/--single-folder` - Create separate folders per CSV (default: folder-per-file)
- `--kml-name TEXT` - KML document name (default: Combined CSV Data)

**Example:**
```bash
# Combine multiple CSV files
topoconvert multi-csv-to-kml survey1.csv survey2.csv survey3.csv --output combined.kml

# Custom columns and styling
topoconvert multi-csv-to-kml *.csv --output styled.kml --x-column lon --y-column lat --point-style star --point-color ff00ff00
```

### slope-heatmap

Generate slope analysis heatmap from elevation data.

```bash
topoconvert slope-heatmap INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file with elevation data
- `OUTPUT_FILE` - Path to output image file (PNG/JPG)

**Options:**
- `--slope-units, -u [degrees|percent|ratio]` - Units for slope (default: degrees)
- `--resolution, -r FLOAT` - Grid resolution in meters (default: 1.0)
- `--colormap, -c TEXT` - Matplotlib colormap name (default: RdYlGn_r)

**Example:**
```bash
topoconvert slope-heatmap terrain.kml slope.png --slope-units percent --resolution 0.5
```

### kml-contours-to-dxf

Convert KML contour lines to DXF format.

```bash
topoconvert kml-contours-to-dxf INPUT_FILE [OUTPUT_FILE] [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file with contour lines
- `OUTPUT_FILE` - Path to output DXF file (optional, defaults to input name with .dxf extension)

**Options:**
- `--layer-by-elevation/--single-layer` - Create separate layers by elevation (default: layer-by-elevation)
- `--elevation-units [meters|feet]` - Units of elevation values (default: meters)
- `--layer-prefix TEXT` - Prefix for elevation-based layer names (default: ELEV_)
- `--single-layer-name TEXT` - Layer name when using --single-layer (default: CONTOURS)
- `--no-translate` - Don't translate coordinates to origin (default: translate)
- `--target-epsg INT` - Target EPSG code for projection (default: auto-detect UTM)
- `--wgs84` - Keep coordinates in WGS84 format (cannot use with --target-epsg)

**Example:**
```bash
# Basic conversion with automatic UTM projection
topoconvert kml-contours-to-dxf contours.kml

# Convert with specific projection and elevation units
topoconvert kml-contours-to-dxf contours.kml contours.dxf --target-epsg 32633 --elevation-units feet

# Keep geographic coordinates
topoconvert kml-contours-to-dxf contours.kml geographic_contours.dxf --wgs84
```

### gps-grid

Generate GPS grid layout for field surveys.

```bash
topoconvert gps-grid OUTPUT_FILE --bounds MIN_X MIN_Y MAX_X MAX_Y [OPTIONS]
```

**Arguments:**
- `OUTPUT_FILE` - Path to output file

**Required Options:**
- `--bounds, -b MIN_X MIN_Y MAX_X MAX_Y` - Grid bounds in projected coordinates

**Options:**
- `--spacing, -s FLOAT` - Grid spacing in meters (default: 100.0)
- `--format, -f [kml|csv|dxf]` - Output format (default: kml)
- `--label-format, -l TEXT` - Grid point label format (default: "A{row}-{col}")

**Example:**
```bash
topoconvert gps-grid grid.kml --bounds 500000 4000000 501000 4001000 --spacing 50 --format kml
```

## Common Use Cases

### Topographical Survey Processing

1. Convert CSV survey data to KML:
   ```bash
   topoconvert csv-to-kml survey.csv points.kml
   ```

2. Generate contours from points:
   ```bash
   topoconvert kml-to-dxf-contours points.kml contours.dxf --interval 0.5
   ```

3. Create slope analysis:
   ```bash
   topoconvert slope-heatmap points.kml slope.png --slope-units degrees
   ```

### Field Survey Planning

Generate a GPS grid for field collection:
```bash
topoconvert gps-grid survey_grid.kml --bounds 500000 4000000 502000 4002000 --spacing 100
```

### Data Format Conversion

Convert between formats while preserving attributes:
```bash
topoconvert kml-to-csv input.kml output.csv --include-attributes
topoconvert csv-to-kml input.csv output.kml --add-labels
```

## Projection Examples

### Working with Different Coordinate Systems

1. **Use specific UTM zone for local accuracy:**
   ```bash
   # Force UTM Zone 33N (Central Europe)
   topoconvert kml-to-dxf-contours terrain.kml --target-epsg 32633
   
   # Force UTM Zone 14N (Central USA)
   topoconvert kml-to-dxf-mesh points.kml --target-epsg 32614
   ```

2. **Keep geographic coordinates (WGS84):**
   ```bash
   # Extract points without projection
   topoconvert kml-to-points survey.kml geographic.csv --wgs84
   
   # Combine CSV files keeping lat/lon
   topoconvert multi-csv-to-dxf data1.csv data2.csv --output geo.dxf --wgs84
   ```

3. **Use local projected coordinate systems:**
   ```bash
   # British National Grid
   topoconvert kml-to-dxf-contours uk_terrain.kml --target-epsg 27700
   
   # State Plane California Zone 3
   topoconvert kml-to-dxf-mesh ca_points.kml --target-epsg 2227
   ```

### Common EPSG Codes

- **UTM Zones (WGS84)**:
  - 32610-32619: UTM Zone 10N-19N (Western USA)
  - 32620-32627: UTM Zone 20N-27N (Eastern USA)
  - 32630-32638: UTM Zone 30N-38N (Europe/Africa)
  
- **National Grids**:
  - 27700: British National Grid
  - 2154: French Lambert-93
  - 25832: ETRS89 / UTM zone 32N (Germany)
  - 3857: Web Mercator (for web mapping)

- **State Plane (USA)**:
  - 2229: California Zone 5 (ft)
  - 2263: New York Long Island (ft)
  - 3435: Illinois East (ft)