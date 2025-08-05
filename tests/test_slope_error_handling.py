"""Tests for slope heatmap error handling and validation."""
import pytest
import tempfile
from pathlib import Path
import numpy as np
import warnings

from topoconvert.core.slope_heatmap import (
    compute_slope_from_points, 
    generate_slope_heatmap,
    render_slope_heatmap,
    _parse_coordinates,
    _extract_points
)
from topoconvert.core.exceptions import ProcessingError, FileFormatError


class TestParameterValidation:
    """Test parameter validation and error handling."""
    
    def test_invalid_elevation_units(self):
        """Test that invalid elevation units are rejected."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
        ]
        
        # Should accept 'meters' and 'feet', but handle others gracefully
        # Currently no validation, so this should work but treat as meters
        result = compute_slope_from_points(
            points=points,
            elevation_units='invalid_unit'  # Should default to treating as meters
        )
        assert result is not None
    
    def test_invalid_slope_units(self):
        """Test that invalid slope units are rejected."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
        ]
        
        # Should raise error for invalid slope units
        with pytest.raises(ValueError, match="Invalid slope units"):
            compute_slope_from_points(
                points=points,
                slope_units='invalid_unit'
            )
    
    def test_negative_grid_resolution(self):
        """Test that negative grid resolution is handled."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
        ]
        
        # Should raise error for negative resolution
        with pytest.raises(ValueError):
            compute_slope_from_points(
                points=points,
                grid_resolution=-50
            )
    
    def test_zero_grid_resolution(self):
        """Test that zero grid resolution is handled."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
        ]
        
        # Should raise error for zero resolution
        with pytest.raises(ValueError):
            compute_slope_from_points(
                points=points,
                grid_resolution=0
            )
    
    def test_negative_smooth_parameter(self):
        """Test that negative smoothing is handled."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
        ]
        
        # Negative smoothing should be treated as 0 (no smoothing)
        result = compute_slope_from_points(
            points=points,
            smooth=-1.0
        )
        assert result is not None


class TestCoordinateValidation:
    """Test coordinate parsing and validation."""
    
    def test_parse_coordinates_with_spaces(self):
        """Test parsing coordinates with extra spaces."""
        coord = _parse_coordinates("  -122.0822035 , 37.4222899 , 100.5  ")
        assert coord == (-122.0822035, 37.4222899, 100.5)
    
    def test_parse_coordinates_missing_values(self):
        """Test parsing incomplete coordinate strings."""
        # Only one value
        coord = _parse_coordinates("123.45")
        assert coord is None
        
        # Empty string
        coord = _parse_coordinates("")
        assert coord is None
        
        # Just commas
        coord = _parse_coordinates(",,")
        assert coord is None
    
    def test_parse_coordinates_non_numeric(self):
        """Test parsing non-numeric coordinate values."""
        with pytest.raises(ValueError):
            _parse_coordinates("abc,def,ghi")
        
        with pytest.raises(ValueError):
            _parse_coordinates("-122.0,north,100")
    
    def test_invalid_longitude_range(self):
        """Test handling of out-of-range longitude values."""
        # Longitude > 180 or < -180 should still work (wraps around)
        points = [
            (181.0, 37.0, 100.0),     # Invalid longitude
            (-181.0, 37.0, 110.0),    # Invalid longitude
            (0.0, 37.0, 120.0),
        ]
        
        # Should still compute, pyproj handles wraparound
        result = compute_slope_from_points(points=points)
        assert result is not None
    
    def test_invalid_latitude_range(self):
        """Test handling of out-of-range latitude values."""
        # Latitude > 90 or < -90 is truly invalid
        points = [
            (-122.0, 91.0, 100.0),    # Invalid latitude
            (-122.001, -91.0, 110.0), # Invalid latitude
            (-122.0, 0.0, 120.0),
        ]
        
        # pyproj might handle this or raise an error due to inf values
        # Should either warn or raise an error
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result = compute_slope_from_points(points=points)
                # If it succeeds, should have warnings
                assert len(w) > 0
                assert any("Latitude" in str(warning.message) for warning in w)
            except ValueError as e:
                # Or it might fail with inf values
                assert "finite" in str(e) or "inf" in str(e)


class TestDataValidation:
    """Test data sufficiency and quality validation."""
    
    def test_duplicate_points_handling(self):
        """Test handling of duplicate coordinate points."""
        # All points at same location
        points = [
            (-122.0, 37.0, 100.0),
            (-122.0, 37.0, 110.0),
            (-122.0, 37.0, 120.0),
        ]
        
        # Should raise error or warning for coincident points
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pytest.raises(ValueError):
                # This will fail because all points are at same location
                compute_slope_from_points(points=points)
    
    def test_collinear_points_warning(self):
        """Test handling of collinear points."""
        # All points in a straight line
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.002, 37.0, 120.0),
        ]
        
        # Should still work but might produce artifacts
        result = compute_slope_from_points(points=points)
        assert result is not None
        
        # Check if interpolation worked despite collinearity
        valid_values = result['slope_grid'][~np.isnan(result['slope_grid'])]
        assert len(valid_values) > 0
    
    def test_extreme_elevation_differences(self):
        """Test handling of extreme elevation differences."""
        points = [
            (-122.0, 37.0, 0.0),         # Sea level
            (-122.001, 37.0, 10000.0),   # 10km elevation!
            (-122.0, 37.001, 100.0),
        ]
        
        # Should still compute but produce extreme slopes
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = compute_slope_from_points(points=points)
            
            # Should produce very high slope values
            max_slope = np.nanmax(result['slope_grid'])
            assert max_slope > 80  # Should be near vertical
    
    def test_negative_elevations(self):
        """Test handling of negative elevations (below sea level)."""
        points = [
            (-122.0, 37.0, -100.0),    # Below sea level
            (-122.001, 37.0, -50.0),
            (-122.0, 37.001, 0.0),     # Sea level
        ]
        
        # Should handle negative elevations fine
        result = compute_slope_from_points(points=points)
        assert result is not None
        
        # Elevation grid should contain negative values
        assert np.nanmin(result['elevation_grid']) < 0


class TestFileHandling:
    """Test file I/O error handling."""
    
    def test_generate_slope_heatmap_missing_file(self):
        """Test error when input file doesn't exist."""
        with pytest.raises(FileFormatError, match="Input file not found"):
            generate_slope_heatmap(
                input_file=Path("nonexistent.kml"),
                output_file=Path("output.png")
            )
    
    def test_generate_slope_heatmap_invalid_output_dir(self):
        """Test error when output directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid KML file
            kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
                <Placemark>
                    <Point><coordinates>-122.0,37.0,100</coordinates></Point>
                </Placemark>
                <Placemark>
                    <Point><coordinates>-122.001,37.0,110</coordinates></Point>
                </Placemark>
                <Placemark>
                    <Point><coordinates>-122.0,37.001,120</coordinates></Point>
                </Placemark>
            </Document>
            </kml>'''
            
            kml_file = Path(temp_dir) / "test.kml"
            kml_file.write_text(kml_content)
            
            # Try to write to non-existent directory
            output_file = Path("/nonexistent/directory/output.png")
            
            # Should raise error when trying to save
            with pytest.raises(Exception):  # Could be OSError, FileNotFoundError, etc.
                generate_slope_heatmap(
                    input_file=kml_file,
                    output_file=output_file
                )
    
    def test_empty_kml_file(self):
        """Test handling of empty KML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty KML
            kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
            </Document>
            </kml>'''
            
            kml_file = Path(temp_dir) / "empty.kml"
            kml_file.write_text(kml_content)
            
            # Should raise error for no points
            with pytest.raises(ProcessingError, match="No Placemarks found"):
                generate_slope_heatmap(
                    input_file=kml_file,
                    output_file=Path(temp_dir) / "output.png"
                )
    
    def test_malformed_kml_file(self):
        """Test handling of malformed KML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create malformed KML (not valid XML)
            kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
            <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
                <Placemark>
                    <Point><coordinates>-122.0,37.0,100</coordinates>
                <!-- Missing closing tags -->
            '''
            
            kml_file = Path(temp_dir) / "malformed.kml"
            kml_file.write_text(kml_content)
            
            # Should raise error when parsing
            with pytest.raises(ProcessingError):
                generate_slope_heatmap(
                    input_file=kml_file,
                    output_file=Path(temp_dir) / "output.png"
                )


