# TopoConvert Documentation

Welcome to the TopoConvert documentation! TopoConvert is a unified geospatial conversion toolkit for survey data processing and transformation.

## Overview

TopoConvert provides a comprehensive set of command-line tools for converting and processing geospatial survey data between various formats. It's designed for surveyors, GIS professionals, and engineers who work with topographical data.

## Key Features

- **Multiple Format Support**: Convert between KML, CSV, and DXF formats
- **Contour Generation**: Create contour lines from point data with customizable intervals
- **Mesh Generation**: Generate Delaunay or concave hull triangulated meshes
- **Slope Analysis**: Create detailed slope heatmaps and analysis reports
- **GPS Grid Generation**: Generate field survey grids with custom spacing
- **Batch Processing**: Combine multiple files efficiently
- **Smart Projection System**: Automatic UTM detection with manual override options
- **Flexible Coordinate Handling**: Support for both geographic and projected coordinates

## Quick Links

- [Installation Guide](installation.md) - Get TopoConvert up and running
- [CLI Reference](cli_reference.md) - Detailed command documentation
- [Projection Guide](projection_guide.md) - Understanding coordinate systems and projections
- [Developer Guide](developer_guide.md) - Contributing and extending TopoConvert

## Example Usage

```bash
# Convert KML points to DXF contours with automatic UTM projection
topoconvert kml-to-dxf-contours survey_points.kml contours.dxf --interval 0.5

# Generate slope analysis with specific projection
topoconvert slope-heatmap terrain.kml slope_map.png --slope-units degrees

# Extract points keeping geographic coordinates
topoconvert kml-to-points locations.kml waypoints.csv --wgs84

# Combine multiple CSV files into DXF with custom projection
topoconvert multi-csv-to-dxf *.csv --output merged.dxf --target-epsg 27700
```

## Getting Help

- Use `topoconvert --help` to see all available commands
- Use `topoconvert <command> --help` for detailed help on any command
- Check our [GitHub repository](https://github.com/DavGarcia/topoconvert) for issues and discussions

## License

TopoConvert is released under the MIT License. See the [LICENSE](../LICENSE) file for details.