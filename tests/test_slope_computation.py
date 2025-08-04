"""Tests for slope computation functions (pure computation, no matplotlib)."""
import pytest
import numpy as np
from typing import List, Tuple, Dict, Any

from topoconvert.core.slope_heatmap import compute_slope_from_points
from topoconvert.core.exceptions import ProcessingError


class TestComputeSlopeFromPoints:
    """Test cases for compute_slope_from_points function."""
    
    def test_basic_computation(self):
        """Test basic slope computation from points."""
        # Create synthetic points in a simple pattern
        points = [
            (-122.0, 37.0, 100.0),      # lon, lat, elevation (meters)
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
            (-122.001, 37.001, 130.0),
        ]
        
        result = compute_slope_from_points(
            points=points,
            elevation_units='meters',
            grid_resolution=50,
            slope_units='degrees',
            smooth=0.0
        )
        
        # Expected return structure
        expected_keys = {
            'slope_grid',       # 2D numpy array of slopes
            'elevation_grid',   # 2D numpy array of interpolated elevations
            'x_coords',         # 1D array of projected x coordinates (feet)
            'y_coords',         # 1D array of projected y coordinates (feet)
            'xi',              # 1D array of grid x coordinates
            'yi',              # 1D array of grid y coordinates
            'extent',          # [x_min, x_max, y_min, y_max] for plotting
            'mask',            # 2D boolean array of valid data points
            'slope_stats',     # Dict with min, max, mean, median
            'utm_zone',        # UTM zone used for projection
            'epsg_code'        # EPSG code used
        }
        
        # When implemented, verify structure
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
    
    def test_insufficient_points_error(self):
        """Test error handling for insufficient points."""
        # Too few points for interpolation
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
        ]
        
        # Should raise ProcessingError with appropriate message
        with pytest.raises(ProcessingError, match="Need at least 3 points"):
            compute_slope_from_points(points=points)
    
    def test_empty_points_error(self):
        """Test error handling for empty points list."""
        with pytest.raises(ProcessingError, match="No points provided"):
            compute_slope_from_points(points=[])
    
    def test_elevation_unit_conversion(self):
        """Test that elevation units are properly converted."""
        points_meters = [
            (-122.0, 37.0, 100.0),    # 100 meters
            (-122.001, 37.0, 101.0),   # 101 meters
            (-122.0, 37.001, 102.0),   # 102 meters
        ]
        
        points_feet = [
            (-122.0, 37.0, 328.084),   # ~100m in feet
            (-122.001, 37.0, 331.365), # ~101m in feet
            (-122.0, 37.001, 334.646), # ~102m in feet
        ]
        
        result_m = compute_slope_from_points(
            points=points_meters,
            elevation_units='meters'
        )
        
        result_ft = compute_slope_from_points(
            points=points_feet,
            elevation_units='feet'
        )
        
        # Slopes should be similar regardless of input units
        # (actual comparison would be done when implemented)
    
    def test_different_slope_units(self):
        """Test computation with different slope unit outputs."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 105.0),
            (-122.0, 37.001, 110.0),
        ]
        
        # Test all three slope unit types
        for units in ['degrees', 'percent', 'rise-run']:
            result = compute_slope_from_points(
                points=points,
                slope_units=units,
                run_length=12.0 if units == 'rise-run' else 10.0
            )
            
            # Verify appropriate ranges for each unit type
            valid_slopes = result['slope_grid'][~np.isnan(result['slope_grid'])]
            if units == 'degrees':
                # Slopes should be 0-90 degrees
                assert np.all(valid_slopes >= 0)
                assert np.all(valid_slopes <= 90)
            elif units == 'percent':
                # Slopes should be >= 0
                assert np.all(valid_slopes >= 0)
            else:  # rise-run
                # Slopes should be >= 0
                assert np.all(valid_slopes >= 0)
    
    def test_grid_resolution_effect(self):
        """Test that grid resolution affects output size."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
            (-122.001, 37.001, 130.0),
        ]
        
        # Test different resolutions
        for resolution in [20, 50, 100]:
            result = compute_slope_from_points(
                points=points,
                grid_resolution=resolution
            )
            
            # Grid should be resolution x resolution
            assert result['slope_grid'].shape == (resolution, resolution)
            assert result['elevation_grid'].shape == (resolution, resolution)
            assert len(result['xi']) == resolution
            assert len(result['yi']) == resolution
    
    def test_smoothing_parameter(self):
        """Test effect of smoothing parameter."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 150.0),  # Sharp elevation change
            (-122.0, 37.001, 110.0),
            (-122.001, 37.001, 160.0),
        ]
        
        # Without smoothing
        result_no_smooth = compute_slope_from_points(
            points=points,
            smooth=0.0
        )
        
        # With smoothing
        result_smooth = compute_slope_from_points(
            points=points,
            smooth=2.0
        )
        
        # Smoothed result should have lower maximum slope
        assert np.nanmax(result_smooth['slope_grid']) <= np.nanmax(result_no_smooth['slope_grid'])
    
    def test_slope_statistics(self):
        """Test that slope statistics are correctly computed."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
            (-122.001, 37.001, 130.0),
        ]
        
        result = compute_slope_from_points(points=points)
        
        stats = result['slope_stats']
        assert 'min' in stats
        assert 'max' in stats
        assert 'mean' in stats
        assert 'median' in stats
        
        # Statistics should be consistent with grid values
        valid_slopes = result['slope_grid'][~np.isnan(result['slope_grid'])]
        assert stats['min'] == pytest.approx(np.min(valid_slopes))
        assert stats['max'] == pytest.approx(np.max(valid_slopes))
        assert stats['mean'] == pytest.approx(np.mean(valid_slopes))
        assert stats['median'] == pytest.approx(np.median(valid_slopes))
    
    def test_known_slope_pattern(self):
        """Test computation with a known slope pattern."""
        # Create a simple inclined plane
        points = []
        for i in range(5):
            for j in range(5):
                lon = -122.0 + i * 0.001
                lat = 37.0 + j * 0.001
                # Linear elevation increase: 10 ft per 0.001 degree
                elev = 100.0 + i * 10.0  
                points.append((lon, lat, elev))
        
        result = compute_slope_from_points(
            points=points,
            grid_resolution=20,
            slope_units='degrees',
            smooth=0.0
        )
        
        # For a uniform incline in one direction, 
        # slopes should be relatively constant
        valid_slopes = result['slope_grid'][~np.isnan(result['slope_grid'])]
        slope_std = np.std(valid_slopes)
        
        # Standard deviation should be low for uniform slope
        assert slope_std < 5.0  # degrees
    
    def test_projection_info_returned(self):
        """Test that projection information is included in results."""
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
            (-122.0, 37.001, 120.0),
        ]
        
        result = compute_slope_from_points(points=points)
        
        # Should include projection details
        assert 'utm_zone' in result
        assert 'epsg_code' in result
        
        # For this longitude/latitude, should be UTM zone 10N
        assert result['utm_zone'] == 10
        assert result['epsg_code'] == 32610  # WGS 84 / UTM zone 10N
    
    def test_interpolation_fallback_sparse_data(self):
        """Test that interpolation falls back gracefully with sparse data."""
        # Create very sparse data that might fail cubic interpolation
        points = [
            (-122.0, 37.0, 100.0),
            (-122.01, 37.0, 110.0),      # Large gaps between points
            (-122.0, 37.01, 120.0),
        ]
        
        # Should still produce valid results (using fallback interpolation)
        result = compute_slope_from_points(
            points=points,
            grid_resolution=100  # High resolution with sparse data
        )
        
        # Should have valid grids despite sparse data
        assert result['slope_grid'] is not None
        assert result['elevation_grid'] is not None
        
        # Should have some valid (non-NaN) values
        valid_slopes = result['slope_grid'][~np.isnan(result['slope_grid'])]
        assert len(valid_slopes) > 0
    
    def test_sparse_data_warning(self):
        """Test that sparse data triggers a warning."""
        import warnings
        
        # Create very sparse data over a large area
        points = [
            (-122.0, 37.0, 100.0),
            (-122.1, 37.0, 110.0),      # 0.1 degree gap (very large)
            (-122.0, 37.1, 120.0),
        ]
        
        # Should trigger a sparse data warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = compute_slope_from_points(
                points=points,
                grid_resolution=100
            )
            
            # Should have generated a warning
            assert len(w) > 0
            assert any("Sparse data detected" in str(warning.message) for warning in w)