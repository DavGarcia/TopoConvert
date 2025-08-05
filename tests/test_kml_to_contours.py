"""Tests for KML to contours conversion."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from topoconvert.cli import cli
from topoconvert.core.contours import generate_contours
from topoconvert.core.exceptions import FileFormatError, ProcessingError


class TestKmlToContours:
    """Test cases for kml-to-contours command."""
    
    def test_command_exists(self):
        """Test that the kml-to-dxf-contours command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-to-dxf-contours', '--help'])
        assert result.exit_code == 0
        assert 'Convert KML points to DXF contours' in result.output
        assert '--interval' in result.output
        assert '--label' in result.output
        assert '--elevation-units' in result.output
        assert '--grid-resolution' in result.output
    
    def test_basic_conversion(self, grid_kml):
        """Test basic KML to contours conversion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify it's a valid DXF by checking file header
            with open(output_file, 'r') as f:
                content = f.read()
                assert '0\nSECTION' in content  # Basic DXF structure
    
    def test_custom_interval(self, grid_kml):
        """Test conversion with custom contour interval."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with 5-foot interval
            output_5ft = Path(temp_dir) / "contours_5ft.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_5ft),
                '--interval', '5.0'
            ])
            assert result.exit_code == 0
            assert output_5ft.exists()
            
            # Test with 0.5-foot interval
            output_half = Path(temp_dir) / "contours_half.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_half),
                '--interval', '0.5'
            ])
            assert result.exit_code == 0
            assert output_half.exists()
    
    def test_label_option(self, grid_kml):
        """Test conversion with and without labels."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with labels (default)
            output_with_labels = Path(temp_dir) / "with_labels.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_with_labels)
            ])
            assert result.exit_code == 0
            assert output_with_labels.exists()
            
            # Test without labels
            output_no_labels = Path(temp_dir) / "no_labels.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_no_labels),
                '--no-label'
            ])
            assert result.exit_code == 0
            assert output_no_labels.exists()
    
    def test_elevation_units(self, grid_kml):
        """Test conversion with different elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with meters
            output_meters = Path(temp_dir) / "contours_m.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_meters),
                '--elevation-units', 'meters'
            ])
            assert result.exit_code == 0
            assert output_meters.exists()
            
            # Test with feet
            output_feet = Path(temp_dir) / "contours_ft.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_feet),
                '--elevation-units', 'feet'
            ])
            assert result.exit_code == 0
            assert output_feet.exists()
    
    def test_grid_resolution(self, grid_kml):
        """Test conversion with different grid resolutions."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with low resolution (faster but rougher)
            output_low = Path(temp_dir) / "contours_low.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_low),
                '--grid-resolution', '50'
            ])
            assert result.exit_code == 0
            assert output_low.exists()
            
            # Test with high resolution (slower but smoother)
            output_high = Path(temp_dir) / "contours_high.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_high),
                '--grid-resolution', '200'
            ])
            assert result.exit_code == 0
            assert output_high.exists()
    
    def test_label_height_option(self, grid_kml):
        """Test conversion with custom label height."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours_label_height.dxf"
            
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_file),
                '--label-height', '5.0'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_translation_option(self, grid_kml):
        """Test conversion with translation disabled."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours_no_translate.dxf"
            
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_file),
                '--no-translate'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_projection_option(self, grid_kml):
        """Test conversion with specific projection."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours_utm.dxf"
            
            # Use UTM Zone 32N (Europe)
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(grid_kml),
                str(output_file),
                '--target-epsg', '32632'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_default_output_file(self, grid_kml):
        """Test default output filename generation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy KML to temp directory
            temp_kml = Path(temp_dir) / "test_grid.kml"
            temp_kml.write_text(grid_kml.read_text())
            
            # Run without specifying output file
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(temp_kml)
            ])
            
            assert result.exit_code == 0
            
            # Check default output file was created
            default_output = temp_kml.with_suffix('.dxf')
            assert default_output.exists()
    
    def test_invalid_input_file(self):
        """Test error handling for invalid input file."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-to-dxf-contours',
            'nonexistent.kml',
            'output.dxf'
        ])
        
        assert result.exit_code != 0
    
    def test_insufficient_points(self, simple_kml):
        """Test handling with minimal points."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            # Simple KML has only 3 points, which can still generate contours
            result = runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(simple_kml),
                str(output_file)
            ])
            
            # Should succeed but with limited contours
            assert result.exit_code == 0
            assert output_file.exists()
            assert 'Found 3 points' in result.output
    
    def test_invalid_interval(self, grid_kml):
        """Test error handling for invalid contour interval."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(grid_kml),
            'output.dxf',
            '--interval', '-1.0'  # Negative interval
        ])
        
        assert result.exit_code != 0


