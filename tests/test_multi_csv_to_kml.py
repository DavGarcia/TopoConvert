"""Tests for multiple CSV to KML conversion."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from xml.etree import ElementTree as ET

from topoconvert.cli import cli
from topoconvert.core.combined_kml import merge_csv_to_kml
from topoconvert.core.exceptions import TopoConvertError, ProcessingError


class TestMultiCsvToKmlCommand:
    """Test cases for multi-csv-to-kml command."""
    
    def test_command_exists(self):
        """Test that the multi-csv-to-kml command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['multi-csv-to-kml', '--help'])
        assert result.exit_code == 0
        assert 'Merge CSV files to KML with separate folders' in result.output
        assert 'Each CSV file is placed in its own KML folder' in result.output
    
    def test_command_arguments_and_options(self):
        """Test that all expected arguments and options are available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['multi-csv-to-kml', '--help'])
        assert result.exit_code == 0
        
        # Check required arguments
        assert 'CSV_FILES' in result.output
        
        # Check all options
        assert '--output' in result.output or '-o' in result.output
        assert '--add-labels / --no-labels' in result.output
        assert '--x-column' in result.output or '-x' in result.output
        assert '--y-column' in result.output or '-y' in result.output
        assert '--z-column' in result.output or '-z' in result.output
        assert '--elevation-units' in result.output
        assert '--point-scale' in result.output
    
    def test_basic_multi_csv_merge(self):
        """Test basic multiple CSV file merging to KML."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "merged_output.kml"
            
            # Check if we have test CSV files
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            # Skip if test data doesn't exist
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify KML file contains data from multiple folders
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            
            # Find folders (should have one for each CSV file)
            folders = root.findall('.//{http://www.opengis.net/kml/2.2}Folder')
            assert len(folders) >= 2, "Should have at least 2 folders for CSV files"
            
            # Check that folders have names matching CSV files
            folder_names = [folder.find('{http://www.opengis.net/kml/2.2}name').text 
                           for folder in folders]
            csv_stems = [f.stem for f in csv_files]
            for stem in csv_stems:
                assert stem in folder_names, f"Should have folder for {stem}"
    
    def test_merge_with_custom_columns(self):
        """Test CSV merging with custom column names."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "custom_columns.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with custom column names (using defaults which should work)
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file),
                '--x-column', 'Longitude',
                '--y-column', 'Latitude',
                '--z-column', 'Elevation'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_merge_with_elevation_units(self):
        """Test CSV merging with different elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with meters (default)
            output_file1 = Path(temp_dir) / "meters.kml"
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file1),
                '--elevation-units', 'meters'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with feet
            output_file2 = Path(temp_dir) / "feet.kml"
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file2),
                '--elevation-units', 'feet'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Elevations converted from feet to meters" in result.output
    
    def test_merge_with_label_options(self):
        """Test CSV merging with different label options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with labels enabled (default)
            output_file1 = Path(temp_dir) / "with_labels.kml"
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file1),
                '--add-labels'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with labels disabled
            output_file2 = Path(temp_dir) / "no_labels.kml"
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file2),
                '--no-labels'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_merge_with_point_scale(self):
        """Test CSV merging with custom point scale."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "scaled_points.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file),
                '--point-scale', '1.5'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify scale is applied in KML
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            scales = root.findall('.//{http://www.opengis.net/kml/2.2}scale')
            if scales:
                # Check that at least one scale element has the custom value
                scale_values = [scale.text for scale in scales]
                assert '1.5' in scale_values
    
    def test_merge_multiple_csv_files(self):
        """Test merging more than 2 CSV files."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "multi_merged.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv"),
                Path("testdata/test_points.csv")
            ]
            
            # Filter to only existing files
            existing_files = [f for f in csv_files if f.exists()]
            
            if len(existing_files) < 2:
                pytest.skip("Need at least 2 CSV test files")
            
            # Build command with multiple files
            cmd = ['multi-csv-to-kml'] + [str(f) for f in existing_files] + ['--output', str(output_file)]
            
            result = runner.invoke(cli, cmd)
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify folders correspond to number of input files
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            folders = root.findall('.//{http://www.opengis.net/kml/2.2}Folder')
            
            assert len(folders) == len(existing_files), f"Should have {len(existing_files)} folders"
    
    def test_folder_naming_and_styles(self):
        """Test that folders are named correctly and have different styles."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "styled_merge.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify folder naming and styles
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            
            # Check folders have names matching CSV stems
            folders = root.findall('.//{http://www.opengis.net/kml/2.2}Folder')
            folder_names = [folder.find('{http://www.opengis.net/kml/2.2}name').text for folder in folders]
            
            for csv_file in csv_files:
                assert csv_file.stem in folder_names, f"Should have folder named {csv_file.stem}"
            
            # Check that different styles exist
            styles = root.findall('.//{http://www.opengis.net/kml/2.2}Style')
            assert len(styles) >= 2, "Should have at least 2 different styles"
            
            # Check style IDs are different
            style_ids = [style.get('id') for style in styles]
            assert len(set(style_ids)) == len(style_ids), "All styles should have unique IDs"
    
    def test_point_data_preservation(self):
        """Test that point data and extended data are preserved."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "data_preservation.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify placemarks exist
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            
            placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
            assert len(placemarks) > 0, "Should contain placemark elements from CSV files"
            
            # Check that placemarks have coordinates
            coordinates = root.findall('.//{http://www.opengis.net/kml/2.2}coordinates')
            assert len(coordinates) > 0, "Should have coordinate elements"
            
            # Check for extended data
            extended_data = root.findall('.//{http://www.opengis.net/kml/2.2}ExtendedData')
            assert len(extended_data) > 0, "Should preserve extended data from CSV"
    
    def test_invalid_csv_files(self):
        """Test error handling for invalid CSV files."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "invalid_test.kml"
            
            # Test with nonexistent files
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                'nonexistent1.csv',
                'nonexistent2.csv',
                '--output', str(output_file)
            ])
            
            assert result.exit_code != 0
    
    def test_missing_output_option(self):
        """Test error handling when output option is missing."""
        runner = CliRunner()
        
        # Create temporary CSV files to avoid path issues
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal CSV files for the test
            csv1 = Path(temp_dir) / "test1.csv"
            csv2 = Path(temp_dir) / "test2.csv"
            
            csv_content = "Latitude,Longitude,Elevation\n40.7128,-74.0060,10\n"
            csv1.write_text(csv_content)
            csv2.write_text(csv_content)
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv1),
                str(csv2)
                # Missing --output option
            ])
            
            assert result.exit_code != 0
            assert 'Missing option' in result.output or 'required' in result.output.lower()
    
    def test_single_csv_file(self):
        """Test that command works with just one CSV file."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "single_csv.kml"
            
            csv_file = Path("testdata/survey_data_1.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_file),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify single folder was created
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            folders = root.findall('.//{http://www.opengis.net/kml/2.2}Folder')
            
            assert len(folders) == 1, "Should have exactly 1 folder"
    
    def test_invalid_elevation_units(self):
        """Test error handling for invalid elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "invalid_units.kml"
            
            csv_file = Path("testdata/survey_data_1.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_file),
                '--output', str(output_file),
                '--elevation-units', 'invalid_unit'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()
    
    def test_custom_column_names_with_missing_column(self):
        """Test error handling when specified columns don't exist."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "missing_column.kml"
            
            csv_file = Path("testdata/survey_data_1.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-kml',
                str(csv_file),
                '--output', str(output_file),
                '--x-column', 'NonexistentColumn'
            ])
            
            assert result.exit_code != 0
            assert 'Error:' in result.output


class TestMergeCsvToKmlCoreFunction:
    """Test cases for the core merge_csv_to_kml function."""
    
    def test_merge_csv_basic(self):
        """Test basic CSV merging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_merge.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test basic merge
            merge_csv_to_kml(
                csv_files=csv_files,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify content
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
            assert len(placemarks) > 0
    
    def test_merge_csv_with_elevation_units(self):
        """Test CSV merging with different elevation units."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_merge_units.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with feet elevation
            merge_csv_to_kml(
                csv_files=csv_files,
                output_file=output_file,
                elevation_units='feet'
            )
            
            assert output_file.exists()
    
    def test_merge_csv_with_custom_columns(self):
        """Test CSV merging with custom column names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_merge_columns.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with custom column names
            merge_csv_to_kml(
                csv_files=csv_files,
                output_file=output_file,
                x_column='Longitude',
                y_column='Latitude',
                z_column='Elevation'
            )
            
            assert output_file.exists()
    
    def test_merge_csv_parameter_validation(self):
        """Test parameter validation in CSV merging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_validation.kml"
            
            # Test empty CSV files list
            with pytest.raises(ProcessingError, match="No CSV files provided"):
                merge_csv_to_kml(
                    csv_files=[],
                    output_file=output_file
                )
    
    def test_merge_csv_missing_columns(self):
        """Test error handling for missing columns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_missing_cols.kml"
            
            csv_file = Path("testdata/survey_data_1.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file not found")
            
            # Test with nonexistent column
            with pytest.raises(ProcessingError, match="Column .* not found"):
                merge_csv_to_kml(
                    csv_files=[csv_file],
                    output_file=output_file,
                    x_column='NonexistentColumn'
                )
    
    def test_merge_csv_nonexistent_files(self):
        """Test error handling for nonexistent CSV files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_nonexistent.kml"
            
            csv_files = [
                Path("nonexistent1.csv"),
                Path("nonexistent2.csv")
            ]
            
            with pytest.raises(FileNotFoundError):
                merge_csv_to_kml(
                    csv_files=csv_files,
                    output_file=output_file
                )
    
    def test_merge_csv_labels_and_scale(self):
        """Test CSV merging with label and scale options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_labels_scale.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            merge_csv_to_kml(
                csv_files=csv_files,
                output_file=output_file,
                add_labels=False,
                point_scale=2.0
            )
            
            assert output_file.exists()
            
            # Verify options are applied
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            
            # Check for scale elements
            scales = root.findall('.//{http://www.opengis.net/kml/2.2}scale')
            if scales:
                scale_values = [scale.text for scale in scales]
                assert '2.0' in scale_values
    
    def test_merge_csv_kml_structure(self):
        """Test that generated KML has proper structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_structure.kml"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/test_points.csv")
            ]
            
            # Filter to existing files
            existing_files = [f for f in csv_files if f.exists()]
            
            if len(existing_files) < 1:
                pytest.skip("Need at least 1 CSV test file")
            
            merge_csv_to_kml(
                csv_files=existing_files,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify KML structure
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            
            # Check root element
            assert root.tag == '{http://www.opengis.net/kml/2.2}kml'
            
            # Check document
            document = root.find('{http://www.opengis.net/kml/2.2}Document')
            assert document is not None
            
            # Check document has name
            doc_name = document.find('{http://www.opengis.net/kml/2.2}name')
            assert doc_name is not None
            assert doc_name.text == output_file.stem
            
            # Check styles exist
            styles = document.findall('{http://www.opengis.net/kml/2.2}Style')
            assert len(styles) >= len(existing_files)
            
            # Check folders exist
            folders = document.findall('{http://www.opengis.net/kml/2.2}Folder')
            assert len(folders) == len(existing_files)
    
    def test_merge_csv_coordinate_conversion(self):
        """Test that coordinates are properly formatted in KML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_coordinates.kml"
            
            csv_file = Path("testdata/test_points.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file not found")
            
            merge_csv_to_kml(
                csv_files=[csv_file],
                output_file=output_file,
                elevation_units='meters'
            )
            
            assert output_file.exists()
            
            # Verify coordinate format
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            
            coordinates = root.findall('.//{http://www.opengis.net/kml/2.2}coordinates')
            assert len(coordinates) > 0
            
            # Check coordinate format (lon,lat,elevation)
            for coord in coordinates:
                coord_text = coord.text.strip()
                parts = coord_text.split(',')
                assert len(parts) == 3, "Coordinates should have lon,lat,elevation format"
                
                # Verify they're numeric
                try:
                    float(parts[0])  # longitude
                    float(parts[1])  # latitude
                    float(parts[2])  # elevation
                except ValueError:
                    pytest.fail("Coordinates should be numeric")