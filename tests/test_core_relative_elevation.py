"""Tests for relative elevation processing module."""
import pytest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from topoconvert.core.exceptions import FileFormatError, ProcessingError


def test_relative_elevation_module_exists():
    """Test that relative_elevation module can be imported."""
    try:
        from topoconvert.core import relative_elevation
        assert hasattr(relative_elevation, 'convert_to_relative_elevation')
    except ImportError as e:
        pytest.fail(f"Failed to import relative_elevation module: {e}")


def test_extract_elevation_points_basic():
    """Test basic elevation point extraction from KML."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    # Use existing fixture
    kml_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
    
    points = _extract_elevation_points(kml_file)
    
    assert len(points) == 3
    assert all(len(point) == 3 for point in points)  # lon, lat, elev
    
    # Check specific values from fixture
    expected_elevations = [100.0, 110.0, 120.0]
    actual_elevations = [point[2] for point in points]
    assert sorted(actual_elevations) == sorted(expected_elevations)


def test_extract_elevation_points_no_elevation():
    """Test extraction from KML without elevation data."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    kml_file = Path(__file__).parent / "fixtures" / "no_elevation.kml"
    
    with pytest.raises(ProcessingError, match="No points found"):
        _extract_elevation_points(kml_file)


def test_extract_elevation_points_empty_kml():
    """Test extraction from empty KML."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    kml_file = Path(__file__).parent / "fixtures" / "empty.kml"
    
    with pytest.raises(ProcessingError, match="No points found"):
        _extract_elevation_points(kml_file)


def test_extract_elevation_points_invalid_coords():
    """Test extraction with invalid coordinate data."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    kml_file = Path(__file__).parent / "fixtures" / "invalid_coords.kml"
    
    # Should handle invalid coordinates gracefully by skipping them
    points = _extract_elevation_points(kml_file)
    # Should still extract some valid points if any exist
    assert isinstance(points, list)


def test_extract_elevation_points_large_file():
    """Test extraction from larger KML file."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    kml_file = Path(__file__).parent / "fixtures" / "grid_4x4.kml"
    
    points = _extract_elevation_points(kml_file)
    
    assert len(points) >= 16  # 4x4 grid should have at least 16 points
    assert all(len(point) == 3 for point in points)
    assert all(isinstance(point[2], (int, float)) for point in points)


def test_extract_elevation_points_with_namespace_variations():
    """Test extraction with different KML namespace variations."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    # Create temporary KML with Google Earth namespace
    kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>Namespace Test</name>
    <Placemark>
      <name>Test Point</name>
      <Point>
        <coordinates>-122.0,37.0,50.5</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        kml_file = Path(temp_dir) / "namespace_test.kml"
        kml_file.write_text(kml_content)
        
        points = _extract_elevation_points(kml_file)
        
        assert len(points) == 1
        assert points[0][2] == 50.5


def test_extract_elevation_points_mixed_elevations():
    """Test extraction with mixed positive/negative elevations."""
    from topoconvert.core.relative_elevation import _extract_elevation_points
    
    # Create temporary KML with mixed elevations
    kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Mixed Elevations</name>
    <Placemark>
      <name>High Point</name>
      <Point>
        <coordinates>-122.0,37.0,150.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Low Point</name>
      <Point>
        <coordinates>-122.001,37.0,-25.5</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Sea Level</name>
      <Point>
        <coordinates>-122.002,37.0,0.0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        kml_file = Path(temp_dir) / "mixed_elevations.kml"
        kml_file.write_text(kml_content)
        
        points = _extract_elevation_points(kml_file)
        
        assert len(points) == 3
        elevations = [point[2] for point in points]
        assert 150.0 in elevations
        assert -25.5 in elevations
        assert 0.0 in elevations