class TestGenerateContoursCoreFunction:
    """Test cases for the core generate_contours function."""
    
    def test_generate_contours_basic(self, grid_kml):
        """Test basic contour generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            generate_contours(
                input_file=grid_kml,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify it's a valid DXF
            with open(output_file, 'r') as f:
                content = f.read()
                assert '0\nSECTION' in content
                assert 'ENTITIES' in content
    
    def test_generate_contours_with_options(self, grid_kml):
        """Test contour generation with various options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours_options.dxf"
            
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                elevation_units='feet',
                contour_interval=2.5,
                grid_resolution=150,
                add_labels=True,
                label_height=3.0,
                translate_to_origin=False,
                target_epsg=32614  # UTM Zone 14N
            )
            
            assert output_file.exists()
    
    def test_generate_contours_no_labels(self, grid_kml):
        """Test contour generation without labels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours_no_labels.dxf"
            
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                add_labels=False
            )
            
            assert output_file.exists()
    
    def test_generate_contours_nonexistent_file(self):
        """Test error handling for nonexistent input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            with pytest.raises(FileNotFoundError, match="File not found"):
                generate_contours(
                    input_file=Path("nonexistent.kml"),
                    output_file=output_file
                )
    
    def test_generate_contours_invalid_parameters(self, grid_kml):
        """Test parameter validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            # Test invalid elevation units
            with pytest.raises(ValueError, match="elevation_units"):
                generate_contours(
                    input_file=grid_kml,
                    output_file=output_file,
                    elevation_units="invalid"
                )
            
            # Test invalid contour interval
            with pytest.raises(ValueError, match="contour_interval"):
                generate_contours(
                    input_file=grid_kml,
                    output_file=output_file,
                    contour_interval=-1.0
                )
            
            # Test invalid grid resolution
            with pytest.raises(ValueError, match="grid_resolution"):
                generate_contours(
                    input_file=grid_kml,
                    output_file=output_file,
                    grid_resolution=0
                )
    
    def test_generate_contours_empty_kml(self, empty_kml):
        """Test handling of empty KML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            with pytest.raises(ProcessingError, match="No points found"):
                generate_contours(
                    input_file=empty_kml,
                    output_file=output_file
                )
    
    def test_generate_contours_sparse_data(self, sparse_kml):
        """Test handling of sparse point data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours_sparse.dxf"
            
            # Should either succeed with limited contours or warn
            try:
                generate_contours(
                    input_file=sparse_kml,
                    output_file=output_file,
                    grid_resolution=50  # Lower resolution for sparse data
                )
                assert output_file.exists()
            except ProcessingError as e:
                # Acceptable if it fails due to insufficient data
                assert "insufficient" in str(e).lower() or "not enough" in str(e).lower()
    
    def test_generate_contours_progress_callback(self, grid_kml):
        """Test that progress callback is called during processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contours.dxf"
            
            progress_calls = []
            
            def progress_callback(message, percent):
                progress_calls.append((message, percent))
            
            generate_contours(
                input_file=grid_kml,
                output_file=output_file,
                progress_callback=progress_callback
            )
            
            # Verify progress was reported
            assert len(progress_calls) > 0
            # Check that progress went from 0 to 100
            assert any(p[1] == 0 for p in progress_calls)
            assert any(p[1] == 100 for p in progress_calls)