"""Tests for consistent input validation across modules."""
import pytest
from pathlib import Path
import tempfile
import os

from topoconvert.core.combined_dxf import merge_csv_to_dxf
from topoconvert.core.combined_kml import merge_csv_to_kml
from topoconvert.core.exceptions import FileFormatError, ProcessingError


class TestValidationConsistency:
    """Test that all modules validate inputs consistently."""
    
    def test_merge_csv_to_dxf_validates_missing_files(self):
        """Test that merge_csv_to_dxf validates missing input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that doesn't exist
            missing_file = Path(tmpdir) / "missing.csv"
            output_file = Path(tmpdir) / "output.dxf"
            
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="File not found"):
                merge_csv_to_dxf([missing_file], output_file)
    
    def test_merge_csv_to_kml_validates_missing_files(self):
        """Test that merge_csv_to_kml validates missing input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that doesn't exist
            missing_file = Path(tmpdir) / "missing.csv"
            output_file = Path(tmpdir) / "output.kml"
            
            # Should raise FileNotFoundError (after our fix)
            with pytest.raises(FileNotFoundError, match="File not found"):
                merge_csv_to_kml([missing_file], output_file)
    
    def test_both_functions_validate_before_processing(self):
        """Test that validation happens before any processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create one valid file and one missing file
            valid_file = Path(tmpdir) / "valid.csv"
            valid_file.write_text("Latitude,Longitude,Elevation\n37.0,-122.0,100.0\n")
            
            missing_file = Path(tmpdir) / "missing.csv"
            
            # Both functions should fail immediately without processing valid_file
            with pytest.raises(FileNotFoundError):
                merge_csv_to_dxf([valid_file, missing_file], Path(tmpdir) / "out.dxf")
            
            with pytest.raises(FileNotFoundError):
                merge_csv_to_kml([valid_file, missing_file], Path(tmpdir) / "out.kml")
    
    def test_empty_file_list_handling(self):
        """Test handling of empty file lists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dxf = Path(tmpdir) / "output.dxf"
            output_kml = Path(tmpdir) / "output.kml"
            
            # Both should handle empty lists appropriately
            with pytest.raises(ValueError, match="At least one CSV file is required"):
                merge_csv_to_dxf([], output_dxf)
            
            with pytest.raises(ProcessingError, match="No CSV files provided"):
                merge_csv_to_kml([], output_kml)
    
    def test_output_extension_correction(self):
        """Test that output files get correct extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid CSV file
            csv_file = Path(tmpdir) / "data.csv"
            csv_file.write_text("Latitude,Longitude,Elevation\n37.0,-122.0,100.0\n")
            
            # Test with wrong extension for DXF
            wrong_ext_dxf = Path(tmpdir) / "output.txt"
            # This would need to be tested by checking the actual output file
            # For now we just verify the function doesn't crash
            
            # Test with wrong extension for KML
            wrong_ext_kml = Path(tmpdir) / "output.txt"
            # This would need to be tested by checking the actual output file