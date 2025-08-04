"""Tests for CSV to KML conversion module."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from topoconvert.core.exceptions import FileFormatError, ProcessingError


def test_csv_kml_module_exists():
    """Test that csv_kml module can be imported."""
    try:
        from topoconvert.core import csv_kml
        assert hasattr(csv_kml, 'convert_csv_to_kml')
    except ImportError as e:
        pytest.fail(f"Failed to import csv_kml module: {e}")


def test_convert_csv_to_kml_validates_input():
    """Test that convert_csv_to_kml validates input file."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        convert_csv_to_kml(
            input_file=Path("nonexistent.csv"),
            output_file=Path("output.kml")
        )


def test_convert_csv_to_kml_validates_parameters():
    """Test parameter validation."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Create a mock file that exists
    with patch('pathlib.Path.exists', return_value=True):
        # Test invalid elevation units
        with pytest.raises(ValueError, match="elevation_units"):
            convert_csv_to_kml(
                input_file=Path("test.csv"),
                output_file=Path("output.kml"),
                elevation_units="invalid"
            )
        
        # Test invalid point style
        with pytest.raises(ValueError, match="point_style"):
            convert_csv_to_kml(
                input_file=Path("test.csv"),
                output_file=Path("output.kml"),
                point_style="invalid"
            )
        
        # Test invalid color format
        with pytest.raises(ValueError, match="color"):
            convert_csv_to_kml(
                input_file=Path("test.csv"),
                output_file=Path("output.kml"),
                point_color="invalid"
            )


def test_convert_csv_to_kml_with_sample_data(sample_csv_file, temp_dir):
    """Test CSV to KML conversion with sample data."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    output_file = temp_dir / "output.kml"
    
    # Mock the actual processing for now
    with patch('topoconvert.core.csv_kml._process_csv_to_kml') as mock_process:
        mock_process.return_value = None
        
        convert_csv_to_kml(
            input_file=sample_csv_file,
            output_file=output_file,
            elevation_units='meters',
            add_labels=True
        )
        
        # Verify the mock was called with correct parameters
        mock_process.assert_called_once()


def test_convert_csv_to_kml_custom_columns():
    """Test conversion with custom column names."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('topoconvert.core.csv_kml._process_csv_to_kml') as mock_process:
            mock_process.return_value = None
            
            convert_csv_to_kml(
                input_file=Path("test.csv"),
                output_file=Path("output.kml"),
                x_column='lon',
                y_column='lat',
                z_column='alt'
            )
            
            # Verify custom columns were passed
            call_args = mock_process.call_args[1]
            assert call_args['x_column'] == 'lon'
            assert call_args['y_column'] == 'lat'
            assert call_args['z_column'] == 'alt'