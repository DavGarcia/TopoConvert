# Developer Guide

This guide is for developers who want to contribute to TopoConvert or extend its functionality.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Virtual environment tool (venv, virtualenv, or conda)

### Setting Up Your Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/DavGarcia/topoconvert.git
   cd topoconvert
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode with all dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Project Structure

```
topoconvert/
├── topoconvert/           # Main package
│   ├── __init__.py       # Package initialization
│   ├── cli.py            # CLI entry point
│   ├── commands/         # Command implementations
│   │   ├── __init__.py
│   │   ├── kml_to_contours.py
│   │   └── ...
│   └── utils/            # Shared utilities
│       ├── __init__.py
│       ├── file_io.py
│       ├── geometry.py
│       └── projection.py
├── tests/                # Test suite
├── docs/                 # Documentation
├── examples/             # Example data and notebooks
└── pyproject.toml       # Project configuration
```

## Adding a New Command

To add a new conversion command to TopoConvert:

1. **Create a new module** in `topoconvert/commands/`:
   ```python
   # topoconvert/commands/your_command.py
   import click
   
   def register(cli):
       """Register the command with the CLI."""
       @cli.command('your-command')
       @click.argument('input_file', type=click.Path(exists=True))
       @click.argument('output_file', type=click.Path())
       def your_command(input_file, output_file):
           """Brief description of your command."""
           # Implementation here
           pass
   ```

2. **Import and register** in `topoconvert/cli.py`:
   ```python
   from topoconvert.commands import your_command
   your_command.register(cli)
   ```

3. **Add tests** in `tests/test_your_command.py`

4. **Update documentation** in `docs/cli_reference.md`

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Maximum line length: 88 characters (Black default)
- Use type hints where possible

### Docstrings

Use Google-style docstrings:

```python
def transform_points(points: List[Tuple[float, float]], 
                    from_crs: str, 
                    to_crs: str) -> List[Tuple[float, float]]:
    """Transform points between coordinate systems.
    
    Args:
        points: List of (x, y) coordinate tuples
        from_crs: Source coordinate system (EPSG code)
        to_crs: Target coordinate system (EPSG code)
        
    Returns:
        List of transformed (x, y) coordinate tuples
        
    Raises:
        ValueError: If CRS is invalid
    """
```

### Imports

Organize imports in the following order:
1. Standard library imports
2. Third-party imports
3. Local application imports

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=topoconvert

# Run specific test file
pytest tests/test_kml_to_contours.py

# Run specific test
pytest tests/test_kml_to_contours.py::test_basic_conversion
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files as `test_<module_name>.py`
- Use descriptive test function names
- Include both positive and negative test cases
- Use fixtures for common test data

Example test:

```python
def test_contour_generation(sample_kml_file, temp_dir):
    """Test basic contour generation from KML points."""
    output_file = temp_dir / "contours.dxf"
    
    runner = CliRunner()
    result = runner.invoke(cli, [
        'kml-to-contours',
        str(sample_kml_file),
        str(output_file),
        '--interval', '1.0'
    ])
    
    assert result.exit_code == 0
    assert output_file.exists()
```

## Code Quality Tools

### Formatting

```bash
# Format code with Black
black topoconvert/

# Check without modifying
black --check topoconvert/
```

### Linting

```bash
# Run flake8
flake8 topoconvert/

# Run mypy for type checking
mypy topoconvert/
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## Debugging Tips

### CLI Debugging

Use Click's built-in debugging:

```python
# Enable debug mode
cli(standalone_mode=False)

# Use click.echo for debug output
click.echo(f"Debug: Processing {len(points)} points", err=True)
```

### Using IPython

For interactive debugging:

```python
# Add breakpoint in code
import IPython; IPython.embed()
```

## Performance Considerations

- Use numpy arrays for large numerical operations
- Implement streaming for large files
- Add progress bars for long operations using `click.progressbar()`
- Profile code with cProfile for optimization

## Contributing Workflow

1. **Create an issue** describing the feature or bug
2. **Fork the repository** and create a feature branch
3. **Make your changes** following the style guidelines
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Run tests and linting** locally
7. **Submit a pull request** with a clear description

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will handle the PyPI release

## Getting Help

- Check existing issues on GitHub
- Join discussions in the repository
- Review the codebase for examples
- Ask questions in pull requests

Thank you for contributing to TopoConvert!