class TestUnitConversion:
    """Tests for elevation unit conversion functions."""
    
    def test_meters_to_feet_conversion(self):
        """Test meters to feet conversion."""
        from topoconvert.core.relative_elevation import _convert_elevation_units
        
        # Test basic conversion
        result = _convert_elevation_units(100.0, "meters", "feet")
        expected = 100.0 * 3.28084  # ~328.084 feet
        assert abs(result - expected) < 0.001
        
        # Test zero
        result = _convert_elevation_units(0.0, "meters", "feet")
        assert result == 0.0
        
        # Test negative
        result = _convert_elevation_units(-50.0, "meters", "feet")
        expected = -50.0 * 3.28084
        assert abs(result - expected) < 0.001
    
    def test_feet_to_meters_conversion(self):
        """Test feet to meters conversion."""
        from topoconvert.core.relative_elevation import _convert_elevation_units
        
        # Test basic conversion
        result = _convert_elevation_units(328.084, "feet", "meters")
        expected = 328.084 * 0.3048  # ~100 meters
        assert abs(result - expected) < 0.001
        
        # Test zero
        result = _convert_elevation_units(0.0, "feet", "meters")
        assert result == 0.0
    
    def test_same_unit_conversion(self):
        """Test conversion with same input/output units."""
        from topoconvert.core.relative_elevation import _convert_elevation_units
        
        # Test meters to meters
        result = _convert_elevation_units(100.0, "meters", "meters")
        assert result == 100.0
        
        # Test feet to feet
        result = _convert_elevation_units(328.0, "feet", "feet")
        assert result == 328.0
    
    def test_invalid_unit_conversion(self):
        """Test conversion with invalid units."""
        from topoconvert.core.relative_elevation import _convert_elevation_units
        
        with pytest.raises(ValueError, match="Unsupported unit"):
            _convert_elevation_units(100.0, "kilometers", "feet")
        
        with pytest.raises(ValueError, match="Unsupported unit"):
            _convert_elevation_units(100.0, "meters", "yards")
    
    def test_conversion_precision(self):
        """Test conversion maintains adequate precision."""
        from topoconvert.core.relative_elevation import _convert_elevation_units
        
        # Test round-trip conversion
        original = 123.456
        feet = _convert_elevation_units(original, "meters", "feet")
        back_to_meters = _convert_elevation_units(feet, "feet", "meters")
        
        # Should be within 0.001 meters due to rounding
        assert abs(back_to_meters - original) < 0.001


