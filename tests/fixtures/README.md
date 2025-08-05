# Test Fixtures

This directory contains test KML files for the TopoConvert test suite. These files are small, minimal examples designed to test specific functionality.

## Files

### Valid KML Files

- **`simple_3points.kml`** - Minimal valid KML with 3 elevation points
  - Used for: Basic functionality tests
  - Points: 3 points with elevations 100m, 110m, 120m

- **`grid_4x4.kml`** - 16 points in a 4x4 grid pattern
  - Used for: Grid interpolation and contouring tests
  - Points: Regular grid with gradual elevation increase (100m to 115m)

- **`sparse_data.kml`** - Very sparse data (3 points far apart)
  - Used for: Testing interpolation fallback mechanisms
  - Points: 3 points with 0.01 degree spacing

- **`steep_slope.kml`** - Points with extreme elevation changes
  - Used for: Testing steep slope calculations
  - Points: 6 points with 100m+ elevation changes over small distances

- **`no_elevation.kml`** - Points without elevation data
  - Used for: Testing default elevation handling
  - Points: 3 points without elevation, 1 with elevation

### Error Testing Files

- **`empty.kml`** - Valid KML with no placemarks
  - Used for: Testing "no points found" error handling

- **`invalid_coords.kml`** - KML with some invalid coordinates
  - Used for: Testing coordinate parsing error handling
  - Contains: Non-numeric values, missing coordinates

## Usage in Tests

```python
from pathlib import Path

def test_basic_functionality():
    fixtures_dir = Path(__file__).parent / "fixtures"
    kml_file = fixtures_dir / "simple_3points.kml"
    
    result = generate_slope_heatmap(
        input_file=kml_file,
        output_file=output_path
    )
```

## Adding New Fixtures

When adding new test files:
1. Keep files minimal - only include data needed for the test
2. Use descriptive names that indicate the test purpose
3. Update this README with the file's purpose and contents
4. Ensure all coordinates are valid WGS84 (longitude, latitude, elevation)