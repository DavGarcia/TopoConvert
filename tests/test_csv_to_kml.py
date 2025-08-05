"""Tests for CSV to KML conversion."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import xml.etree.ElementTree as ET
from topoconvert.cli import cli
from topoconvert.core.csv_kml import convert_csv_to_kml
from topoconvert.core.exceptions import FileFormatError, ProcessingError


class TestCsvToKml:
    """Test cases for csv-to-kml command."""
    
    def test_command_exists(self):
        """Test that the csv-to-kml command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['csv-to-kml', '--help'])
        assert result.exit_code == 0
        assert 'Convert CSV survey data to KML format' in result.output
        assert '--x-column' in result.output
        assert '--y-column' in result.output
        assert '--z-column' in result.output
    
    def test_basic_conversion(self, sample_csv_file):
        """Test basic CSV to KML conversion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.kml"
            
            # Use correct column mappings for sample CSV
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_file),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify it's valid XML/KML
            tree = ET.parse(output_file)
            root = tree.getroot()
            assert 'kml' in root.tag
            
            # Check for placemarks
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            placemarks = root.findall('.//kml:Placemark', ns)
            assert len(placemarks) >= 2  # Sample CSV has at least 2 points
    
    def test_custom_columns(self, temp_dir):
        """Test conversion with custom column names."""
        runner = CliRunner()
        
        # Create CSV with custom column names
        csv_content = """lon,lat,alt,name
