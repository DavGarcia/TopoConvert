"""Tests for contours generation module."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from topoconvert.core.exceptions import FileFormatError, ProcessingError


def test_contours_module_exists():
    """Test that contours module can be imported."""
    try:
        from topoconvert.core import contours
        assert hasattr(contours, 'generate_contours')
    except ImportError as e:
        pytest.fail(f"Failed to import contours module: {e}")


def test_generate_contours_validates_input():
    """Test that generate_contours validates input file."""
    from topoconvert.core.contours import generate_contours
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        generate_contours(
            input_file=Path("nonexistent.kml"),
            output_file=Path("output.dxf")
        )


def test_generate_contours_validates_parameters():
    """Test parameter validation."""
    from topoconvert.core.contours import generate_contours
    
    # Create a mock file that exists
    with patch('pathlib.Path.exists', return_value=True):
        # Test invalid elevation units
        with pytest.raises(ValueError, match="elevation_units"):
            generate_contours(
                input_file=Path("test.kml"),
                output_file=Path("output.dxf"),
                elevation_units="invalid"
            )
        
        # Test invalid contour interval
        with pytest.raises(ValueError, match="contour_interval"):
            generate_contours(
                input_file=Path("test.kml"),
                output_file=Path("output.dxf"),
                contour_interval=-1.0
            )
        
        # Test invalid grid resolution
        with pytest.raises(ValueError, match="grid_resolution"):
            generate_contours(
                input_file=Path("test.kml"),
                output_file=Path("output.dxf"),
                grid_resolution=0
            )


def test_generate_contours_with_sample_data(sample_kml_file, temp_dir):
    """Test contour generation with sample KML data."""
    from topoconvert.core.contours import generate_contours
    
    output_file = temp_dir / "contours.dxf"
    
    # Mock the actual processing for now
    with patch('topoconvert.core.contours._process_contours') as mock_process:
        mock_process.return_value = None
        
        generate_contours(
            input_file=sample_kml_file,
            output_file=output_file,
            elevation_units='meters',
            contour_interval=1.0,
            add_labels=True
        )
        
        # Verify the mock was called with correct parameters
        mock_process.assert_called_once()


def test_generate_contours_progress_callback():
    """Test that progress callback is called during processing."""
    from topoconvert.core.contours import generate_contours
    
    progress_mock = Mock()
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('topoconvert.core.contours._process_contours') as mock_process:
            mock_process.return_value = None
            
            generate_contours(
                input_file=Path("test.kml"),
                output_file=Path("output.dxf"),
                progress_callback=progress_mock
            )
            
            # Verify progress callback was used
            assert mock_process.call_args[1]['progress_callback'] == progress_mock


def test_generate_contours_error_handling():
    """Test error handling during contour generation."""
    from topoconvert.core.contours import generate_contours
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('topoconvert.core.contours._process_contours') as mock_process:
            # Simulate processing error
            mock_process.side_effect = Exception("Processing failed")
            
            with pytest.raises(ProcessingError, match="Processing failed"):
                generate_contours(
                    input_file=Path("test.kml"),
                    output_file=Path("output.dxf")
                )