"""Tests for combined KML core functionality with result types."""
import pytest
import tempfile
from pathlib import Path
import pandas as pd
from xml.etree import ElementTree as ET

from topoconvert.core.combined_kml import merge_csv_to_kml
from topoconvert.core.exceptions import ProcessingError
from topoconvert.core.result_types import CombinedKMLResult


class TestCombinedKMLWithResultTypes:
    """Test cases for combined KML functionality returning result objects."""
    
    def test_merge_csv_to_kml_returns_result(self):
        """Test that merge_csv_to_kml returns a CombinedKMLResult."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test CSV files
            csv1 = Path(temp_dir) / "test1.csv"
            csv2 = Path(temp_dir) / "test2.csv"
            output = Path(temp_dir) / "output.kml"
            
            # Write test data
            df1 = pd.DataFrame({
                'Latitude': [37.1, 37.2],
                'Longitude': [-122.1, -122.2],
                'Elevation': [100, 200]
            })
            df2 = pd.DataFrame({
                'Latitude': [37.3, 37.4],
                'Longitude': [-122.3, -122.4],
                'Elevation': [150, 250]
            })
            
            df1.to_csv(csv1, index=False)
            df2.to_csv(csv2, index=False)
            
            # Run merge
            result = merge_csv_to_kml([csv1, csv2], output)
            
            # Check result type
            assert isinstance(result, CombinedKMLResult)
            assert result.success is True
            assert result.output_file == str(output)
            assert result.input_file_count == 2
            assert result.total_points == 4
            assert result.elevations_converted is False  # Default is meters
            
            # Check output file exists
            assert output.exists()
            
            # Verify KML structure
            tree = ET.parse(str(output))
            root = tree.getroot()
            # Check namespace
            assert 'kml' in root.tag
    
    def test_result_contains_dataset_details(self):
        """Test that result contains dataset details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "data1.csv"
            output = Path(temp_dir) / "output.kml"
            
            df = pd.DataFrame({
                'Latitude': [37.1],
                'Longitude': [-122.1],
                'Elevation': [100]
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_kml([csv1], output)
            
            assert 'datasets' in result.details
            assert len(result.details['datasets']) == 1
            
            # Check dataset info (name, count)
            name, count = result.details['datasets'][0]
            assert name == 'data1'
            assert count == 1
    
    def test_result_with_elevation_conversion(self):
        """Test result when converting elevation from feet to meters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "feet_elev.csv"
            output = Path(temp_dir) / "output.kml"
            
            df = pd.DataFrame({
                'Latitude': [37.1],
                'Longitude': [-122.1],
                'Elevation': [328.084]  # 100 meters in feet
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_kml([csv1], output, elevation_units='feet')
            
            assert result.elevations_converted is True
    
    def test_result_contains_options_used(self):
        """Test that result details contain options used."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "test.csv"
            output = Path(temp_dir) / "output.kml"
            
            df = pd.DataFrame({
                'Latitude': [37.1],
                'Longitude': [-122.1],
                'Elevation': [100]
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_kml(
                [csv1], 
                output,
                point_scale=2.0,
                add_labels=False,
                x_column='Longitude',
                y_column='Latitude',
                z_column='Elevation'
            )
            
            assert result.details['point_scale'] == 2.0
            assert result.details['labels_added'] is False
            assert result.details['column_names']['x'] == 'Longitude'
            assert result.details['column_names']['y'] == 'Latitude'
            assert result.details['column_names']['z'] == 'Elevation'
    
    def test_empty_file_list_raises_error(self):
        """Test that empty file list raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "output.kml"
            
            with pytest.raises(ProcessingError, match="No CSV files provided"):
                merge_csv_to_kml([], output)
    
    def test_missing_file_raises_error(self):
        """Test that missing input file raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.csv"
            output = Path(temp_dir) / "output.kml"
            
            with pytest.raises(FileNotFoundError):
                merge_csv_to_kml([missing], output)
    
    def test_missing_column_raises_error(self):
        """Test that missing required column raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "bad.csv"
            output = Path(temp_dir) / "output.kml"
            
            # Missing Longitude column
            df = pd.DataFrame({
                'Latitude': [37.1],
                'Elevation': [100]
            })
            df.to_csv(csv1, index=False)
            
            with pytest.raises(ProcessingError, match="Column 'Longitude' not found"):
                merge_csv_to_kml([csv1], output)
    
    def test_custom_column_names(self):
        """Test using custom column names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "custom.csv"
            output = Path(temp_dir) / "output.kml"
            
            df = pd.DataFrame({
                'Y': [37.1],
                'X': [-122.1],
                'Z': [100]
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_kml(
                [csv1], 
                output,
                x_column='X',
                y_column='Y',
                z_column='Z'
            )
            
            assert result.success is True
            assert result.total_points == 1