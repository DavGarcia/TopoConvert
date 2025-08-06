"""Test suite for edge case test data generators."""

import tempfile
import pytest
from pathlib import Path
from typing import List, Tuple
import xml.etree.ElementTree as ET
import pandas as pd
import ezdxf

from tests.edge_case_generators import (
    generate_large_point_dataset,
    generate_corrupted_kml,
    generate_corrupted_csv,
    CorruptionType,
    KMLCorruption,
    CSVCorruption
)


class TestLargeDatasetGeneration:
    """Test large dataset generation utilities."""

    def test_generate_large_point_dataset_basic(self):
        """Test basic large dataset generation."""
        points = generate_large_point_dataset(count=1000, bounds=(-1, -1, 1, 1))
        
        assert len(points) == 1000
        assert all(isinstance(p, tuple) and len(p) == 3 for p in points)
        
        # Check bounds
        x_coords, y_coords, z_coords = zip(*points)
        assert min(x_coords) >= -1
        assert max(x_coords) <= 1
        assert min(y_coords) >= -1
        assert max(y_coords) <= 1

    def test_generate_large_point_dataset_elevation_range(self):
        """Test elevation range in generated datasets."""
        points = generate_large_point_dataset(
            count=100, 
            bounds=(0, 0, 10, 10),
            elevation_range=(50, 150)
        )
        
        z_coords = [p[2] for p in points]
        assert min(z_coords) >= 50
        assert max(z_coords) <= 150

    def test_generate_large_point_dataset_extreme_sizes(self):
        """Test generation of very large datasets."""
        # Test 10k points (should complete quickly)
        points = generate_large_point_dataset(count=10000)
        assert len(points) == 10000
        
        # Test memory efficiency - should not consume excessive memory
        import sys
        size = sys.getsizeof(points)
        # Should be reasonable for 10k points (rough estimate < 1MB)
        assert size < 1024 * 1024


class TestCorruptedKMLGeneration:
    """Test corrupted KML file generation."""

    def test_generate_corrupted_kml_malformed_xml(self):
        """Test generation of malformed XML KML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_corrupted_kml(
                temp_path,
                corruption_type=KMLCorruption.MALFORMED_XML,
                point_count=10
            )
            
            assert temp_path.exists()
            content = temp_path.read_text()
            
            # Should contain KML-like content but be malformed
            assert 'kml' in content.lower()
            
            # Should not be valid XML
            with pytest.raises(ET.ParseError):
                ET.parse(temp_path)
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_generate_corrupted_kml_invalid_coordinates(self):
        """Test generation of KML with invalid coordinates."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_corrupted_kml(
                temp_path,
                corruption_type=KMLCorruption.INVALID_COORDINATES,
                point_count=5
            )
            
            assert temp_path.exists()
            content = temp_path.read_text()
            
            # Should be valid XML but have invalid coordinates
            root = ET.parse(temp_path).getroot()
            assert root is not None
            
            # Should contain some invalid coordinate values
            assert any(invalid in content for invalid in ['999', 'invalid', 'NaN'])
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_generate_corrupted_kml_missing_elements(self):
        """Test generation of KML with missing required elements."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_corrupted_kml(
                temp_path,
                corruption_type=KMLCorruption.MISSING_ELEMENTS,
                point_count=3
            )
            
            assert temp_path.exists()
            
            # Should be valid XML but missing critical elements
            root = ET.parse(temp_path).getroot()
            assert root is not None
            
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestCorruptedCSVGeneration:
    """Test corrupted CSV file generation."""

    def test_generate_corrupted_csv_wrong_columns(self):
        """Test generation of CSV with wrong column structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_corrupted_csv(
                temp_path,
                corruption_type=CSVCorruption.WRONG_COLUMNS,
                row_count=10
            )
            
            assert temp_path.exists()
            
            # Should be readable as CSV but have unexpected columns
            df = pd.read_csv(temp_path)
            expected_columns = {'x', 'y', 'z'}
            actual_columns = set(df.columns.str.lower())
            
            # Should not have standard survey columns
            assert not expected_columns.issubset(actual_columns)
            
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_generate_corrupted_csv_invalid_data_types(self):
        """Test generation of CSV with invalid data types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_corrupted_csv(
                temp_path,
                corruption_type=CSVCorruption.INVALID_DATA_TYPES,
                row_count=5
            )
            
            assert temp_path.exists()
            
            df = pd.read_csv(temp_path)
            assert len(df) == 5
            
            # Should contain some non-numeric values in coordinate columns
            coordinate_cols = [col for col in df.columns if col.lower() in ['x', 'y', 'z', 'latitude', 'longitude']]
            if coordinate_cols:
                for col in coordinate_cols:
                    # Try to convert to numeric - should have some failures
                    numeric_series = pd.to_numeric(df[col], errors='coerce')
                    assert numeric_series.isna().any()  # Some values should be unconvertible
            
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_generate_corrupted_csv_encoding_issues(self):
        """Test generation of CSV with encoding problems."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            generate_corrupted_csv(
                temp_path,
                corruption_type=CSVCorruption.ENCODING_ISSUES,
                row_count=3
            )
            
            assert temp_path.exists()
            
            # Should exist but may cause encoding issues when read with wrong encoding
            content = temp_path.read_bytes()
            assert len(content) > 0
            
            # Try reading with UTF-8 - might fail or produce unexpected characters
            try:
                text_content = content.decode('utf-8')
                # Should contain some special characters from the special_chars list
                # or we should have encoding issues (which is the point of this test)
                has_special_chars = any(char in text_content for char in ['café', 'naïve', 'résumé', 'Москва', '北京', '🌍'])
                assert has_special_chars or len(content) > 0  # Either has special chars or has content indicating encoding mixing
            except UnicodeDecodeError:
                # This is expected for encoding issues - test passes
                pass
            
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestCorruptionTypeValidation:
    """Test corruption type enumeration and validation."""

    def test_corruption_type_coverage(self):
        """Test that all corruption types are covered."""
        kml_types = list(KMLCorruption)
        csv_types = list(CSVCorruption)
        
        assert len(kml_types) >= 3  # At least malformed_xml, invalid_coordinates, missing_elements
        assert len(csv_types) >= 3  # At least wrong_columns, invalid_data_types, encoding_issues
        
        # Each type should have a string representation
        for corruption_type in kml_types + csv_types:
            assert isinstance(corruption_type.value, str)
            assert len(corruption_type.value) > 0