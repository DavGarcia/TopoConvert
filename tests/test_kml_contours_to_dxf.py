"""Tests for KML contours to DXF conversion."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from xml.etree import ElementTree as ET
import ezdxf

from topoconvert.cli import cli
from topoconvert.core.kml_contours import convert_kml_contours_to_dxf
from topoconvert.core.exceptions import TopoConvertError, ProcessingError, FileFormatError


class TestKmlContoursToDxfCommand:
    """Test cases for kml-contours-to-dxf command."""
    
    def test_command_exists(self):
        """Test that the kml-contours-to-dxf command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-contours-to-dxf', '--help'])
        assert result.exit_code == 0
        assert 'Convert KML contour LineStrings to DXF format' in result.output
        assert 'Reads KML files with LineString elements' in result.output
    
    def test_command_arguments_and_options(self):
        """Test that all expected arguments and options are available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-contours-to-dxf', '--help'])
        assert result.exit_code == 0
        
        # Check required arguments
        assert 'INPUT_FILE' in result.output
        assert 'OUTPUT_FILE' in result.output
        
        # Check all options
        assert '--elevation-units' in result.output
        assert '--label / --no-label' in result.output
        assert '--label-height' in result.output
        assert '--translate / --no-translate' in result.output
        assert '--target-epsg' in result.output
        assert '--wgs84' in result.output
    
    def test_basic_kml_contours_conversion(self):
        """Test basic KML contours to DXF conversion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple KML with contour LineStrings
            input_file = Path(temp_dir) / "contours.kml"
            output_file = Path(temp_dir) / "contours_output.dxf"
            
            # Create test KML with contour lines
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>100m Contour</name>
      <LineString>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
          -122.0840,37.4220,100
          -122.0835,37.4225,100
          -122.0830,37.4220,100
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>110m Contour</name>
      <LineString>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
          -122.0840,37.4230,110
          -122.0835,37.4235,110
          -122.0830,37.4230,110
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "Created contours DXF" in result.output
            
            # Verify DXF structure
            doc = ezdxf.readfile(str(output_file))
            assert doc is not None
    
    def test_kml_contours_with_elevation_units(self):
        """Test KML contours conversion with different elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test with meters
            output_file1 = Path(temp_dir) / "contours_meters.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file1),
                '--elevation-units', 'meters'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with feet
            output_file2 = Path(temp_dir) / "contours_feet.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file2),
                '--elevation-units', 'feet'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_kml_contours_with_labels(self):
        """Test KML contours conversion with and without labels."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100 -122.06,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test with labels (default)
            output_file1 = Path(temp_dir) / "contours_with_labels.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file1),
                '--label'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test without labels
            output_file2 = Path(temp_dir) / "contours_no_labels.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file2),
                '--no-label'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_kml_contours_with_label_height(self):
        """Test KML contours conversion with custom label height."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            output_file = Path(temp_dir) / "contours_custom_label.dxf"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file),
                '--label',
                '--label-height', '10.0'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_kml_contours_with_translation(self):
        """Test KML contours conversion with and without translation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test with translation (default)
            output_file1 = Path(temp_dir) / "contours_translate.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file1),
                '--translate'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test without translation
            output_file2 = Path(temp_dir) / "contours_no_translate.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file2),
                '--no-translate'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_kml_contours_with_projection_options(self):
        """Test KML contours conversion with projection options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test with specific EPSG
            output_file1 = Path(temp_dir) / "contours_epsg.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file1),
                '--target-epsg', '26910'  # UTM Zone 10N
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with WGS84
            output_file2 = Path(temp_dir) / "contours_wgs84.dxf"
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file2),
                '--wgs84'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_kml_contours_with_extended_data(self):
        """Test KML contours with elevation in ExtendedData."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours_extended.kml"
            output_file = Path(temp_dir) / "contours_extended_output.dxf"
            
            # Create test KML with ExtendedData
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Contour Line</name>
      <ExtendedData>
        <Data name="elevation">
          <value>120</value>
        </Data>
      </ExtendedData>
      <LineString>
        <coordinates>-122.08,37.42,0 -122.07,37.42,0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_conflicting_projection_options(self):
        """Test error handling for conflicting projection options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            output_file = Path(temp_dir) / "output.dxf"
            
            # Create minimal KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test using both --target-epsg and --wgs84
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file),
                '--target-epsg', '26910',
                '--wgs84'
            ])
            
            assert result.exit_code != 0
            assert 'Cannot use both' in result.output
    
    def test_invalid_kml_file(self):
        """Test error handling for invalid KML files."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.dxf"
            
            # Test with nonexistent file
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                'nonexistent.kml',
                str(output_file)
            ])
            
            assert result.exit_code != 0
    
    def test_invalid_elevation_units(self):
        """Test error handling for invalid elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contours.kml"
            output_file = Path(temp_dir) / "output.dxf"
            
            # Create minimal KML
            input_file.write_text('<?xml version="1.0"?><kml></kml>')
            
            result = runner.invoke(cli, [
                'kml-contours-to-dxf',
                str(input_file),
                str(output_file),
                '--elevation-units', 'invalid_unit'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()


class TestKmlContoursToDxfCoreFunction:
    """Test cases for the core convert_kml_contours_to_dxf function."""
    
    def test_convert_kml_contours_basic(self):
        """Test basic KML contours conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test_contours.kml"
            output_file = Path(temp_dir) / "test_output.dxf"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100 -122.06,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test basic conversion
            convert_kml_contours_to_dxf(
                input_file=input_file,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify DXF content
            doc = ezdxf.readfile(str(output_file))
            assert doc is not None
    
    def test_convert_kml_contours_with_options(self):
        """Test KML contours conversion with various options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test_contours.kml"
            output_file = Path(temp_dir) / "test_output.dxf"
            
            # Create test KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-122.08,37.42,100 -122.07,37.42,100</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test with options
            convert_kml_contours_to_dxf(
                input_file=input_file,
                output_file=output_file,
                z_units='feet',
                add_labels=True,
                layer_prefix='CONTOUR_',
                decimals=2,
                translate_to_origin=False,
                label_height=8.0
            )
            
            assert output_file.exists()
    
    def test_convert_kml_contours_nonexistent_file(self):
        """Test error handling for nonexistent input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.dxf"
            
            with pytest.raises(FileNotFoundError, match="File not found"):
                convert_kml_contours_to_dxf(
                    input_file=Path("nonexistent.kml"),
                    output_file=output_file
                )
    
    def test_convert_kml_contours_invalid_parameters(self):
        """Test parameter validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test.kml"
            output_file = Path(temp_dir) / "output.dxf"
            
            # Create minimal KML
            input_file.write_text('<?xml version="1.0"?><kml></kml>')
            
            # Test invalid z_source
            with pytest.raises(ValueError, match="z_source must be"):
                convert_kml_contours_to_dxf(
                    input_file=input_file,
                    output_file=output_file,
                    z_source='invalid'
                )
            
            # Test invalid z_units
            with pytest.raises(ValueError, match="z_units must be"):
                convert_kml_contours_to_dxf(
                    input_file=input_file,
                    output_file=output_file,
                    z_units='invalid'
                )