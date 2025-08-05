"""Tests for combined DXF core functionality with result types."""
import pytest
import tempfile
from pathlib import Path
import pandas as pd
import ezdxf

from topoconvert.core.combined_dxf import merge_csv_to_dxf
from topoconvert.core.exceptions import ProcessingError, FileFormatError
from topoconvert.core.result_types import CombinedDXFResult


class TestCombinedDXFWithResultTypes:
    """Test cases for combined DXF functionality returning result objects."""
    
    def test_merge_csv_to_dxf_returns_result(self):
        """Test that merge_csv_to_dxf returns a CombinedDXFResult."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test CSV files
            csv1 = Path(temp_dir) / "test1.csv"
            csv2 = Path(temp_dir) / "test2.csv"
            output = Path(temp_dir) / "output.dxf"
            
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
            result = merge_csv_to_dxf([csv1, csv2], output)
            
            # Check result type
            assert isinstance(result, CombinedDXFResult)
            assert result.success is True
            assert result.output_file == str(output)
            assert result.input_file_count == 2
            assert result.total_points == 4
            assert len(result.layers_created) == 2
            assert "test1_POINTS" in result.layers_created
            assert "test2_POINTS" in result.layers_created
            assert result.translated_to_origin is True
            assert result.reference_point is not None
            assert len(result.reference_point) == 3
            
            # Check output file exists
            assert output.exists()
            
            # Verify DXF structure
            doc = ezdxf.readfile(str(output))
            assert len(doc.layers) >= 2
    
    def test_result_contains_dataset_details(self):
        """Test that result contains dataset details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "data1.csv"
            output = Path(temp_dir) / "output.dxf"
            
            df = pd.DataFrame({
                'Latitude': [37.1],
                'Longitude': [-122.1],
                'Elevation': [100]
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_dxf([csv1], output)
            
            assert 'datasets' in result.details
            assert len(result.details['datasets']) == 1
            
            # Check dataset info (name, count, message)
            name, count, msg = result.details['datasets'][0]
            assert name == 'data1'
            assert count == 1
            assert 'with elevation' in msg
    
    def test_result_contains_coordinate_ranges(self):
        """Test that result contains coordinate range information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "points.csv"
            output = Path(temp_dir) / "output.dxf"
            
            df = pd.DataFrame({
                'Latitude': [37.1, 37.2, 37.3],
                'Longitude': [-122.1, -122.2, -122.3],
                'Elevation': [100, 200, 300]
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_dxf([csv1], output)
            
            assert 'coordinate_ranges' in result.details
            ranges = result.details['coordinate_ranges']
            
            # Check ranges exist
            assert 'x' in ranges
            assert 'y' in ranges
            assert 'z' in ranges
            assert 'units' in ranges
            
            # Check units
            units = ranges['units']
            assert units['x'] == 'feet'
            assert units['y'] == 'feet'
            assert units['z'] == 'feet'
            
            # Check ranges start at 0
            assert ranges['x'][0] == 0.0
            assert ranges['y'][0] == 0.0
            assert ranges['z'][0] == 0.0
    
    def test_result_with_wgs84_coordinates(self):
        """Test result when using WGS84 coordinates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv1 = Path(temp_dir) / "wgs84.csv"
            output = Path(temp_dir) / "output.dxf"
            
            df = pd.DataFrame({
                'Latitude': [37.1],
                'Longitude': [-122.1],
                'Elevation': [100]
            })
            df.to_csv(csv1, index=False)
            
            result = merge_csv_to_dxf([csv1], output, wgs84=True)
            
            assert result.coordinate_system == "WGS84 (degrees)"
            
            # Check units for WGS84
            if 'coordinate_ranges' in result.details:
                units = result.details['coordinate_ranges']['units']
                assert units['x'] == 'degrees'
                assert units['y'] == 'degrees'
                assert units['z'] == 'meters'  # Elevation stays in meters
    
    def test_empty_file_list_raises_error(self):
        """Test that empty file list raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "output.dxf"
            
            with pytest.raises(ValueError, match="At least one CSV file is required"):
                merge_csv_to_dxf([], output)
    
    def test_missing_file_raises_error(self):
        """Test that missing input file raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.csv"
            output = Path(temp_dir) / "output.dxf"
            
            with pytest.raises(FileNotFoundError):
                merge_csv_to_dxf([missing], output)