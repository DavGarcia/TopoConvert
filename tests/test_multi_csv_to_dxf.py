"""Tests for multiple CSV to DXF conversion."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import ezdxf

from topoconvert.cli import cli
from topoconvert.core.combined_dxf import merge_csv_to_dxf
from topoconvert.core.exceptions import TopoConvertError, FileFormatError, ProcessingError


class TestMultiCsvToDxfCommand:
    """Test cases for multi-csv-to-dxf command."""
    
    def test_command_exists(self):
        """Test that the multi-csv-to-dxf command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['multi-csv-to-dxf', '--help'])
        assert result.exit_code == 0
        assert 'Merge CSV files to DXF with separate layers' in result.output
        assert 'Each CSV file is placed on its own layer' in result.output
    
    def test_command_arguments_and_options(self):
        """Test that all expected arguments and options are available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['multi-csv-to-dxf', '--help'])
        assert result.exit_code == 0
        
        # Check required arguments
        assert 'CSV_FILES' in result.output
        
        # Check all options
        assert '--output' in result.output or '-o' in result.output
        assert '--target-epsg' in result.output
        assert '--wgs84' in result.output
    
    def test_basic_multi_csv_merge(self):
        """Test basic multiple CSV file merging."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "merged_output.dxf"
            
            # Check if we have test CSV files
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            # Skip if test data doesn't exist
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify DXF file contains data from multiple layers
            doc = ezdxf.readfile(str(output_file))
            
            # Should have multiple layers (one for each CSV file)
            layers = list(doc.layers)
            layer_names = [layer.dxf.name for layer in layers]
            
            # Should have layers for each CSV file (plus default layers)
            csv_layers = [name for name in layer_names if '_POINTS' in name]
            assert len(csv_layers) >= 2, "Should have at least 2 CSV-specific layers"
    
    def test_merge_with_projection_options(self):
        """Test CSV merging with different projection options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with specific EPSG code
            output_file1 = Path(temp_dir) / "merged_epsg.dxf"
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file1),
                '--target-epsg', '26914'  # NAD83 / UTM Zone 14N
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with WGS84 option
            output_file2 = Path(temp_dir) / "merged_wgs84.dxf"
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file2),
                '--wgs84'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_merge_multiple_csv_files(self):
        """Test merging multiple CSV files (more than 2)."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "multi_merged.dxf"
            
            # Use CSV files that have the correct format (Latitude, Longitude, Elevation)
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv"),
                Path("testdata/test_points.csv")
                # Note: boundary_points.csv doesn't have Elevation column
            ]
            
            # Filter to only existing files
            existing_files = [f for f in csv_files if f.exists()]
            
            if len(existing_files) < 2:
                pytest.skip("Need at least 2 CSV test files")
            
            # Build command with multiple files
            cmd = ['multi-csv-to-dxf'] + [str(f) for f in existing_files] + ['--output', str(output_file)]
            
            result = runner.invoke(cli, cmd)
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify layers correspond to number of input files
            doc = ezdxf.readfile(str(output_file))
            layer_names = [layer.dxf.name for layer in doc.layers]
            csv_layers = [name for name in layer_names if '_POINTS' in name]
            
            assert len(csv_layers) == len(existing_files), f"Should have {len(existing_files)} CSV layers"
    
    def test_layer_naming_and_colors(self):
        """Test that layers are named correctly and have different colors."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "colored_merge.dxf"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify layer naming and colors
            doc = ezdxf.readfile(str(output_file))
            layers = list(doc.layers)
            
            csv_layers = [layer for layer in layers if '_POINTS' in layer.dxf.name]
            
            # Check that layers have different colors
            colors = [layer.dxf.color for layer in csv_layers]
            assert len(set(colors)) == len(csv_layers), "Each layer should have a unique color"
            
            # Check layer naming pattern
            for layer in csv_layers:
                assert layer.dxf.name.endswith('_POINTS'), "CSV layers should end with '_POINTS'"
    
    def test_point_data_preservation(self):
        """Test that point data from all CSV files is preserved."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "data_preservation.dxf"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify points exist in the DXF
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            
            points = list(msp.query('POINT'))
            assert len(points) > 0, "Should contain point entities from CSV files"
    
    def test_conflicting_projection_options(self):
        """Test error handling for conflicting projection options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "conflict_test.dxf"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test using both --target-epsg and --wgs84 (should fail)
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file),
                '--target-epsg', '26914',
                '--wgs84'
            ])
            
            assert result.exit_code != 0
            assert 'Cannot use both' in result.output or 'mutually exclusive' in result.output.lower()
    
    def test_invalid_csv_files(self):
        """Test error handling for invalid CSV files."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "invalid_test.dxf"
            
            # Test with nonexistent files
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                'nonexistent1.csv',
                'nonexistent2.csv',
                '--output', str(output_file)
            ])
            
            assert result.exit_code != 0
    
    def test_missing_output_option(self):
        """Test error handling when output option is missing."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'multi-csv-to-dxf',
            'testdata/survey_data_1.csv',
            'testdata/survey_data_2.csv'
            # Missing --output option
        ])
        
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()
    
    def test_single_csv_file(self):
        """Test that command works with just one CSV file."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "single_csv.dxf"
            
            csv_file = Path("testdata/survey_data_1.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_file),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify single layer was created
            doc = ezdxf.readfile(str(output_file))
            layer_names = [layer.dxf.name for layer in doc.layers]
            csv_layers = [name for name in layer_names if '_POINTS' in name]
            
            assert len(csv_layers) == 1, "Should have exactly 1 CSV layer"
    
    def test_csv_without_elevation(self):
        """Test CSV files without elevation column (should default to 0.0)."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "no_elevation.dxf"
            
            # boundary_points.csv doesn't have elevation column
            csv_file = Path("testdata/boundary_points.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file boundary_points.csv not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_file),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "(elevation set to 0.0)" in result.output
            
            # Verify points were created at Z=0
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            points = list(msp.query('POINT'))
            
            # All points should have Z coordinate near 0 (after translation)
            for point in points:
                assert abs(point.dxf.location.z) < 1.0, "Points without elevation should be at Z≈0"
    
    def test_mixed_elevation_files(self):
        """Test mixing CSV files with and without elevation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "mixed_elevation.dxf"
            
            csv_files = [
                Path("testdata/boundary_points.csv"),  # No elevation
                Path("testdata/survey_data_1.csv")     # Has elevation
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            result = runner.invoke(cli, [
                'multi-csv-to-dxf',
                str(csv_files[0]),
                str(csv_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify output messages
            assert "(elevation set to 0.0)" in result.output
            assert "(with elevation)" in result.output
            
            # Verify both layers were created
            doc = ezdxf.readfile(str(output_file))
            layer_names = [layer.dxf.name for layer in doc.layers]
            csv_layers = [name for name in layer_names if '_POINTS' in name]
            
            assert len(csv_layers) == 2, "Should have 2 CSV layers"


class TestMergeCsvToDxfCoreFunction:
    """Test cases for the core merge_csv_to_dxf function."""
    
    def test_merge_csv_basic(self):
        """Test basic CSV merging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_merge.dxf"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test basic merge
            merge_csv_to_dxf(
                csv_files=csv_files,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify content
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            points = list(msp.query('POINT'))
            assert len(points) > 0
    
    def test_merge_csv_with_projection(self):
        """Test CSV merging with projection options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_merge_proj.dxf"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            # Test with specific EPSG
            merge_csv_to_dxf(
                csv_files=csv_files,
                output_file=output_file,
                target_epsg=26914
            )
            
            assert output_file.exists()
            
            # Test with WGS84
            output_file2 = Path(temp_dir) / "test_merge_wgs84.dxf"
            merge_csv_to_dxf(
                csv_files=csv_files,
                output_file=output_file2,
                wgs84=True
            )
            
            assert output_file2.exists()
    
    def test_merge_csv_parameter_validation(self):
        """Test parameter validation in CSV merging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_validation.dxf"
            
            # Test empty CSV files list
            with pytest.raises(ValueError, match="At least one CSV file is required"):
                merge_csv_to_dxf(
                    csv_files=[],
                    output_file=output_file
                )
    
    def test_merge_csv_without_elevation(self):
        """Test merging CSV files without elevation columns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_no_elevation.dxf"
            
            csv_file = Path("testdata/boundary_points.csv")
            
            if not csv_file.exists():
                pytest.skip("Test CSV data file boundary_points.csv not found")
            
            # Should work without elevation column
            merge_csv_to_dxf(
                csv_files=[csv_file],
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify points exist
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            points = list(msp.query('POINT'))
            assert len(points) > 0
    
    def test_merge_csv_nonexistent_files(self):
        """Test error handling for nonexistent CSV files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_nonexistent.dxf"
            
            csv_files = [
                Path("nonexistent1.csv"),
                Path("nonexistent2.csv")
            ]
            
            with pytest.raises((FileNotFoundError, ProcessingError)):
                merge_csv_to_dxf(
                    csv_files=csv_files,
                    output_file=output_file
                )
    
    def test_merge_csv_coordinate_translation(self):
        """Test that coordinates are properly translated to origin."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_translation.dxf"
            
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv")
            ]
            
            if not all(f.exists() for f in csv_files):
                pytest.skip("Test CSV data files not found")
            
            merge_csv_to_dxf(
                csv_files=csv_files,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify points have been translated (should start near origin)
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            points = list(msp.query('POINT'))
            
            if points:
                # Check that at least some points are near the origin
                min_x = min(point.dxf.location.x for point in points)
                min_y = min(point.dxf.location.y for point in points)
                
                # After translation, minimum coordinates should be close to 0
                assert min_x < 1000, "X coordinates should be translated closer to origin"
                assert min_y < 1000, "Y coordinates should be translated closer to origin"
    
    def test_merge_csv_layer_colors(self):
        """Test that different CSV files get different layer colors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_colors.dxf"
            
            # Use CSV files with correct format (Latitude, Longitude, Elevation)
            csv_files = [
                Path("testdata/survey_data_1.csv"),
                Path("testdata/survey_data_2.csv"),
                Path("testdata/test_points.csv")
            ]
            
            # Filter to existing files
            existing_files = [f for f in csv_files if f.exists()]
            
            if len(existing_files) < 2:
                pytest.skip("Need at least 2 CSV test files")
            
            merge_csv_to_dxf(
                csv_files=existing_files,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify layer colors are different
            doc = ezdxf.readfile(str(output_file))
            layers = list(doc.layers)
            csv_layers = [layer for layer in layers if '_POINTS' in layer.dxf.name]
            
            colors = [layer.dxf.color for layer in csv_layers]
            unique_colors = set(colors)
            
            assert len(unique_colors) == len(csv_layers), "Each CSV should have a unique layer color"