-122.0822035,37.4222899,100.0,Point 1
-122.0844278,37.4222007,110.0,Point 2
-122.0856534,37.4219842,120.0,Point 3
"""
        csv_file = temp_dir / "custom_columns.csv"
        csv_file.write_text(csv_content)
        
        output_file = temp_dir / "output.kml"
        
        result = runner.invoke(cli, [
            'csv-to-kml',
            str(csv_file),
            str(output_file),
            '--x-column', 'lon',
            '--y-column', 'lat',
            '--z-column', 'alt'
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        
        # Verify KML contains points
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        coordinates = root.findall('.//kml:coordinates', ns)
        assert len(coordinates) == 3
    
    def test_label_option(self, sample_csv_file):
        """Test conversion with and without labels."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with labels (default)
            output_with_labels = Path(temp_dir) / "with_labels.kml"
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_with_labels),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z'
            ])
            assert result.exit_code == 0
            
            # Test without labels
            output_no_labels = Path(temp_dir) / "no_labels.kml"
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_no_labels),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z',
                '--no-labels'
            ])
            assert result.exit_code == 0
            
            # Both files should exist
            assert output_with_labels.exists()
            assert output_no_labels.exists()
    
    def test_elevation_units_conversion(self, sample_csv_file):
        """Test elevation unit conversion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with meters (default)
            output_meters = Path(temp_dir) / "meters.kml"
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_meters),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z',
                '--elevation-units', 'meters'
            ])
            assert result.exit_code == 0
            
            # Test with feet
            output_feet = Path(temp_dir) / "feet.kml"
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_feet),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z',
                '--elevation-units', 'feet'
            ])
            assert result.exit_code == 0
            
            assert output_meters.exists()
            assert output_feet.exists()
    
    def test_point_styling_options(self, sample_csv_file):
        """Test different point styling options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "styled.kml"
            
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_file),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z',
                '--point-style', 'pin',
                '--point-color', 'ff0000ff',  # Red
                '--point-scale', '1.5'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify style elements in KML
            tree = ET.parse(output_file)
            root = tree.getroot()
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            # Check for style elements
            styles = root.findall('.//kml:Style', ns)
            assert len(styles) > 0
    
    def test_kml_name_option(self, sample_csv_file):
        """Test custom KML document name."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "named.kml"
            
            result = runner.invoke(cli, [
                'csv-to-kml',
                str(sample_csv_file),
                str(output_file),
                '--x-column', 'x',
                '--y-column', 'y',
                '--z-column', 'z',
                '--kml-name', 'My Survey Data'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify document name in KML
            tree = ET.parse(output_file)
            root = tree.getroot()
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            name_elem = root.find('.//kml:Document/kml:name', ns)
            assert name_elem is not None
            assert name_elem.text == 'My Survey Data'
    
    def test_invalid_csv_file(self):
        """Test error handling for invalid CSV file."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'csv-to-kml',
            'nonexistent.csv',
            'output.kml'
        ])
        
        assert result.exit_code != 0
    
    def test_missing_required_columns(self, temp_dir):
        """Test error handling for CSV missing required columns."""
        runner = CliRunner()
        
        # Create CSV without required columns
        csv_content = """name,value
Point 1,100
Point 2,200
"""
        csv_file = temp_dir / "missing_columns.csv"
        csv_file.write_text(csv_content)
        
        output_file = temp_dir / "output.kml"
        
        result = runner.invoke(cli, [
            'csv-to-kml',
            str(csv_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        # Should complain about missing columns
    
    def test_invalid_point_style(self, sample_csv_file):
        """Test error handling for invalid point style."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'csv-to-kml',
            str(sample_csv_file),
            'output.kml',
            '--point-style', 'invalid'
        ])
        
        assert result.exit_code != 0
        assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()


class TestConvertCsvToKmlCoreFunction:
    """Test cases for the core convert_csv_to_kml function."""
    
    def test_convert_csv_to_kml_basic(self, sample_csv_file):
        """Test basic CSV to KML conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test.kml"
            
            # Use correct column mappings for sample CSV
            convert_csv_to_kml(
                input_file=sample_csv_file,
                output_file=output_file,
                x_column='x',
                y_column='y',
                z_column='z'
            )
            
            assert output_file.exists()
            
            # Verify KML structure
            tree = ET.parse(output_file)
            root = tree.getroot()
            assert 'kml' in root.tag
    
    def test_convert_csv_to_kml_with_options(self, sample_csv_file):
        """Test conversion with various options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_options.kml"
            
            convert_csv_to_kml(
                input_file=sample_csv_file,
                output_file=output_file,
                x_column='x',
                y_column='y',
                z_column='z',
                elevation_units='feet',
                point_style='square',
                point_color='ffff0000',  # Blue
                point_scale=1.2,
                add_labels=False,
                kml_name='Test Data'
            )
            
            assert output_file.exists()
    
    def test_convert_csv_to_kml_nonexistent_file(self):
        """Test error handling for nonexistent input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test.kml"
            
            with pytest.raises(FileNotFoundError):
                convert_csv_to_kml(
                    input_file=Path("nonexistent.csv"),
                    output_file=output_file
                )
    
    def test_convert_csv_to_kml_empty_csv(self, temp_dir):
        """Test handling of empty CSV file."""
        # Create empty CSV
        csv_file = temp_dir / "empty.csv"
        csv_file.write_text("")
        
        output_file = temp_dir / "output.kml"
        
        with pytest.raises(ProcessingError):
            convert_csv_to_kml(
                input_file=csv_file,
                output_file=output_file
            )
    
    def test_convert_csv_to_kml_invalid_coordinates(self, temp_dir):
        """Test handling of invalid coordinate values."""
        # Create CSV with invalid coordinates
        csv_content = """Longitude,Latitude,Elevation,Name
invalid,37.4222899,100.0,Point 1
-122.0844278,invalid,110.0,Point 2
"""
        csv_file = temp_dir / "invalid_coords.csv"
        csv_file.write_text(csv_content)
        
        output_file = temp_dir / "output.kml"
        
        with pytest.raises(ProcessingError):
            convert_csv_to_kml(
                input_file=csv_file,
                output_file=output_file
            )
    
    def test_convert_csv_to_kml_custom_columns(self, temp_dir):
        """Test conversion with custom column names."""
        # Create CSV with custom columns
        csv_content = """x_coord,y_coord,z_value,description
-122.0822035,37.4222899,100.0,First Point
-122.0844278,37.4222007,110.0,Second Point
"""
        csv_file = temp_dir / "custom.csv"
        csv_file.write_text(csv_content)
        
        output_file = temp_dir / "output.kml"
        
        convert_csv_to_kml(
            input_file=csv_file,
            output_file=output_file,
            x_column='x_coord',
            y_column='y_coord',
            z_column='z_value'
        )
        
        assert output_file.exists()
        
        # Verify coordinates were extracted correctly
        tree = ET.parse(output_file)
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        coordinates = root.findall('.//kml:coordinates', ns)
        assert len(coordinates) == 2
    
    def test_convert_csv_to_kml_missing_elevation(self, temp_dir):
        """Test handling of missing elevation data."""
        # Create CSV without elevation column
        csv_content = """Longitude,Latitude,Name
-122.0822035,37.4222899,Point 1
-122.0844278,37.4222007,Point 2
"""
        csv_file = temp_dir / "no_elevation.csv"
        csv_file.write_text(csv_content)
        
        output_file = temp_dir / "output.kml"
        
        # Should handle missing elevation gracefully (use 0 or skip)
        convert_csv_to_kml(
            input_file=csv_file,
            output_file=output_file,
            x_column='Longitude',
            y_column='Latitude',
            z_column='Elevation'  # Column doesn't exist
        )
        
        assert output_file.exists()