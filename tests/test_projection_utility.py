"""Tests for projection utility functions."""
import pytest
from pyproj import CRS
from topoconvert.utils.projection import (
    get_target_crs, 
    get_transformer, 
    detect_utm_zone,
    transform_coordinates
)


class TestGetTargetCRS:
    """Test get_target_crs function."""
    
    def test_wgs84_flag_returns_4326(self):
        """WGS84 flag should return EPSG:4326."""
        crs = get_target_crs(target_epsg=None, wgs84=True, sample_point=(-97.5, 30.0))
        assert crs.to_epsg() == 4326
    
    def test_explicit_epsg_overrides_auto_detection(self):
        """Explicit EPSG should be used when provided."""
        crs = get_target_crs(target_epsg=26914, wgs84=False, sample_point=(-97.5, 30.0))
        assert crs.to_epsg() == 26914
    
    def test_auto_detects_utm_zone_14n(self):
        """Should auto-detect UTM Zone 14N for Austin, TX coordinates."""
        crs = get_target_crs(target_epsg=None, wgs84=False, sample_point=(-97.5, 30.0))
        # UTM Zone 14N in WGS84
        assert "utm" in crs.to_proj4().lower()
        assert "zone=14" in crs.to_proj4()
        assert "south" not in crs.to_proj4()
    
    def test_auto_detects_utm_zone_32n(self):
        """Should auto-detect UTM Zone 32N for Oslo, Norway coordinates."""
        crs = get_target_crs(target_epsg=None, wgs84=False, sample_point=(10.75, 59.91))
        assert "utm" in crs.to_proj4().lower()
        assert "zone=32" in crs.to_proj4()
        assert "south" not in crs.to_proj4()
    
    def test_auto_detects_southern_hemisphere(self):
        """Should detect southern hemisphere for Sydney, Australia."""
        crs = get_target_crs(target_epsg=None, wgs84=False, sample_point=(151.21, -33.87))
        assert "utm" in crs.to_proj4().lower()
        assert "zone=56" in crs.to_proj4()
        assert "south" in crs.to_proj4()
    
    def test_handles_zone_boundary(self):
        """Should handle coordinates on UTM zone boundaries."""
        # Boundary between zone 30 and 31 (0 degrees longitude)
        crs = get_target_crs(target_epsg=None, wgs84=False, sample_point=(0.0, 51.5))
        assert "utm" in crs.to_proj4().lower()
        assert "zone=31" in crs.to_proj4()


class TestDetectUTMZone:
    """Test detect_utm_zone function."""
    
    def test_zone_calculation_examples(self):
        """Test known UTM zone calculations."""
        # Austin, TX - Zone 14
        zone = detect_utm_zone(-97.5, 30.0)
        assert zone == 14
        
        # London, UK - Zone 30
        zone = detect_utm_zone(-0.12, 51.5)
        assert zone == 30
        
        # Tokyo, Japan - Zone 54
        zone = detect_utm_zone(139.69, 35.68)
        assert zone == 54
        
        # Sydney, Australia - Zone 56
        zone = detect_utm_zone(151.21, -33.87)
        assert zone == 56
    
    def test_edge_cases(self):
        """Test edge cases for zone calculation."""
        # -180 degrees (Date Line) - Zone 1
        zone = detect_utm_zone(-180.0, 0.0)
        assert zone == 1
        
        # 180 degrees (Date Line) - Zone 1 (wraps around)
        zone = detect_utm_zone(180.0, 0.0)
        assert zone == 1
        
        # Prime Meridian - Zone 31
        zone = detect_utm_zone(0.0, 0.0)
        assert zone == 31


class TestGetTransformer:
    """Test get_transformer function."""
    
    def test_creates_transformer_from_epsg_codes(self):
        """Should create transformer from EPSG codes."""
        transformer = get_transformer(4326, CRS.from_epsg(26914))
        assert transformer is not None
        
        # Test a known coordinate transformation
        x, y = transformer.transform(-97.5, 30.0)
        assert 600000 < x < 700000  # Approximate UTM easting
        assert 3300000 < y < 3400000  # Approximate UTM northing
    
    def test_creates_transformer_from_crs_objects(self):
        """Should create transformer from CRS objects."""
        source_crs = CRS.from_epsg(4326)
        target_crs = CRS.from_epsg(26914)
        transformer = get_transformer(source_crs, target_crs)
        assert transformer is not None
    
    def test_always_xy_true(self):
        """Transformer should always use xy order."""
        transformer = get_transformer(4326, CRS.from_epsg(26914))
        # Transform should expect lon, lat order (not lat, lon)
        x, y = transformer.transform(-97.5, 30.0)
        assert x > 0  # Should be valid easting, not latitude


class TestTransformCoordinates:
    """Test transform_coordinates convenience function."""
    
    def test_transforms_multiple_points(self):
        """Should transform a list of coordinates."""
        points = [
            (-97.5, 30.0),
            (-97.6, 30.1),
            (-97.4, 29.9)
        ]
        
        transformed = transform_coordinates(points, 4326, 26914)
        
        assert len(transformed) == 3
        # All points should be in reasonable UTM range
        for x, y in transformed:
            assert 600000 < x < 700000
            assert 3300000 < y < 3400000
    
    def test_handles_empty_list(self):
        """Should handle empty coordinate list."""
        transformed = transform_coordinates([], 4326, 26914)
        assert transformed == []


class TestMutualExclusivity:
    """Test that target_epsg and wgs84 are mutually exclusive."""
    
    def test_raises_error_when_both_specified(self):
        """Should raise error when both target_epsg and wgs84 are specified."""
        with pytest.raises(ValueError, match="mutually exclusive"):
            get_target_crs(target_epsg=26914, wgs84=True, sample_point=(-97.5, 30.0))