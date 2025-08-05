"""Tests for contours generation module."""
import pytest
import tempfile
from pathlib import Path
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
    with pytest.raises(FileNotFoundError, match="File not found"):
        generate_contours(
            input_file=Path("nonexistent.kml"),
            output_file=Path("output.dxf")
        )


def test_generate_contours_validates_parameters(grid_kml):
    """Test parameter validation."""
    from topoconvert.core.contours import generate_contours
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "output.dxf"
        
        # Test invalid elevation units
        with pytest.raises(ValueError, match="elevation_units"):
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                elevation_units="invalid"
            )
        
        # Test invalid contour interval
        with pytest.raises(ValueError, match="contour_interval"):
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                contour_interval=-1.0
            )
        
        # Test invalid grid resolution
        with pytest.raises(ValueError, match="grid_resolution"):
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                grid_resolution=0
            )


def test_generate_contours_with_sample_data(grid_kml, temp_dir):
    """Test contour generation with sample KML data."""
    from topoconvert.core.contours import generate_contours
    
    output_file = temp_dir / "contours.dxf"
    
    # Actually generate contours
    generate_contours(
        input_file=grid_kml,
        output_file=output_file,
        elevation_units='meters',
        contour_interval=1.0,
        add_labels=True
    )
    
    # Verify output file was created
    assert output_file.exists()
    
    # Verify it's a valid DXF
    with open(output_file, 'r') as f:
        content = f.read()
        assert '0\nSECTION' in content  # Basic DXF structure
        assert 'ENTITIES' in content




def test_generate_contours_error_handling(empty_kml):
    """Test error handling during contour generation."""
    from topoconvert.core.contours import generate_contours
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "output.dxf"
        
        # Empty KML should raise ProcessingError
        with pytest.raises(ProcessingError, match="No points found"):
            generate_contours(
                input_file=empty_kml,
                output_file=output_file
            )


def test_generate_contours_output_formats(grid_kml):
    """Test different output options."""
    from topoconvert.core.contours import generate_contours
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with different options
        test_cases = [
            {
                'name': 'no_labels',
                'options': {'add_labels': False},
                'output': 'contours_no_labels.dxf'
            },
            {
                'name': 'custom_interval',
                'options': {'contour_interval': 5.0},
                'output': 'contours_5ft.dxf'
            },
            {
                'name': 'high_resolution',
                'options': {'grid_resolution': 150},
                'output': 'contours_high_res.dxf'
            },
            {
                'name': 'feet_units',
                'options': {'elevation_units': 'feet'},
                'output': 'contours_feet.dxf'
            }
        ]
        
        for test_case in test_cases:
            output_file = Path(temp_dir) / test_case['output']
            
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                **test_case['options']
            )
            
            assert output_file.exists(), f"Failed to create {test_case['name']}"


def test_generate_contours_coordinate_systems(grid_kml):
    """Test coordinate system handling."""
    from topoconvert.core.contours import generate_contours
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with translation disabled
        output_no_translate = Path(temp_dir) / "no_translate.dxf"
        generate_contours(
            input_file=grid_kml,
            output_file=output_no_translate,
            translate_to_origin=False
        )
        assert output_no_translate.exists()
        
        # Test with specific projection
        output_utm = Path(temp_dir) / "utm_projected.dxf"
        generate_contours(
            input_file=grid_kml,
            output_file=output_utm,
            target_epsg=32614  # UTM Zone 14N
        )
        assert output_utm.exists()


def test_generate_contours_sparse_data_handling(sparse_kml):
    """Test handling of sparse data."""
    from topoconvert.core.contours import generate_contours
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "sparse_contours.dxf"
        
        # Should either succeed with limited contours or fail gracefully
        try:
            generate_contours(
                input_file=sparse_kml,
                output_file=output_file,
                grid_resolution=30  # Lower resolution for sparse data
            )
            # If it succeeds, verify output
            assert output_file.exists()
        except ProcessingError as e:
            # Acceptable if it fails due to insufficient data
            assert "insufficient" in str(e).lower() or "not enough" in str(e).lower()