class TestReferenceCalculation:
    """Tests for reference value calculation methods."""
    
    def test_calculate_reference_min(self):
        """Test minimum reference calculation."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [100.0, 110.0, 90.0, 120.0, 105.0]
        reference = _calculate_reference_value(elevations, "min")
        assert reference == 90.0
    
    def test_calculate_reference_max(self):
        """Test maximum reference calculation."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [100.0, 110.0, 90.0, 120.0, 105.0]
        reference = _calculate_reference_value(elevations, "max")
        assert reference == 120.0
    
    def test_calculate_reference_mean(self):
        """Test mean reference calculation."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [100.0, 110.0, 90.0, 120.0, 105.0]
        reference = _calculate_reference_value(elevations, "mean")
        expected = sum(elevations) / len(elevations)  # 105.0
        assert abs(reference - expected) < 0.001
    
    def test_calculate_reference_single_value(self):
        """Test reference calculation with single elevation."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [100.0]
        
        assert _calculate_reference_value(elevations, "min") == 100.0
        assert _calculate_reference_value(elevations, "max") == 100.0
        assert _calculate_reference_value(elevations, "mean") == 100.0
    
    def test_calculate_reference_identical_values(self):
        """Test reference calculation with identical elevations."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [100.0, 100.0, 100.0]
        
        assert _calculate_reference_value(elevations, "min") == 100.0
        assert _calculate_reference_value(elevations, "max") == 100.0
        assert _calculate_reference_value(elevations, "mean") == 100.0
    
    def test_calculate_reference_invalid_method(self):
        """Test reference calculation with invalid method."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [100.0, 110.0, 120.0]
        
        with pytest.raises(ValueError, match="Unsupported reference method"):
            _calculate_reference_value(elevations, "invalid")
    
    def test_calculate_reference_empty_list(self):
        """Test reference calculation with empty elevation list."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = []
        
        with pytest.raises(ValueError, match="No elevation values provided"):
            _calculate_reference_value(elevations, "min")
    
    def test_calculate_reference_negative_values(self):
        """Test reference calculation with negative elevations."""
        from topoconvert.core.relative_elevation import _calculate_reference_value
        
        elevations = [-50.0, -25.0, 0.0, 25.0, 50.0]
        
        assert _calculate_reference_value(elevations, "min") == -50.0
        assert _calculate_reference_value(elevations, "max") == 50.0
        assert _calculate_reference_value(elevations, "mean") == 0.0


class TestRelativeTransformation:
    """Tests for relative elevation transformation."""
    
    def test_apply_relative_transform_min_reference(self):
        """Test relative transformation with min reference."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [100.0, 110.0, 90.0, 120.0]
        reference = 90.0  # minimum
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        expected = [10.0, 20.0, 0.0, 30.0]  # subtract 90 from each
        assert all(abs(a - b) < 0.001 for a, b in zip(relative_elevs, expected))
    
    def test_apply_relative_transform_max_reference(self):
        """Test relative transformation with max reference."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [100.0, 110.0, 90.0, 120.0]
        reference = 120.0  # maximum
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        expected = [-20.0, -10.0, -30.0, 0.0]  # subtract 120 from each
        assert all(abs(a - b) < 0.001 for a, b in zip(relative_elevs, expected))
    
    def test_apply_relative_transform_mean_reference(self):
        """Test relative transformation with mean reference."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [100.0, 110.0, 90.0, 120.0]
        reference = 105.0  # mean
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        expected = [-5.0, 5.0, -15.0, 15.0]  # subtract 105 from each
        assert all(abs(a - b) < 0.001 for a, b in zip(relative_elevs, expected))
    
    def test_apply_relative_transform_zero_reference(self):
        """Test relative transformation with zero reference."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [100.0, -50.0, 0.0, 75.0]
        reference = 0.0
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        # Should be identical to original since reference is 0
        assert all(abs(a - b) < 0.001 for a, b in zip(relative_elevs, elevations))
    
    def test_apply_relative_transform_negative_reference(self):
        """Test relative transformation with negative reference."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [-10.0, 0.0, 10.0, 20.0]
        reference = -10.0
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        expected = [0.0, 10.0, 20.0, 30.0]  # subtract -10 (add 10) from each
        assert all(abs(a - b) < 0.001 for a, b in zip(relative_elevs, expected))
    
    def test_apply_relative_transform_empty_list(self):
        """Test relative transformation with empty elevation list."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = []
        reference = 100.0
        
        result = _apply_relative_transform(elevations, reference)
        assert result == []
    
    def test_apply_relative_transform_single_value(self):
        """Test relative transformation with single elevation."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [150.0]
        reference = 150.0
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        assert len(relative_elevs) == 1
        assert abs(relative_elevs[0] - 0.0) < 0.001
    
    def test_apply_relative_transform_precision(self):
        """Test relative transformation maintains precision."""
        from topoconvert.core.relative_elevation import _apply_relative_transform
        
        elevations = [123.456, 234.567, 345.678]
        reference = 123.456
        
        relative_elevs = _apply_relative_transform(elevations, reference)
        
        expected = [0.0, 111.111, 222.222]  # High precision differences
        assert all(abs(a - b) < 0.001 for a, b in zip(relative_elevs, expected))


