# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TopoConvert is a planned Python-based CLI tool for converting and processing geospatial survey data between formats (KML, CSV, DXF) with specialized topographical operations. The project is currently in the architectural planning phase with no implementation yet.

## Development Commands

Since the project hasn't been implemented yet, here are the standard commands that will be used once the Python package is set up:

```bash
# Install package in development mode (once pyproject.toml exists)
pip install -e .

# Run the CLI tool
topoconvert <subcommand> [options]

# Run tests (once implemented)
pytest
pytest tests/test_specific_module.py  # Run single test file
pytest -k "test_name"                  # Run specific test

# Code quality checks (once configured)
black topoconvert/                     # Format code
flake8 topoconvert/                   # Lint code
mypy topoconvert/                     # Type checking
```

## Architecture

### CLI Structure
- **Single entry point**: `topoconvert` command with multiple subcommands
- **Commands**: Each conversion type is a separate subcommand in `topoconvert/commands/`
- **CLI framework**: Will use `argparse` or `click` for command parsing

### Conversion Commands
- `kml-to-contours`: KML points → DXF contours
- `csv-to-kml`: CSV data → KML format
- `kml-to-points`: Extract points from KML
- `kml-to-mesh`: Generate mesh from KML
- `combined-dxf`: Merge multiple DXF files
- `kml-to-csv`: KML → CSV format
- `slope-heatmap`: Generate slope visualizations
- `kml-contours-to-dxf`: KML contours → DXF
- `gps-grid`: Generate GPS grid layouts

### Key Dependencies
- **Geospatial**: `shapely`, `pyproj`
- **Data Processing**: `pandas`, `numpy`, `scipy`
- **File Formats**: `ezdxf` (DXF handling)
- **Visualization**: `matplotlib`
- **Advanced Geometry**: `alphashape`, `concave_hull`

### Code Organization
- `topoconvert/cli.py`: Main CLI entry point and subcommand registration
- `topoconvert/commands/`: Individual conversion modules, each exposing a `register(subparsers)` function
- `topoconvert/utils/`: Shared utilities for file I/O, geometry operations, and projections

## Implementation Guidelines

When implementing features:

1. **Command Module Pattern**: Each command should follow this structure:
   ```python
   def register(subparsers):
       parser = subparsers.add_parser('command-name', help='Description')
       parser.add_argument('input', help='Input file')
       parser.add_argument('output', help='Output file')
       parser.set_defaults(func=execute)
   
   def execute(args):
       # Implementation here
       pass
   ```

2. **Coordinate Systems**: Always handle projection transformations explicitly using `pyproj`

3. **Error Handling**: Provide clear error messages for common issues (invalid file formats, projection mismatches, etc.)

4. **Testing**: Write tests for each conversion command with sample data in `examples/data/`

## Next Steps for Implementation

1. Create `pyproject.toml` with project metadata and dependencies
2. Implement `topoconvert/cli.py` with basic command structure
3. Create `topoconvert/commands/` directory and implement first conversion command
4. Set up pytest infrastructure in `tests/`
5. Add sample data files in `examples/data/`