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
- **Batch Processing**: Combine multiple DXF files efficiently
- **Coordinate System Support**: Handle various projections via pyproj

## Quick Links

- [Installation Guide](installation.md) - Get TopoConvert up and running
- [CLI Reference](cli_reference.md) - Detailed command documentation
- [Developer Guide](developer_guide.md) - Contributing and extending TopoConvert

## Example Usage

```bash
# Convert KML points to DXF contours
topoconvert kml-to-contours survey_points.kml contours.dxf --interval 0.5

# Generate slope analysis
topoconvert slope-heatmap terrain.kml slope_map.png --slope-units degrees

# Combine multiple DXF files
topoconvert combined-dxf file1.dxf file2.dxf --output merged.dxf
```

## Getting Help

- Use `topoconvert --help` to see all available commands
- Use `topoconvert <command> --help` for detailed help on any command
- Check our [GitHub repository](https://github.com/yourusername/topoconvert) for issues and discussions

## License

TopoConvert is released under the MIT License. See the [LICENSE](../LICENSE) file for details.