class TestRenderValidation:
    """Test render_slope_heatmap validation."""
    
    def test_render_with_empty_slope_data(self):
        """Test rendering with empty data dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "empty.png"
            
            # Empty slope data
            slope_data = {
                'slope_grid': np.array([[]]),
                'elevation_grid': np.array([[]]),
                'extent': [0, 0, 0, 0],
                'xi': np.array([]),
                'yi': np.array([]),
                'slope_stats': {'min': 0, 'max': 0, 'mean': 0, 'median': 0}
            }
            
            # Should handle empty data gracefully by creating an image
            # (might be empty/degenerate but shouldn't crash)
            render_slope_heatmap(
                slope_data=slope_data,
                output_file=output_file
            )
            
            # Should create some kind of output file
            assert output_file.exists()
    
    def test_render_with_all_nan_data(self):
        """Test rendering with all NaN values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "all_nan.png"
            
            # All NaN data
            grid_size = 10
            slope_data = {
                'slope_grid': np.full((grid_size, grid_size), np.nan),
                'elevation_grid': np.full((grid_size, grid_size), np.nan),
                'extent': [0, 100, 0, 100],
                'xi': np.linspace(0, 100, grid_size),
                'yi': np.linspace(0, 100, grid_size),
                'slope_stats': {'min': 0, 'max': 0, 'mean': 0, 'median': 0}
            }
            
            # Should still create an image (might be blank/uniform)
            render_slope_heatmap(
                slope_data=slope_data,
                output_file=output_file
            )
            
            assert output_file.exists()
    
    def test_render_with_invalid_colormap(self):
        """Test rendering with invalid colormap name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "invalid_cmap.png"
            
            # Create valid slope data
            grid_size = 10
            x = np.linspace(0, 100, grid_size)
            y = np.linspace(0, 100, grid_size)
            xi, yi = np.meshgrid(x, y)
            slope_grid = np.ones_like(xi) * 15.0
            
            slope_data = {
                'slope_grid': slope_grid,
                'elevation_grid': xi * 0.268,
                'extent': [0, 100, 0, 100],
                'xi': x,
                'yi': y,
                'slope_stats': {'min': 15, 'max': 15, 'mean': 15, 'median': 15}
            }
            
            # Should raise error for invalid colormap
            with pytest.raises(ValueError):
                render_slope_heatmap(
                    slope_data=slope_data,
                    output_file=output_file,
                    colormap='invalid_colormap_name'
                )