# Installation Guide

This guide will help you install TopoConvert on your system.

## Requirements

- Python 3.8 or higher
- pip package manager

## Installation Methods

### From PyPI (Recommended - Coming Soon)

Once published, you'll be able to install TopoConvert directly from PyPI:

```bash
pip install topoconvert
```

### From Source (Development)

For the latest development version or to contribute:

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/topoconvert.git
   cd topoconvert
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Linux/macOS:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e .
   ```

4. **Install development dependencies** (optional)
   ```bash
   pip install -e ".[dev]"
   ```

## Verifying Installation

After installation, verify that TopoConvert is working:

```bash
topoconvert --version
topoconvert --help
```

## Dependencies

TopoConvert relies on several scientific Python packages:

- **shapely** - Geometric operations and transformations
- **pandas** - Data manipulation and CSV handling
- **ezdxf** - DXF file reading and writing
- **pyproj** - Coordinate system transformations
- **scipy** - Scientific computing and interpolation
- **numpy** - Numerical operations
- **matplotlib** - Visualization and heatmap generation
- **alphashape** - Alpha shape calculations
- **concave_hull** - Concave hull generation
- **click** - Command-line interface framework

These dependencies will be automatically installed when you install TopoConvert.

## Platform-Specific Notes

### Windows

- Ensure you have Python installed from [python.org](https://python.org)
- Some geospatial libraries may require Visual C++ redistributables

### macOS

- Python 3 can be installed via Homebrew: `brew install python`
- Some dependencies may require Xcode Command Line Tools

### Linux

- Most distributions include Python 3
- You may need to install development headers: `sudo apt-get install python3-dev` (Ubuntu/Debian)

## Troubleshooting

### Import Errors

If you encounter import errors, ensure all dependencies are installed:

```bash
pip install --upgrade -r requirements.txt
```

### Permission Errors

On Unix-like systems, you may need to use `sudo` for system-wide installation:

```bash
sudo pip install topoconvert
```

However, using a virtual environment is recommended to avoid permission issues.

### Dependency Conflicts

If you have conflicting package versions, create a fresh virtual environment:

```bash
python -m venv fresh_env
source fresh_env/bin/activate  # or fresh_env\Scripts\activate on Windows
pip install topoconvert
```

## Next Steps

- Check out the [CLI Reference](cli_reference.md) to learn about available commands
- See the [Developer Guide](developer_guide.md) if you want to contribute