"""Tests for core module structure."""
import pytest
from pathlib import Path


def test_core_module_exists():
    """Test that the core module directory exists."""
    core_dir = Path(__file__).parent.parent / 'topoconvert' / 'core'
    assert core_dir.exists(), "topoconvert/core directory does not exist"
    assert core_dir.is_dir(), "topoconvert/core should be a directory"


def test_core_module_has_init():
    """Test that core module has __init__.py."""
    core_dir = Path(__file__).parent.parent / 'topoconvert' / 'core'
    init_file = core_dir / '__init__.py'
    assert init_file.exists(), "topoconvert/core/__init__.py does not exist"


def test_core_exceptions_module():
    """Test that core exceptions module exists and can be imported."""
    try:
        from topoconvert.core import exceptions
        assert hasattr(exceptions, 'TopoConvertError')
        assert hasattr(exceptions, 'FileFormatError')
        assert hasattr(exceptions, 'ProcessingError')
        assert hasattr(exceptions, 'CoordinateError')
    except ImportError as e:
        pytest.fail(f"Failed to import core exceptions: {e}")


def test_core_utils_module():
    """Test that core utils module exists and has expected functions."""
    try:
        from topoconvert.core import utils
        # Check for common utility functions
        assert hasattr(utils, 'validate_file_path')
        assert hasattr(utils, 'ensure_file_extension')
        assert hasattr(utils, 'convert_elevation_units')
    except ImportError as e:
        pytest.fail(f"Failed to import core utils: {e}")


def test_exception_inheritance():
    """Test that custom exceptions inherit correctly."""
    from topoconvert.core.exceptions import (
        TopoConvertError,
        FileFormatError,
        ProcessingError,
        CoordinateError
    )
    
    # All should inherit from TopoConvertError
    assert issubclass(FileFormatError, TopoConvertError)
    assert issubclass(ProcessingError, TopoConvertError)
    assert issubclass(CoordinateError, TopoConvertError)
    
    # TopoConvertError should inherit from Exception
    assert issubclass(TopoConvertError, Exception)