class TestKMLProcessingIntegration:
    """Integration tests for full KML processing workflow."""
    
    def test_convert_to_relative_elevation_basic(self, temp_dir):
        """Test full conversion workflow with basic parameters."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Use existing fixture
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "output_relative.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="min",
            label_format="{value:.1f} ft",
            apply_style=True
        )
        
        # Verify result structure
        assert result.success == True
        assert result.point_count == 3
        assert result.input_elevation_units == "meters"
        assert result.output_elevation_units == "feet"
        assert result.reference_method == "min"
        assert result.style_applied == True
        
        # Verify output file was created
        assert output_file.exists()
        
        # Parse and verify KML structure
        tree = ET.parse(output_file)
        root = tree.getroot()
        
        # Check namespace
        assert 'kml' in root.tag
        
        # Check for style element
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        styles = root.findall('.//kml:Style[@id="elevLabels"]', ns)
        assert len(styles) == 1
        
        # Check placemarks have updated labels
        placemarks = root.findall('.//kml:Placemark', ns)
        assert len(placemarks) == 3
        
        for placemark in placemarks:
            name_elem = placemark.find('kml:name', ns)
            assert name_elem is not None
            assert 'ft' in name_elem.text  # Should contain unit
            
            # Should have style reference
            style_url = placemark.find('kml:styleUrl', ns)
            assert style_url is not None
            assert style_url.text == '#elevLabels'
    
    def test_convert_to_relative_elevation_different_units(self, temp_dir):
        """Test conversion with different unit combinations."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "output_meters.kml"
        
        # Convert meters to meters (no unit conversion)
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="meters",
            reference_method="max",
            label_format="{value:.2f}m",
            apply_style=False
        )
        
        assert result.success == True
        assert result.output_elevation_units == "meters"
        assert result.reference_method == "max"
        assert result.style_applied == False
        
        # Check that style was not applied
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        styles = root.findall('.//kml:Style[@id="elevLabels"]', ns)
        assert len(styles) == 0  # No style should be added
        
        # Check labels don't have style reference
        placemarks = root.findall('.//kml:Placemark', ns)
        for placemark in placemarks:
            style_url = placemark.find('kml:styleUrl', ns)
            assert style_url is None or style_url.text != '#elevLabels'
    
    def test_convert_to_relative_elevation_mean_reference(self, temp_dir):
        """Test conversion with mean reference method."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "output_mean.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="mean",
            label_format="Elev: {value:.1f} {unit}",
            apply_style=True
        )
        
        assert result.success == True
        assert result.reference_method == "mean"
        
        # With elevations 100, 110, 120 meters (mean = 110)
        # In feet: ~328.084, ~360.892, ~393.701 (mean = ~360.892)
        # Relative to mean: ~-32.808, ~0.0, ~32.808
        expected_reference = 110.0 * 3.28084  # 110 meters in feet
        assert abs(result.reference_value - expected_reference) < 0.1
        
        # Verify relative range
        expected_min_rel = (100.0 - 110.0) * 3.28084  # -10 meters in feet
        expected_max_rel = (120.0 - 110.0) * 3.28084  # +10 meters in feet
        assert abs(result.relative_range[0] - expected_min_rel) < 0.1
        assert abs(result.relative_range[1] - expected_max_rel) < 0.1
    
    def test_convert_to_relative_elevation_custom_label_format(self, temp_dir):
        """Test conversion with custom label format."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "output_custom.kml"
        
        custom_format = "Height: {value:.2f} {unit} above base"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="min",
            label_format=custom_format,
            apply_style=True
        )
        
        assert result.success == True
        assert result.label_format == custom_format
        
        # Verify custom format was applied
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        names = [elem.text for elem in root.findall('.//kml:name', ns) 
                if elem.text and 'Height:' in elem.text]
        assert len(names) >= 3  # At least 3 placemarks with custom format
        
        for name in names:
            assert 'Height:' in name
            assert 'ft above base' in name
    
    def test_convert_to_relative_elevation_parameter_validation(self, temp_dir):
        """Test parameter validation."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "output.kml"
        
        # Test invalid elevation units
        with pytest.raises(ValueError, match="elevation_units"):
            convert_to_relative_elevation(
                input_file, output_file, elevation_units="invalid"
            )
        
        # Test invalid output units
        with pytest.raises(ValueError, match="output_units"):
            convert_to_relative_elevation(
                input_file, output_file, output_units="invalid"
            )
        
        # Test invalid reference method
        with pytest.raises(ValueError, match="reference_method"):
            convert_to_relative_elevation(
                input_file, output_file, reference_method="invalid"
            )
        
        # Test invalid apply_style
        with pytest.raises(ValueError, match="apply_style"):
            convert_to_relative_elevation(
                input_file, output_file, apply_style="invalid"
            )
    
    def test_convert_to_relative_elevation_file_validation(self, temp_dir):
        """Test file validation."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        output_file = temp_dir / "output.kml"
        
        # Test non-existent input file
        with pytest.raises(FileNotFoundError):
            convert_to_relative_elevation(
                input_file=Path("nonexistent.kml"),
                output_file=output_file
            )
    
    def test_kml_style_application(self, temp_dir):
        """Test KML style application details."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "styled_output.kml"
        
        convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            apply_style=True
        )
        
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Check style definition
        style = root.find('.//kml:Style[@id="elevLabels"]', ns)
        assert style is not None
        
        # Check IconStyle scale
        icon_style = style.find('kml:IconStyle', ns)
        assert icon_style is not None
        icon_scale = icon_style.find('kml:scale', ns)
        assert icon_scale is not None
        assert float(icon_scale.text) == 0.5
        
        # Check LabelStyle scale
        label_style = style.find('kml:LabelStyle', ns)
        assert label_style is not None
        label_scale = label_style.find('kml:scale', ns)
        assert label_scale is not None
        assert float(label_scale.text) == 0.8


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_single_point_kml(self, temp_dir):
        """Test processing KML with only one elevation point."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with single point
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Single Point</name>
    <Placemark>
      <name>Only Point</name>
      <Point>
        <coordinates>-122.0,37.0,100.5</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "single_point.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "single_output.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="min"
        )
        
        assert result.success == True
        assert result.point_count == 1
        
        # With single point, relative elevation should be 0.0 for any reference method
        assert result.relative_range == (0.0, 0.0)
        
        # Verify output file
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        names = root.findall('.//kml:name', ns)
        point_names = [n.text for n in names if n.text and '0.0' in n.text]
        assert len(point_names) >= 1  # Should have at least one point with 0.0 relative elevation
    
    def test_identical_elevations(self, temp_dir):
        """Test processing KML with identical elevation values."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with identical elevations
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Identical Elevations</name>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0,37.0,150.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 2</name>
      <Point>
        <coordinates>-122.001,37.0,150.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 3</name>
      <Point>
        <coordinates>-122.002,37.0,150.0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "identical_elevs.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "identical_output.kml"
        
        # Test all reference methods with identical elevations
        for method in ['min', 'max', 'mean']:
            result = convert_to_relative_elevation(
                input_file=input_file,
                output_file=temp_dir / f"identical_output_{method}.kml",
                reference_method=method
            )
            
            assert result.success == True
            assert result.point_count == 3
            
            # All relative elevations should be 0.0
            assert result.relative_range == (0.0, 0.0)
            
            # Original range should be the same value
            orig_elev_ft = 150.0 * 3.28084  # 150m in feet
            assert abs(result.elevation_range[0] - orig_elev_ft) < 0.1
            assert abs(result.elevation_range[1] - orig_elev_ft) < 0.1
    
    def test_negative_elevations(self, temp_dir):
        """Test processing KML with negative elevation values."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with negative elevations (below sea level)
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Below Sea Level</name>
    <Placemark>
      <name>Deep Point</name>
      <Point>
        <coordinates>-122.0,37.0,-50.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Surface Point</name>
      <Point>
        <coordinates>-122.001,37.0,0.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>High Point</name>
      <Point>
        <coordinates>-122.002,37.0,25.0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "negative_elevs.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "negative_output.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="meters",
            reference_method="min"
        )
        
        assert result.success == True
        assert result.point_count == 3
        
        # Min reference should be -50m, so relative range: 0 to 75m
        assert abs(result.reference_value - (-50.0)) < 0.1
        assert abs(result.relative_range[0] - 0.0) < 0.1
        assert abs(result.relative_range[1] - 75.0) < 0.1
    
    def test_very_small_elevation_differences(self, temp_dir):
        """Test processing KML with very small elevation differences."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with sub-meter differences
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Small Differences</name>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0,37.0,100.001</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 2</name>
      <Point>
        <coordinates>-122.001,37.0,100.005</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 3</name>
      <Point>
        <coordinates>-122.002,37.0,100.010</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "small_diffs.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "small_diffs_output.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="meters",
            reference_method="min",
            label_format="{value:.3f} m"  # Higher precision
        )
        
        assert result.success == True
        assert result.point_count == 3
        
        # Should handle small differences correctly
        assert abs(result.relative_range[0] - 0.0) < 0.001
        assert abs(result.relative_range[1] - 0.009) < 0.001  # 100.010 - 100.001
    
    def test_very_large_elevation_range(self, temp_dir):
        """Test processing KML with very large elevation range."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with extreme elevation range
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Extreme Range</name>
    <Placemark>
      <name>Valley</name>
      <Point>
        <coordinates>-122.0,37.0,-200.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Mountain</name>
      <Point>
        <coordinates>-122.001,37.0,8848.0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "extreme_range.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "extreme_output.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="min"
        )
        
        assert result.success == True
        assert result.point_count == 2
        
        # Should handle extreme ranges (Everest height: 8848m, Death Valley: -200m)
        expected_range_m = 8848.0 - (-200.0)  # 9048m difference
        expected_range_ft = expected_range_m * 3.28084
        
        assert abs(result.relative_range[1] - expected_range_ft) < 10.0  # Allow some tolerance
    
    def test_mixed_coordinate_formats(self, temp_dir):
        """Test processing KML with mixed coordinate formats."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with different coordinate precisions
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Mixed Formats</name>
    <Placemark>
      <name>High Precision</name>
      <Point>
        <coordinates>-122.123456789,37.987654321,100.123456</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Integer Coords</name>
      <Point>
        <coordinates>-122,37,110</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Scientific Notation</name>
      <Point>
        <coordinates>-1.22E+02,3.7E+01,1.2E+02</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "mixed_formats.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "mixed_output.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="min"
        )
        
        assert result.success == True
        assert result.point_count == 3
        assert output_file.exists()


class TestPerformanceAndLimits:
    """Tests for performance with larger datasets and resource limits."""
    
    def test_large_number_of_points(self, temp_dir):
        """Test processing KML with many elevation points."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with 1000 points
        kml_parts = ['''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Large Dataset</name>''']
        
        # Add 1000 points with varying elevations
        import random
        random.seed(42)  # For reproducible tests
        for i in range(1000):
            elevation = 100 + random.uniform(-50, 150)  # 50-250m range
            lon = -122.0 + random.uniform(-0.01, 0.01)
            lat = 37.0 + random.uniform(-0.01, 0.01)
            
            kml_parts.append(f'''    <Placemark>
      <name>Point {i}</name>
      <Point>
        <coordinates>{lon:.6f},{lat:.6f},{elevation:.3f}</coordinates>
      </Point>
    </Placemark>''')
        
        kml_parts.append('  </Document>\n</kml>')
        kml_content = '\n'.join(kml_parts)
        
        input_file = temp_dir / "large_dataset.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "large_output.kml"
        
        # Test performance
        import time
        start_time = time.time()
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file,
            elevation_units="meters",
            output_units="feet",
            reference_method="mean"
        )
        
        processing_time = time.time() - start_time
        
        assert result.success == True
        assert result.point_count == 1000
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        # Verify output file integrity
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        placemarks = root.findall('.//kml:Placemark', ns)
        assert len(placemarks) == 1000
    
    def test_memory_usage_with_large_dataset(self, temp_dir):
        """Test memory usage doesn't grow excessively with large datasets."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        import psutil
        import os
        
        # Get baseline memory
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create reasonably large KML (5000 points)
        kml_parts = ['''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Memory Test</name>''']
        
        for i in range(5000):
            elevation = 100 + (i % 200)  # Predictable pattern
            lon = -122.0 + (i % 100) * 0.0001
            lat = 37.0 + (i % 100) * 0.0001
            
            kml_parts.append(f'''    <Placemark>
      <name>Point {i}</name>
      <Point>
        <coordinates>{lon:.6f},{lat:.6f},{elevation:.1f}</coordinates>
      </Point>
    </Placemark>''')
        
        kml_parts.append('  </Document>\n</kml>')
        kml_content = '\n'.join(kml_parts)
        
        input_file = temp_dir / "memory_test.kml"
        input_file.write_text(kml_content)
        output_file = temp_dir / "memory_output.kml"
        
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file
        )
        
        # Check memory after processing
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory
        
        assert result.success == True
        assert result.point_count == 5000
        assert memory_increase < 500  # Should not use more than 500MB additional memory


class TestCorruptedInputHandling:
    """Tests for handling corrupted or malformed KML input."""
    
    def test_malformed_xml(self, temp_dir):
        """Test handling of malformed XML."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create malformed XML
        malformed_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Malformed</name>
    <Placemark>
      <name>Bad Point</name>
      <Point>
        <coordinates>-122.0,37.0,100.0</coordinates>
      </Point>
    <!-- Missing closing tag for Placemark -->
  </Document>
