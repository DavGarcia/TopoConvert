"""Tests for the kml-relative-elevation CLI command."""
import pytest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from click.testing import CliRunner

from topoconvert.cli import cli


class TestKMLRelativeElevationCommand:
    """Tests for the kml-relative-elevation CLI command."""
    
    def test_command_exists(self):
        """Test that the command is registered with the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'kml-relative-elevation' in result.output
    
    def test_command_help(self):
        """Test command help display."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-relative-elevation', '--help'])
        assert result.exit_code == 0
        assert 'Convert KML elevations to relative values' in result.output
        assert '--elevation-units' in result.output
        assert '--output-units' in result.output
        assert '--reference-method' in result.output
        assert '--label-format' in result.output
        assert '--apply-style' in result.output
    
    def test_basic_command_execution(self, temp_dir):
        """Test basic command execution with required parameters."""
        runner = CliRunner()
        
        # Use existing fixture
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "output.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file)
        ])
        
        assert result.exit_code == 0
        assert 'Created relative elevation KML file' in result.output
        assert '3 elevation points processed' in result.output
        assert 'Input units: meters' in result.output
        assert 'Output units: feet' in result.output
        assert 'Reference method: min' in result.output
        
        # Verify output file was created
        assert output_file.exists()
        
        # Verify KML structure
        tree = ET.parse(output_file)
        root = tree.getroot()
        assert 'kml' in root.tag
    
    def test_command_with_all_options(self, temp_dir):
        """Test command with all available options."""
        runner = CliRunner()
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "custom_output.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file),
            '--elevation-units', 'meters',
            '--output-units', 'meters',
            '--reference-method', 'mean',
            '--label-format', 'Elevation: {value:.2f}m',
            '--no-style'
        ])
        
        assert result.exit_code == 0
        assert 'Created relative elevation KML file' in result.output
        assert 'Input units: meters' in result.output
        assert 'Output units: meters' in result.output
        assert 'Reference method: mean' in result.output
        assert 'No KML styling applied' in result.output
        
        # Verify output file
        assert output_file.exists()
        
        # Verify custom label format was applied
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        names = [elem.text for elem in root.findall('.//kml:name', ns) 
                if elem.text and 'Elevation:' in elem.text]
        assert len(names) >= 3
        
        for name in names:
            assert 'Elevation:' in name
            assert 'm' in name
    
    def test_auto_generated_output_filename(self, temp_dir):
        """Test automatic output filename generation."""
        runner = CliRunner()
        
        # Copy fixture to temp directory so we can control the output location
        input_file = temp_dir / "test_input.kml"
        fixture_content = (Path(__file__).parent / "fixtures" / "simple_3points.kml").read_text()
        input_file.write_text(fixture_content)
        
        # Don't specify output file - should auto-generate
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file)
        ])
        
        assert result.exit_code == 0
        assert 'Auto-generating output file' in result.output
        
        # Check that auto-generated file was created
        expected_output = temp_dir / "test_input_relative.kml"
        assert expected_output.exists()
        
        # Verify content
        tree = ET.parse(expected_output)
        root = tree.getroot()
        assert 'kml' in root.tag
    
    def test_different_reference_methods(self, temp_dir):
        """Test different reference methods."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        reference_methods = ['min', 'max', 'mean']
        
        for method in reference_methods:
            output_file = temp_dir / f"output_{method}.kml"
            
            result = runner.invoke(cli, [
                'kml-relative-elevation',
                str(input_file),
                str(output_file),
                '--reference-method', method
            ])
            
            assert result.exit_code == 0
            assert f'Reference method: {method}' in result.output
            assert output_file.exists()
    
    def test_different_unit_combinations(self, temp_dir):
        """Test different unit combinations."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        unit_combinations = [
            ('meters', 'feet'),
            ('feet', 'meters'),
            ('meters', 'meters'),
            ('feet', 'feet')
        ]
        
        for input_units, output_units in unit_combinations:
            output_file = temp_dir / f"output_{input_units}_to_{output_units}.kml"
            
            result = runner.invoke(cli, [
                'kml-relative-elevation',
                str(input_file),
                str(output_file),
                '--elevation-units', input_units,
                '--output-units', output_units
            ])
            
            assert result.exit_code == 0
            assert f'Input units: {input_units}' in result.output
            assert f'Output units: {output_units}' in result.output
            assert output_file.exists()
    
    def test_custom_label_formats(self, temp_dir):
        """Test various custom label formats."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        label_formats = [
            "{value:.1f} {unit}",
            "Height: {value:.2f}m",
            "Elev {value:.0f} {unit} above base",
            "{value:.3f}"
        ]
        
        for label_format in label_formats:
            output_file = temp_dir / f"output_custom_{len(label_format)}.kml"
            
            result = runner.invoke(cli, [
                'kml-relative-elevation',
                str(input_file),
                str(output_file),
                '--label-format', label_format
            ])
            
            assert result.exit_code == 0
            assert f'Label format: {label_format}' in result.output
            assert output_file.exists()
    
    def test_styling_options(self, temp_dir):
        """Test styling enable/disable options."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        # Test with styling enabled (default)
        output_file_styled = temp_dir / "styled.kml"
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file_styled),
            '--apply-style'
        ])
        
        assert result.exit_code == 0
        assert 'KML styling applied' in result.output
        
        # Verify style is present
        tree = ET.parse(output_file_styled)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        styles = root.findall('.//kml:Style[@id="elevLabels"]', ns)
        assert len(styles) == 1
        
        # Test with styling disabled
        output_file_unstyled = temp_dir / "unstyled.kml"
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file_unstyled),
            '--no-style'
        ])
        
        assert result.exit_code == 0
        assert 'No KML styling applied' in result.output
        
        # Verify no style is present
        tree = ET.parse(output_file_unstyled)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        styles = root.findall('.//kml:Style[@id="elevLabels"]', ns)
        assert len(styles) == 0


