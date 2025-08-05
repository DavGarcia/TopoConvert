"""Tests for KML to points extraction."""
import pytest
import tempfile
import json
from pathlib import Path
from click.testing import CliRunner
from topoconvert.cli import cli
from topoconvert.core.points import extract_points
from topoconvert.core.exceptions import FileFormatError, ProcessingError


class TestKmlToPoints:
    """Test cases for kml-to-points command."""
    
    def test_command_exists(self):
        """Test that the kml-to-points command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-to-points', '--help'])
        assert result.exit_code == 0
        assert 'Extract point data from KML files' in result.output
        assert '--format' in result.output
        assert '--elevation-units' in result.output
    
    def test_output_formats(self, simple_kml):
        """Test different output format options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test CSV format (default)
            csv_output = Path(temp_dir) / "points.csv"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(csv_output),
                '--format', 'csv'
            ])
            assert result.exit_code == 0
            assert csv_output.exists()
            
            # Verify CSV content
            with open(csv_output) as f:
                content = f.read().lower()
                assert 'longitude' in content or 'x' in content
                assert 'latitude' in content or 'y' in content
                assert 'elevation' in content or 'z' in content
            
            # Test JSON format
            json_output = Path(temp_dir) / "points.json"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(json_output),
                '--format', 'json'
            ])
            assert result.exit_code == 0
            assert json_output.exists()
            
            # Verify JSON is valid
            with open(json_output) as f:
                data = json.load(f)
                assert 'points' in data or isinstance(data, list)
            
            # Test TXT format
            txt_output = Path(temp_dir) / "points.txt"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(txt_output),
                '--format', 'txt'
            ])
            assert result.exit_code == 0
            assert txt_output.exists()
            
            # Test DXF format
            dxf_output = Path(temp_dir) / "points.dxf"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(dxf_output),
                '--format', 'dxf'
            ])
            assert result.exit_code == 0
            assert dxf_output.exists()
    
    def test_point_extraction(self, simple_kml):
        """Test point extraction from KML."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "extracted_points.csv"
            
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify extracted points
            with open(output_file) as f:
                lines = f.readlines()
                # Should have header + 3 points from simple_kml fixture
                assert len(lines) >= 4  # header + 3 points
    
    def test_default_output_file(self, simple_kml):
        """Test default output filename generation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy KML to temp directory
            temp_kml = Path(temp_dir) / "test_input.kml"
            temp_kml.write_text(simple_kml.read_text())
            
            # Run without specifying output file
            result = runner.invoke(cli, [
                'kml-to-points',
                str(temp_kml),
                '--format', 'csv'
            ])
            
            assert result.exit_code == 0
            
            # Check default output file was created
            default_output = temp_kml.with_suffix('.csv')
            assert default_output.exists()
    
    def test_elevation_units_conversion(self, simple_kml):
        """Test elevation unit conversion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with meters (default)
            meters_output = Path(temp_dir) / "points_meters.csv"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(meters_output),
                '--elevation-units', 'meters'
            ])
            assert result.exit_code == 0
            
            # Test with feet
            feet_output = Path(temp_dir) / "points_feet.csv"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(feet_output),
                '--elevation-units', 'feet'
            ])
            assert result.exit_code == 0
            
            # Both files should exist but might have different elevation values
            assert meters_output.exists()
            assert feet_output.exists()
    
    def test_dxf_specific_options(self, simple_kml):
        """Test DXF-specific options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with translation disabled
            output_file = Path(temp_dir) / "points_no_translate.dxf"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(output_file),
                '--format', 'dxf',
                '--no-translate'
            ])
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Test with custom layer name and color
            output_file2 = Path(temp_dir) / "points_custom.dxf"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(output_file2),
                '--format', 'dxf',
                '--layer-name', 'CUSTOM_LAYER',
                '--point-color', '5'
            ])
            assert result.exit_code == 0
            assert output_file2.exists()
            
            # Test with WGS84 flag
            output_file3 = Path(temp_dir) / "points_wgs84.dxf"
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(output_file3),
                '--format', 'dxf',
                '--wgs84'
            ])
            assert result.exit_code == 0
            assert output_file3.exists()
    
    def test_projection_options_conflict(self, simple_kml):
        """Test that conflicting projection options are rejected."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.dxf"
            
            # Try to use both --target-epsg and --wgs84
            result = runner.invoke(cli, [
                'kml-to-points',
                str(simple_kml),
                str(output_file),
                '--format', 'dxf',
                '--target-epsg', '32614',
                '--wgs84'
            ])
            
            assert result.exit_code != 0
            assert 'Cannot use both --target-epsg and --wgs84' in result.output
    
    def test_invalid_input_file(self):
        """Test error handling for invalid input file."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-to-points',
            'nonexistent.kml',
            'output.csv'
        ])
        
        assert result.exit_code != 0
    
    def test_invalid_format(self, simple_kml):
        """Test error handling for invalid output format."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-to-points',
            str(simple_kml),
            'output.xyz',
            '--format', 'invalid'
        ])
        
        assert result.exit_code != 0
        assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()


class TestExtractPointsCoreFunction:
    """Test cases for the core extract_points function."""
    
    def test_extract_points_basic(self, simple_kml):
        """Test basic point extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.csv"
            
            extract_points(
                input_file=simple_kml,
                output_file=output_file,
                output_format='csv'
            )
            
            assert output_file.exists()
            
            # Verify CSV content
            with open(output_file) as f:
                lines = f.readlines()
                assert len(lines) >= 4  # header + 3 points
    
    def test_extract_points_dxf_format(self, grid_kml):
        """Test DXF output format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.dxf"
            
            extract_points(
                input_file=grid_kml,
                output_file=output_file,
                output_format='dxf',
                layer_name='TEST_LAYER',
                point_color=5
            )
            
            assert output_file.exists()
            
            # Verify it's a valid DXF by trying to read it
            import ezdxf
            try:
                doc = ezdxf.readfile(str(output_file))
                assert 'TEST_LAYER' in doc.layers
            except Exception as e:
                pytest.fail(f"Generated DXF is not valid: {e}")
    
    def test_extract_points_json_format(self, simple_kml):
        """Test JSON output format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.json"
            
            extract_points(
                input_file=simple_kml,
                output_file=output_file,
                output_format='json'
            )
            
            assert output_file.exists()
            
            # Verify JSON structure
            with open(output_file) as f:
                data = json.load(f)
                assert isinstance(data, (list, dict))
                if isinstance(data, dict):
                    assert 'points' in data
    
    def test_extract_points_txt_format(self, simple_kml):
        """Test text output format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.txt"
            
            extract_points(
                input_file=simple_kml,
                output_file=output_file,
                output_format='txt'
            )
            
            assert output_file.exists()
            
            # Verify text content
            with open(output_file) as f:
                content = f.read()
                # Should contain coordinate data
                assert '-122' in content  # longitude from fixture
                assert '37' in content    # latitude from fixture
    
    def test_extract_points_nonexistent_file(self):
        """Test error handling for nonexistent input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.csv"
            
            with pytest.raises(FileNotFoundError, match="File not found"):
                extract_points(
                    input_file=Path("nonexistent.kml"),
                    output_file=output_file
                )
    
    def test_extract_points_empty_kml(self, empty_kml):
        """Test handling of empty KML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.csv"
            
            with pytest.raises(ProcessingError, match="No points found"):
                extract_points(
                    input_file=empty_kml,
                    output_file=output_file
                )
    
    def test_extract_points_invalid_format(self, simple_kml):
        """Test error handling for invalid output format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "points.xyz"
            
            with pytest.raises(ValueError, match="output_format"):
                extract_points(
                    input_file=simple_kml,
                    output_file=output_file,
                    output_format='invalid'
                )
    
    def test_extract_points_with_elevation_units(self, simple_kml):
        """Test elevation unit handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract with meters
            meters_file = Path(temp_dir) / "points_m.csv"
            extract_points(
                input_file=simple_kml,
                output_file=meters_file,
                output_format='csv',
                elevation_units='meters'
            )
            
            # Extract with feet
            feet_file = Path(temp_dir) / "points_ft.csv"
            extract_points(
                input_file=simple_kml,
                output_file=feet_file,
                output_format='csv',
                elevation_units='feet'
            )
            
            assert meters_file.exists()
            assert feet_file.exists()