</kml>'''
        
        input_file = temp_dir / "malformed.kml"
        input_file.write_text(malformed_content)
        output_file = temp_dir / "malformed_output.kml"
        
        with pytest.raises(ProcessingError, match="Invalid KML file format"):
            convert_to_relative_elevation(
                input_file=input_file,
                output_file=output_file
            )
    
    def test_invalid_coordinates(self, temp_dir):
        """Test handling of invalid coordinate values."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with invalid coordinates
        invalid_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Invalid Coords</name>
    <Placemark>
      <name>Good Point</name>
      <Point>
        <coordinates>-122.0,37.0,100.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Bad Point 1</name>
      <Point>
        <coordinates>invalid,37.0,100.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Bad Point 2</name>
      <Point>
        <coordinates>-122.0,invalid,100.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Bad Point 3</name>
      <Point>
        <coordinates>-122.0,37.0,invalid</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Good Point 2</name>
      <Point>
        <coordinates>-122.001,37.001,110.0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "invalid_coords.kml"
        input_file.write_text(invalid_content)
        output_file = temp_dir / "invalid_coords_output.kml"
        
        # Should skip invalid coordinates and process valid ones
        result = convert_to_relative_elevation(
            input_file=input_file,
            output_file=output_file
        )
        
        assert result.success == True
        assert result.point_count == 2  # Only 2 valid points
        assert output_file.exists()
    
    def test_missing_elevation_in_coordinates(self, temp_dir):
        """Test handling of coordinates missing elevation component."""
        from topoconvert.core.relative_elevation import convert_to_relative_elevation
        
        # Create KML with 2D coordinates (no elevation)
        content_2d = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>2D Only</name>
    <Placemark>
      <name>2D Point</name>
      <Point>
        <coordinates>-122.0,37.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Another 2D Point</name>
      <Point>
        <coordinates>-122.001,37.001</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>'''
        
        input_file = temp_dir / "2d_coords.kml"
        input_file.write_text(content_2d)
        output_file = temp_dir / "2d_output.kml"
        
        # Should detect no elevation data
        with pytest.raises(ProcessingError, match="No points found"):
            convert_to_relative_elevation(
                input_file=input_file,
                output_file=output_file
            )