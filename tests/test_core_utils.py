"""Tests for core utility functions."""
import pytest
import tempfile
from pathlib import Path
import numpy as np
from topoconvert.core.utils import (
    validate_file_path,
    ensure_file_extension,
    convert_elevation_units,
    meters_to_feet,
    feet_to_meters,
    parse_color_string,
    format_coordinates,
    calculate_bounds
)


class TestValidateFilePath:
    """Test cases for validate_file_path function."""
    
    def test_valid_existing_file(self, temp_dir):
        """Test validation of existing file."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        # Test with string path
        result = validate_file_path(str(test_file))
        assert isinstance(result, Path)
        assert result == test_file
        
        # Test with Path object
        result = validate_file_path(test_file)
        assert result == test_file
    
    def test_valid_non_existing_file(self):
        """Test validation when must_exist=False."""
        non_existing = Path("non_existing_file.txt")
        
        result = validate_file_path(non_existing, must_exist=False)
        assert isinstance(result, Path)
        assert result == non_existing
    
    def test_file_not_found_error(self):
        """Test error when file doesn't exist and must_exist=True."""
        non_existing = "non_existing_file.txt"
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_path(non_existing, must_exist=True)
    
    def test_invalid_path(self):
        """Test error with invalid path."""
        # Test with file that doesn't exist
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_path("/this/path/does/not/exist/at/all.txt")


class TestEnsureFileExtension:
    """Test cases for ensure_file_extension function."""
    
    def test_add_extension(self):
        """Test adding extension to file without one."""
        path = Path("test_file")
        result = ensure_file_extension(path, ".txt")
        assert result == Path("test_file.txt")
        
        # Test without dot in extension
        result = ensure_file_extension(path, "txt")
        assert result == Path("test_file.txt")
    
    def test_correct_extension(self):
        """Test file with correct extension."""
        path = Path("test_file.txt")
        result = ensure_file_extension(path, ".txt")
        assert result == path
    
    def test_replace_extension(self):
        """Test replacing incorrect extension."""
        path = Path("test_file.doc")
        result = ensure_file_extension(path, ".txt")
        assert result == Path("test_file.txt")
    
    def test_case_insensitive(self):
        """Test case-insensitive extension matching."""
        path = Path("test_file.TXT")
        result = ensure_file_extension(path, ".txt")
        assert result == path  # Should keep original


class TestConvertElevationUnits:
    """Test cases for convert_elevation_units function."""
    
    def test_same_units(self):
        """Test conversion when units are the same."""
        assert convert_elevation_units(100.0, 'meters', 'meters') == 100.0
        assert convert_elevation_units(328.084, 'feet', 'feet') == 328.084
    
    def test_meters_to_feet(self):
        """Test conversion from meters to feet."""
        result = convert_elevation_units(100.0, 'meters', 'feet')
        assert result == pytest.approx(328.084, rel=1e-3)
        
        # Test zero
        assert convert_elevation_units(0.0, 'meters', 'feet') == 0.0
    
    def test_feet_to_meters(self):
        """Test conversion from feet to meters."""
        result = convert_elevation_units(328.084, 'feet', 'meters')
        assert result == pytest.approx(100.0, rel=1e-3)
        
        # Test zero
        assert convert_elevation_units(0.0, 'feet', 'meters') == 0.0
    
    def test_negative_values(self):
        """Test conversion with negative values."""
        result = convert_elevation_units(-100.0, 'meters', 'feet')
        assert result == pytest.approx(-328.084, rel=1e-3)
    
    def test_invalid_units(self):
        """Test error with invalid units."""
        with pytest.raises(ValueError, match="Invalid units"):
            convert_elevation_units(100.0, 'meters', 'yards')
        
        with pytest.raises(ValueError, match="Invalid units"):
            convert_elevation_units(100.0, 'kilometers', 'feet')


class TestUnitConversionHelpers:
    """Test cases for meters_to_feet and feet_to_meters functions."""
    
    def test_meters_to_feet(self):
        """Test meters to feet conversion."""
        assert meters_to_feet(100.0) == pytest.approx(328.084, rel=1e-3)
        assert meters_to_feet(0.0) == 0.0
        assert meters_to_feet(-10.0) == pytest.approx(-32.8084, rel=1e-3)
    
    def test_feet_to_meters(self):
        """Test feet to meters conversion."""
        assert feet_to_meters(328.084) == pytest.approx(100.0, rel=1e-3)
        assert feet_to_meters(0.0) == 0.0
        assert feet_to_meters(-32.8084) == pytest.approx(-10.0, rel=1e-3)
    
    def test_round_trip_conversion(self):
        """Test round-trip conversion accuracy."""
        original = 123.456
        # Meters -> Feet -> Meters
        result = feet_to_meters(meters_to_feet(original))
        assert result == pytest.approx(original, rel=1e-6)
        
        # Feet -> Meters -> Feet
        original_ft = 405.0
        result_ft = meters_to_feet(feet_to_meters(original_ft))
        assert result_ft == pytest.approx(original_ft, rel=1e-6)


