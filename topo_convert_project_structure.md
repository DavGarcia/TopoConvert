# TopoConvert Project Structure

A unified project layout for **TopoConvert**, a geospatial conversion toolkit with a single CLI entry point (`topoconvert`) and multiple subcommands for converting and processing survey data.

---

## Repository Structure

```
topoconvert/
│
├── topoconvert/                 # Main Python package
│   ├── __init__.py
│   ├── cli.py                   # CLI entry point (handles subcommands)
│   ├── commands/                # Subcommand modules
│   │   ├── kml_to_contours.py
│   │   ├── csv_to_kml.py
│   │   ├── kml_to_points.py
│   │   ├── kml_to_mesh.py
│   │   ├── combined_dxf.py
│   │   ├── kml_to_csv.py
│   │   ├── slope_heatmap.py
│   │   ├── kml_contours_to_dxf.py
│   │   └── gps_grid.py
│   ├── utils/                   # Shared utility functions
│   │   ├── file_io.py
│   │   ├── geometry.py
│   │   └── projection.py
│   └── __main__.py              # Allows `python -m topoconvert`
│
├── tests/                       # Automated tests
│   ├── test_kml_to_contours.py
│   ├── test_csv_to_kml.py
│   ├── test_kml_to_points.py
│   └── ...
│
├── examples/                    # Example input/output files and usage
│   ├── data/
│   │   ├── sample.kml
│   │   ├── sample.csv
│   │   └── ...
│   └── notebooks/
│       ├── quickstart.ipynb
│       └── slope_analysis_demo.ipynb
│
├── docs/                        # Project documentation
│   ├── index.md
│   ├── installation.md
│   ├── cli_reference.md
│   └── developer_guide.md
│
├── pyproject.toml               # Project metadata and dependencies
├── requirements.txt             # Optional pinned dependencies for dev
├── README.md                    # Project overview and basic usage
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # Open-source license
└── .github/
    └── workflows/               # CI/CD pipelines
        ├── lint.yml
        └── tests.yml
```

---

## Key Points

### 1. **Single CLI Entry Point (**``**)**

- Defined in `cli.py`.
- Uses `argparse` or `click` to handle subcommands.
- Each subcommand lives in its own file inside `commands/`.

### 2. **Commands Directory**

- One module per conversion type (`kml_to_contours.py`, `csv_to_kml.py`, etc.).
- Each module exposes a `register(subparsers)` function to add its CLI arguments.

### 3. **Utilities Directory**

- Shared helpers (file I/O, geometry manipulation, projections).
- Keeps command modules small and focused.

### 4. **Documentation**

- `docs/` folder for Markdown-based documentation.
- Includes CLI reference (auto-generated or manually maintained).

### 5. **Examples**

- Real-world KML, CSV, and DXF files.
- Jupyter notebooks showing usage and workflows.

### 6. **Tests**

- Unit tests for each command.
- Can be run via `pytest` or GitHub Actions.

### 7. **Packaging**

- `pyproject.toml` defines dependencies and the CLI entry point:

```toml
[project]
name = "topoconvert"
version = "0.1.0"
dependencies = ["shapely", "pandas", "ezdxf", "pyproj", "scipy", "numpy", "matplotlib", "alphashape", "concave_hull"]

[project.scripts]
topoconvert = "topoconvert.cli:main"
```

This creates a single executable `topoconvert` with multiple subcommands.

---

## Example CLI Usage

```bash
# Convert KML points to DXF contours
$ topoconvert kml-to-contours input.kml output.dxf --label

# Convert CSV to KML
$ topoconvert csv-to-kml input.csv output.kml --add-labels

# Generate slope heatmap
$ topoconvert slope-heatmap input.kml slope.png --slope-units degrees
```

---

This structure keeps the project modular, testable, and user-friendly while supporting a single unified CLI.