class TestKMLRelativeElevationCommandErrorHandling:
    """Tests for error handling in the kml-relative-elevation command."""
    
    def test_missing_input_file(self, temp_dir):
        """Test error handling for missing input file."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            'nonexistent.kml',
            str(temp_dir / "output.kml")
        ])
        
        assert result.exit_code != 0
        assert 'Error:' in result.output
    
    def test_invalid_elevation_units(self, temp_dir):
        """Test error handling for invalid elevation units."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(temp_dir / "output.kml"),
            '--elevation-units', 'invalid'
        ])
        
        assert result.exit_code != 0
        # Click should handle invalid choice validation
    
    def test_invalid_output_units(self, temp_dir):
        """Test error handling for invalid output units."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(temp_dir / "output.kml"),
            '--output-units', 'invalid'
        ])
        
        assert result.exit_code != 0
        # Click should handle invalid choice validation
    
    def test_invalid_reference_method(self, temp_dir):
        """Test error handling for invalid reference method."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(temp_dir / "output.kml"),
            '--reference-method', 'invalid'
        ])
        
        assert result.exit_code != 0
        # Click should handle invalid choice validation
    
    def test_empty_kml_file_error(self, temp_dir):
        """Test error handling for empty KML file."""
        runner = CliRunner()
        
        # Use existing empty fixture
        input_file = Path(__file__).parent / "fixtures" / "empty.kml"
        output_file = temp_dir / "output.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert 'Error:' in result.output
    
    def test_no_elevation_data_error(self, temp_dir):
        """Test error handling for KML with no elevation data."""
        runner = CliRunner()
        
        # Use fixture without elevation data
        input_file = Path(__file__).parent / "fixtures" / "no_elevation.kml"
        output_file = temp_dir / "output.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert 'Error:' in result.output
    
    def test_invalid_kml_format_error(self, temp_dir):
        """Test error handling for invalid KML format."""
        runner = CliRunner()
        
        # Create invalid KML file
        invalid_kml = temp_dir / "invalid.kml"
        invalid_kml.write_text("This is not valid XML")
        
        output_file = temp_dir / "output.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(invalid_kml),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert 'Error:' in result.output


class TestKMLRelativeElevationCommandOutput:
    """Tests for command output formatting and information display."""
    
    def test_detailed_output_information(self, temp_dir):
        """Test that command provides detailed output information."""
        runner = CliRunner()
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "detailed_output.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file),
            '--reference-method', 'mean'
        ])
        
        assert result.exit_code == 0
        
        # Check for detailed information in output
        assert 'Created relative elevation KML file' in result.output
        assert 'elevation points processed' in result.output
        assert 'Input units:' in result.output
        assert 'Output units:' in result.output
        assert 'Reference method:' in result.output
        assert 'Reference value:' in result.output
        assert 'Original elevation range:' in result.output
        assert 'Relative elevation range:' in result.output
        assert 'Label format:' in result.output
    
    def test_range_calculations_display(self, temp_dir):
        """Test that elevation range calculations are displayed correctly."""
        runner = CliRunner()
        
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        output_file = temp_dir / "range_test.kml"
        
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file),
            '--elevation-units', 'meters',
            '--output-units', 'feet',
            '--reference-method', 'min'
        ])
        
        assert result.exit_code == 0
        
        # With min reference, the range should start from 0.0 ft
        # Original elevations: 100, 110, 120 meters
        # In feet: ~328.1, ~360.9, ~393.7 ft
        # Relative to min: 0.0, ~32.8, ~65.6 ft
        
        assert 'Original elevation range:' in result.output
        assert 'Relative elevation range:' in result.output
        assert '0.0 to' in result.output  # Min reference should start at 0.0
    
    def test_unit_display_formatting(self, temp_dir):
        """Test proper unit display formatting."""
        runner = CliRunner()
        input_file = Path(__file__).parent / "fixtures" / "simple_3points.kml"
        
        # Test feet output
        output_file_ft = temp_dir / "feet_output.kml"
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file_ft),
            '--output-units', 'feet'
        ])
        
        assert result.exit_code == 0
        assert 'ft' in result.output
        
        # Test meters output
        output_file_m = temp_dir / "meters_output.kml"
        result = runner.invoke(cli, [
            'kml-relative-elevation',
            str(input_file),
            str(output_file_m),
            '--output-units', 'meters'
        ])
        
        assert result.exit_code == 0
        assert 'm' in result.output and 'ft' not in result.output.split('Label format:')[0]