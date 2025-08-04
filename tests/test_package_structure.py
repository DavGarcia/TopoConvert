"""Test Python package structure and imports."""
import importlib
import os
from pathlib import Path


def test_package_directory_exists():
    """Test that the topoconvert package directory exists."""
    package_dir = Path(__file__).parent.parent / 'topoconvert'
    assert package_dir.exists(), "topoconvert package directory does not exist"
    assert package_dir.is_dir(), "topoconvert should be a directory"


def test_package_has_init():
    """Test that the package has __init__.py files."""
    package_dir = Path(__file__).parent.parent / 'topoconvert'
    
    # Check main package
    init_file = package_dir / '__init__.py'
    assert init_file.exists(), "topoconvert/__init__.py does not exist"
    
    # Check subpackages
    subpackages = ['commands', 'utils']
    for subpackage in subpackages:
        subpackage_init = package_dir / subpackage / '__init__.py'
        assert subpackage_init.exists(), f"topoconvert/{subpackage}/__init__.py does not exist"


def test_cli_module_exists():
    """Test that cli.py exists and has main function."""
    package_dir = Path(__file__).parent.parent / 'topoconvert'
    cli_file = package_dir / 'cli.py'
    assert cli_file.exists(), "topoconvert/cli.py does not exist"


def test_command_modules_exist():
    """Test that all command modules exist."""
    package_dir = Path(__file__).parent.parent / 'topoconvert'
    commands_dir = package_dir / 'commands'
    
    expected_commands = [
        'kml_to_contours.py',
        'csv_to_kml.py',
        'kml_to_points.py',
        'kml_to_mesh.py',
        'combined_dxf.py',
        'kml_to_csv.py',
        'slope_heatmap.py',
        'kml_contours_to_dxf.py',
        'gps_grid.py',
    ]
    
    for command in expected_commands:
        command_file = commands_dir / command
        assert command_file.exists(), f"Command module {command} does not exist"


def test_util_modules_exist():
    """Test that utility modules exist."""
    package_dir = Path(__file__).parent.parent / 'topoconvert'
    utils_dir = package_dir / 'utils'
    
    expected_utils = [
        'file_io.py',
        'geometry.py',
        'projection.py',
    ]
    
    for util in expected_utils:
        util_file = utils_dir / util
        assert util_file.exists(), f"Utility module {util} does not exist"


def test_package_importable():
    """Test that the package can be imported."""
    try:
        import topoconvert
        assert topoconvert is not None
    except ImportError as e:
        assert False, f"Failed to import topoconvert: {e}"


def test_main_py_exists():
    """Test that __main__.py exists for python -m execution."""
    package_dir = Path(__file__).parent.parent / 'topoconvert'
    main_file = package_dir / '__main__.py'
    assert main_file.exists(), "topoconvert/__main__.py does not exist"