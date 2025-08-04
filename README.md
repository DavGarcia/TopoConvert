# TopoConvert

A unified geospatial conversion toolkit for survey data processing and transformation.

## Overview

TopoConvert is a Python-based command-line tool that provides a comprehensive set of utilities for converting and processing geospatial survey data between various formats including KML, CSV, and DXF. It's designed specifically for surveyors, GIS professionals, and engineers who need to transform topographical data efficiently.

## Features

- **Multiple Format Support**: Convert between KML, CSV, and DXF formats
- **Contour Generation**: Create contour lines from point data with customizable intervals
- **Mesh Generation**: Generate triangulated meshes from survey points (with optional wireframe)
- **Slope Analysis**: Create slope heatmaps with contours, target slope settings, and color-blind friendly options
- **GPS Grid Generation**: Generate GPS grid layouts within property boundaries (supports convex/concave hulls)
- **Batch Processing**: Combine multiple CSV files into DXF (separate layers) or KML
- **Coordinate System Support**: Handle various projection systems via pyproj
- **Smart Defaults**: Optional output files automatically named based on input
- **No Progress Bars**: Clean, distraction-free command execution

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/topoconvert.git
cd topoconvert

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### From PyPI (Coming Soon)

```bash
pip install topoconvert
```

## Quick Start

TopoConvert provides a single CLI with multiple subcommands:

```bash
# Convert KML points to DXF contours (output file optional)
topoconvert kml-to-dxf-contours input.kml --interval 1.0

# Convert CSV to KML
topoconvert csv-to-kml survey_data.csv output.kml --add-labels

# Generate slope heatmap (output file optional, contours shown by default)
topoconvert slope-heatmap terrain.kml --target-slope 5.0

# Combine multiple CSV files to DXF on separate layers
topoconvert multi-csv-to-dxf file1.csv file2.csv file3.csv --output merged.dxf

# Combine multiple CSV files to KML
topoconvert multi-csv-to-kml file1.csv file2.csv file3.csv output.kml
```

## Available Commands

### Data Conversion
- `csv-to-kml` - Convert CSV survey data to KML format
- `kml-to-csv` - Convert KML data to CSV format
- `kml-to-points` - Extract points from KML (supports DXF, CSV, JSON, TXT output)

### DXF Generation
- `kml-to-dxf-contours` - Generate contour lines from KML point data
- `kml-to-dxf-mesh` - Generate triangulated mesh from KML points (wireframe by default)
- `kml-contours-to-dxf` - Convert KML contour lines to DXF format
- `multi-csv-to-dxf` - Merge multiple CSV files to DXF on separate layers

### KML Generation
- `multi-csv-to-kml` - Combine multiple CSV files into a single KML
- `gps-grid` - Generate GPS grid points within property boundaries

### Analysis & Visualization
- `slope-heatmap` - Generate slope analysis PNG (contours by default, color-blind friendly options)

For detailed usage of each command:

```bash
topoconvert <command> --help
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=topoconvert

# Run specific test file
pytest tests/test_kml_to_contours.py
```

### Code Quality

```bash
# Format code
black topoconvert/

# Lint code
flake8 topoconvert/

# Type checking
mypy topoconvert/
```

### Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Documentation

Full documentation is available in the [docs/](docs/) directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Shapely](https://shapely.readthedocs.io/) for geometric operations
- Uses [ezdxf](https://ezdxf.readthedocs.io/) for DXF file handling
- Powered by [pandas](https://pandas.pydata.org/) for data manipulation
- Coordinate transformations via [pyproj](https://pyproj4.github.io/pyproj/)

## Support

For bug reports and feature requests, please use the [GitHub issue tracker](https://github.com/yourusername/topoconvert/issues).