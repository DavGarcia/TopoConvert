# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TopoConvert is a fully implemented Python-based CLI tool for converting and processing geospatial survey data between formats (KML, CSV, DXF) with specialized topographical operations. The project is production-ready with comprehensive tests and documentation.

## Development Commands

```bash
# Install package in development mode
pip install -e .

# Run the CLI tool
topoconvert <subcommand> [options]

# Run tests
pytest
pytest tests/test_specific_module.py  # Run single test file
pytest -k "test_name"                  # Run specific test
pytest --cov=topoconvert              # Run with coverage

# Code quality checks
black topoconvert/                     # Format code
flake8 topoconvert/                   # Lint code
mypy topoconvert/                     # Type checking
```

## Architecture

### CLI Structure
- **Single entry point**: `topoconvert` command with multiple subcommands
- **Commands**: Each conversion type is implemented as a separate subcommand in `topoconvert/commands/`
- **CLI framework**: Uses `click` for command parsing and argument handling
- **Core modules**: Business logic separated in `topoconvert/core/` for testability and reusability

### Available Commands
- `csv-to-kml`: Convert CSV survey data to KML format
- `gps-grid`: Generate GPS grid points within property boundaries
- `kml-contours-to-dxf`: Convert KML contour LineStrings to DXF format
- `kml-to-dxf-contours`: Convert KML points to DXF contours
- `kml-to-dxf-mesh`: Generate 3D TIN mesh from KML points
- `kml-to-points`: Extract point data from KML files (supports DXF, CSV, JSON, TXT output)
- `multi-csv-to-dxf`: Merge CSV files to DXF with separate layers
- `multi-csv-to-kml`: Merge CSV files to KML with separate folders
- `slope-heatmap`: Generate slope heatmap from elevation data

### Key Dependencies
- **CLI Framework**: `click` for command-line interface
- **Geospatial**: `shapely`, `pyproj` for geometry and projections
- **Data Processing**: `pandas`, `numpy`, `scipy` for data manipulation
- **File Formats**: `ezdxf` for DXF file handling
- **Visualization**: `matplotlib` for slope heatmaps
- **Advanced Geometry**: `alphashape`, `concave_hull` for boundary analysis

### Code Organization
- `topoconvert/cli.py`: Main CLI entry point with Click-based command registration
- `topoconvert/commands/`: Individual command implementations using Click decorators
- `topoconvert/core/`: Core business logic modules with structured result types
- `topoconvert/utils/`: Shared utilities for projections and common operations
- `tests/`: Comprehensive test suite with 350+ tests covering all functionality

## Implementation Guidelines

When implementing features:

1. **Click Command Pattern**: Each command uses Click decorators:
   ```python
   import click
   from topoconvert.core.module_name import core_function
   
   @click.command()
   @click.argument('input_file', type=click.Path(exists=True))
   @click.argument('output_file', type=click.Path(), required=False)
   @click.option('--option-name', default=value, help='Description')
   def command_name(input_file, output_file, option_name):
       \"\"\"Command description.\"\"\"
       try:
           result = core_function(input_file, output_file, option_name=option_name)
           click.echo(f"Success: {result.success}")
       except Exception as e:
           click.echo(f"Error: {e}", err=True)
           raise click.Abort()
   ```

2. **Result Types**: All core functions return structured result objects for consistency:
   ```python
   @dataclass
   class ProcessingResult:
       success: bool
       output_file: str
       details: dict = field(default_factory=dict)
   ```

3. **Coordinate Systems**: Handle projection transformations using the utilities in `topoconvert.utils.projection`

4. **Error Handling**: Use custom exceptions from `topoconvert.core.exceptions` with clear messages

5. **Testing**: Write comprehensive tests using pytest with fixtures in `tests/` directory

## Project Status

✅ **Fully Implemented Features:**
- All CLI commands functional and tested
- Core modules with proper separation of concerns
- Comprehensive test suite (350+ tests)
- Package building and distribution ready
- Documentation and usage examples
- Result type system for structured outputs
- Custom exception handling
- Coordinate projection utilities

## Virtual Environment Usage

This project uses `venv` for Python environment management. When running Python commands, use:

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Use venv Python for all commands
venv/bin/python -m pytest  # Instead of just: pytest
```