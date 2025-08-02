# TopoConvert

A unified geospatial conversion toolkit for survey data processing and transformation.

## Overview

TopoConvert is a Python-based command-line tool that provides a comprehensive set of utilities for converting and processing geospatial survey data between various formats including KML, CSV, and DXF. It's designed specifically for surveyors, GIS professionals, and engineers who need to transform topographical data efficiently.

## Features

- **Multiple Format Support**: Convert between KML, CSV, and DXF formats
- **Contour Generation**: Create contour lines from point data
- **Mesh Generation**: Generate triangulated meshes from survey points
- **Slope Analysis**: Create slope heatmaps and analysis reports
- **GPS Grid Generation**: Generate GPS grid layouts for field work
- **Batch Processing**: Combine multiple DXF files into a single output
- **Coordinate System Support**: Handle various projection systems via pyproj

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
# Convert KML points to DXF contours
topoconvert kml-to-contours input.kml output.dxf --interval 1.0

# Convert CSV to KML
topoconvert csv-to-kml survey_data.csv output.kml --add-labels

# Generate slope heatmap
topoconvert slope-heatmap terrain.kml slope_analysis.png --slope-units degrees

# Combine multiple DXF files
topoconvert combined-dxf file1.dxf file2.dxf file3.dxf --output merged.dxf
```

## Available Commands

- `kml-to-contours` - Generate contour lines from KML point data
- `csv-to-kml` - Convert CSV survey data to KML format
- `kml-to-points` - Extract point data from KML files
- `kml-to-mesh` - Generate triangulated mesh from KML points
- `combined-dxf` - Merge multiple DXF files
- `kml-to-csv` - Convert KML data to CSV format
- `slope-heatmap` - Generate slope analysis visualizations
- `kml-contours-to-dxf` - Convert KML contour lines to DXF format
- `gps-grid` - Generate GPS grid layouts

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