class TestParseColorString:
    """Test cases for parse_color_string function."""
    
    def test_valid_color(self):
        """Test parsing valid color string."""
        # Test opaque red (AABBGGRR format)
        result = parse_color_string('ff0000ff')
        assert result == (255, 0, 0, 255)  # RGBA
        
        # Test semi-transparent green
        result = parse_color_string('8000ff00')
        assert result == (0, 255, 0, 128)
        
        # Test opaque blue
        result = parse_color_string('ffff0000')
        assert result == (0, 0, 255, 255)
    
    def test_mixed_colors(self):
        """Test parsing mixed color values."""
        # Test purple (red + blue)
        result = parse_color_string('ffff00ff')
        assert result == (255, 0, 255, 255)
        
        # Test white
        result = parse_color_string('ffffffff')
        assert result == (255, 255, 255, 255)
        
        # Test black
        result = parse_color_string('ff000000')
        assert result == (0, 0, 0, 255)
    
    def test_invalid_length(self):
        """Test error with wrong length color string."""
        with pytest.raises(ValueError, match="8 characters"):
            parse_color_string('ff00ff')  # Too short
        
        with pytest.raises(ValueError, match="8 characters"):
            parse_color_string('ff00ff00ff')  # Too long
    
    def test_invalid_hex(self):
        """Test error with invalid hex characters."""
        with pytest.raises(ValueError, match="Invalid color format"):
            parse_color_string('ff00ggxx')  # Invalid hex


class TestFormatCoordinates:
    """Test cases for format_coordinates function."""
    
    def test_default_precision(self):
        """Test formatting with default precision."""
        result = format_coordinates(123.456789, -45.678901)
        assert result == "(123.456789, -45.678901)"
    
    def test_custom_precision(self):
        """Test formatting with custom precision."""
        result = format_coordinates(123.456789, -45.678901, precision=2)
        assert result == "(123.46, -45.68)"
        
        result = format_coordinates(123.456789, -45.678901, precision=0)
        assert result == "(123, -46)"
    
    def test_large_numbers(self):
        """Test formatting large coordinate values."""
        result = format_coordinates(1234567.89, -987654.321, precision=3)
        assert result == "(1234567.890, -987654.321)"
    
    def test_zero_values(self):
        """Test formatting zero coordinates."""
        result = format_coordinates(0.0, 0.0, precision=1)
        assert result == "(0.0, 0.0)"


class TestCalculateBounds:
    """Test cases for calculate_bounds function."""
    
    def test_2d_points(self):
        """Test bounds calculation with 2D points."""
        points = [
            (0, 0),
            (10, 5),
            (5, 10),
            (-5, 2)
        ]
        
        bounds = calculate_bounds(points)
        assert bounds == (-5, 0, 10, 10)
    
    def test_3d_points(self):
        """Test bounds calculation with 3D points (ignores Z)."""
        points = [
            (0, 0, 100),
            (10, 5, 200),
            (5, 10, 150),
            (-5, 2, 50)
        ]
        
        bounds = calculate_bounds(points)
        assert bounds == (-5, 0, 10, 10)
    
    def test_single_point(self):
        """Test bounds with single point."""
        points = [(5.5, 3.3)]
        bounds = calculate_bounds(points)
        assert bounds == (5.5, 3.3, 5.5, 3.3)
    
    def test_negative_coordinates(self):
        """Test bounds with all negative coordinates."""
        points = [
            (-10, -20),
            (-5, -15),
            (-30, -5)
        ]
        
        bounds = calculate_bounds(points)
        assert bounds == (-30, -20, -5, -5)
    
    def test_empty_points(self):
        """Test error with empty points list."""
        with pytest.raises(ValueError, match="No points provided"):
            calculate_bounds([])
    
    def test_numpy_array_input(self):
        """Test bounds calculation with numpy array input."""
        points = np.array([
            [0, 0],
            [10, 5],
            [5, 10],
            [-5, 2]
        ])
        
        bounds = calculate_bounds(points)
        assert bounds == (-5, 0, 10, 10)


