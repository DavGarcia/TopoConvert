# CLI Reference

This document provides detailed information about all TopoConvert commands and their options.

## Global Options

These options are available for all commands:

- `--version` - Show the TopoConvert version
- `-h, --help` - Show help message

## Commands

### kml-to-contours

Generate contour lines from KML point data.

```bash
topoconvert kml-to-contours INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file containing elevation points
- `OUTPUT_FILE` - Path to output DXF file

**Options:**
- `--interval, -i FLOAT` - Contour interval in meters (default: 1.0)
- `--label/--no-label` - Add elevation labels to contours (default: label)

**Example:**
```bash
topoconvert kml-to-contours terrain.kml contours.dxf --interval 0.5 --label
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

Extract point data from KML files.

```bash
topoconvert kml-to-points INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file
- `OUTPUT_FILE` - Path to output file

**Options:**
- `--format, -f [csv|json|txt]` - Output format (default: csv)

**Example:**
```bash
topoconvert kml-to-points survey.kml points.csv --format csv
```

### kml-to-mesh

Generate triangulated mesh from KML point data.

```bash
topoconvert kml-to-mesh INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file
- `OUTPUT_FILE` - Path to output mesh file

**Options:**
- `--mesh-type, -t [delaunay|concave]` - Type of mesh generation (default: delaunay)
- `--alpha, -a FLOAT` - Alpha value for concave hull, 0=convex (default: 0.0)

**Example:**
```bash
topoconvert kml-to-mesh points.kml mesh.dxf --mesh-type concave --alpha 0.5
```

### combined-dxf

Combine multiple DXF files into a single file.

```bash
topoconvert combined-dxf INPUT_FILES... --output OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILES` - Paths to input DXF files (multiple)

**Required Options:**
- `--output, -o PATH` - Output DXF file path

**Options:**
- `--merge-layers/--keep-layers` - Merge all entities into single layer (default: keep-layers)

**Example:**
```bash
topoconvert combined-dxf file1.dxf file2.dxf file3.dxf --output merged.dxf --merge-layers
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
topoconvert kml-contours-to-dxf INPUT_FILE OUTPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to input KML file with contour lines
- `OUTPUT_FILE` - Path to output DXF file

**Options:**
- `--layer-by-elevation/--single-layer` - Create separate layers by elevation (default: layer-by-elevation)
- `--smooth/--no-smooth` - Apply smoothing to contour lines (default: no-smooth)

**Example:**
```bash
topoconvert kml-contours-to-dxf contours.kml contours.dxf --smooth
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
   topoconvert kml-to-contours points.kml contours.dxf --interval 0.5
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