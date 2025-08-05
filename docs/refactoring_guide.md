# Core Module Refactoring Guide

This guide documents the refactoring approach for decoupling core modules from CLI dependencies.

## Problem Statement

Currently, core modules in `topoconvert/core/` use `click.echo()` to print status messages directly to the console. This creates tight coupling between the core logic and the CLI, making it difficult to:
- Use core modules as a library
- Write proper unit tests
- Integrate with other interfaces (GUI, web API, etc.)

## Solution Approach

Replace direct console output with structured result objects that contain all relevant information about the operation.

## Implementation Pattern

### 1. Create Result Types

Result types are defined in `topoconvert/core/result_types.py`:

```python
@dataclass
class ProcessingResult:
    """Base result type for all processing operations."""
    success: bool
    output_file: str
    message: str = ""
    details: Dict[str, Any] = None
    warnings: List[str] = None
```

Each core module gets its own specialized result type that extends `ProcessingResult`.

### 2. Update Core Functions

Core functions should:
- Remove all `import click` statements
- Replace `click.echo()` calls with data collection
- Return a result object instead of `None`

**Before:**
```python
import click

def process_data(input_file: Path) -> None:
    # Process...
    click.echo(f"Found {count} items")
    click.echo(f"Created output: {output_file}")
```

**After:**
```python
from topoconvert.core.result_types import ProcessingResult

def process_data(input_file: Path) -> ProcessingResult:
    # Process...
    return ProcessingResult(
        success=True,
        output_file=str(output_file),
        details={"item_count": count}
    )
```

### 3. Update CLI Commands

CLI commands should:
- Call the core function and receive the result
- Format and display the result information using `click.echo()`
- Handle errors based on the result status

**Example:**
```python
def command(input_file):
    result = core_function(input_file)
    
    if result.success:
        click.echo(f"Found {result.details['item_count']} items")
        click.echo(f"Created output: {result.output_file}")
    else:
        click.echo(f"Error: {result.message}", err=True)
```

## Module-Specific Refactoring

### points.py
- Return: `PointExtractionResult`
- Key data: point_count, coordinate_ranges, reference_point, coordinate_system

### contours.py
- Return: `ContourGenerationResult` 
- Key data: contour_count, elevation_levels, elevation_range

### mesh.py
- Return: `MeshGenerationResult`
- Key data: face_count, vertex_count, edge_count, mesh_type

### gps_grid.py
- Return: `GridGenerationResult`
- Key data: grid_points, spacing, boundary_type

### csv_kml.py
- Return: `CSVToKMLResult`
- Key data: valid_points, coordinate_bounds, elevation_units

### slope_heatmap.py
- Return: `SlopeHeatmapResult`
- Key data: grid_resolution, slope_units, point_count

### combined_dxf.py
- Return: `CombinedDXFResult`
- Key data: input_file_count, total_points, layers_created

### combined_kml.py
- Return: `CombinedKMLResult`
- Key data: input_file_count, total_points

### kml_contours.py
- Return: `KMLContoursResult`
- Key data: contour_count, missing_elevations, coordinate_system

## Testing Strategy

1. **Unit Tests for Result Types**: Test that result objects can be created and contain expected fields
2. **Core Module Tests**: Test that functions return proper result objects with correct data
3. **CLI Integration Tests**: Test that CLI commands properly display result information

## Migration Approach

1. **Phase 1**: Create result types and example refactoring (completed)
2. **Phase 2**: Refactor one module at a time, updating both core and CLI
3. **Phase 3**: Update all tests to work with new result objects
4. **Phase 4**: Remove all click imports from core modules

## Benefits

- **Decoupled Architecture**: Core logic independent of presentation layer
- **Better Testing**: Can test core logic without mocking click.echo
- **Reusability**: Core modules can be used in non-CLI contexts
- **Type Safety**: Result objects provide clear contracts
- **Structured Data**: All operation details available programmatically