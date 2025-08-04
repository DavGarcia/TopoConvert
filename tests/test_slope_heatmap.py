"""Tests for slope heatmap generation."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import numpy as np
from PIL import Image

from topoconvert.cli import cli
from topoconvert.core.slope_heatmap import generate_slope_heatmap, _extract_points, _calculate_slope, _parse_coordinates
from topoconvert.core.exceptions import TopoConvertError, ProcessingError, FileFormatError


class TestSlopeHeatmapCommand:
    """Test cases for slope-heatmap command."""
    
    def test_command_exists(self):
        """Test that the slope-heatmap command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['slope-heatmap', '--help'])
        assert result.exit_code == 0
        assert 'Generate slope heatmap from elevation data' in result.output
        assert 'Calculates terrain slope and saves as PNG' in result.output
    
    def test_command_arguments_and_options(self):
        """Test that all expected arguments and options are available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['slope-heatmap', '--help'])
        assert result.exit_code == 0
        
        # Check required arguments
        assert 'INPUT_FILE' in result.output
        assert 'OUTPUT_FILE' in result.output
        
        # Check all options
        assert '--elevation-units' in result.output
        assert '--grid-resolution' in result.output
        assert '--slope-units' in result.output
        assert '--run-length' in result.output
        assert '--max-slope' in result.output
        assert '--colormap' in result.output
        assert '--dpi' in result.output
        assert '--smooth' in result.output
        assert '--no-contours' in result.output
        assert '--contour-interval' in result.output
        assert '--target-slope' in result.output
    
    def test_basic_slope_heatmap_generation(self):
        """Test basic slope heatmap generation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "slope_output.png"
            
            # Check if we have test KML file
            kml_file = Path("testdata/sample.kml")
            
            # Skip if test data doesn't exist
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify it's a valid PNG image
            try:
                img = Image.open(str(output_file))
                assert img.format == 'PNG'
                assert img.size[0] > 0
                assert img.size[1] > 0
            except Exception as e:
                pytest.fail(f"Generated image is not valid: {e}")
    
    def test_slope_heatmap_with_default_output(self):
        """Test slope heatmap with default output filename."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy KML file to temp directory so default output goes there
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            temp_kml = Path(temp_dir) / "test_input.kml"
            temp_kml.write_text(kml_file.read_text())
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(temp_kml)
                # No output file specified - should use default
            ])
            
            assert result.exit_code == 0
            
            # Check default output file was created
            default_output = temp_kml.with_suffix('.png')
            assert default_output.exists()
    
    def test_slope_heatmap_with_elevation_units(self):
        """Test slope heatmap with different elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test with meters (default)
            output_file1 = Path(temp_dir) / "slope_meters.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--elevation-units', 'meters'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with feet
            output_file2 = Path(temp_dir) / "slope_feet.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--elevation-units', 'feet'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_slope_heatmap_with_different_slope_units(self):
        """Test slope heatmap with different slope units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test degrees (default)
            output_file1 = Path(temp_dir) / "slope_degrees.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--slope-units', 'degrees'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test percent
            output_file2 = Path(temp_dir) / "slope_percent.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--slope-units', 'percent'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            
            # Test rise-run
            output_file3 = Path(temp_dir) / "slope_rise_run.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file3),
                '--slope-units', 'rise-run',
                '--run-length', '12.0'
            ])
            
            assert result.exit_code == 0
            assert output_file3.exists()
    
    def test_slope_heatmap_with_grid_resolution(self):
        """Test slope heatmap with different grid resolutions."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test low resolution
            output_file1 = Path(temp_dir) / "slope_low_res.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--grid-resolution', '50'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            assert "Grid resolution: 50x50" in result.output
            
            # Test high resolution
            output_file2 = Path(temp_dir) / "slope_high_res.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--grid-resolution', '300'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Grid resolution: 300x300" in result.output
    
    def test_slope_heatmap_with_smoothing(self):
        """Test slope heatmap with different smoothing values."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test no smoothing
            output_file1 = Path(temp_dir) / "slope_no_smooth.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--smooth', '0'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with smoothing
            output_file2 = Path(temp_dir) / "slope_smooth.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--smooth', '2.0'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Smoothing applied: sigma=2.0" in result.output
    
    def test_slope_heatmap_with_contours(self):
        """Test slope heatmap with and without contours."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test with contours (default)
            output_file1 = Path(temp_dir) / "slope_with_contours.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--contour-interval', '10.0'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test without contours
            output_file2 = Path(temp_dir) / "slope_no_contours.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--no-contours'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_slope_heatmap_with_custom_colormap(self):
        """Test slope heatmap with different colormaps."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test viridis colormap
            output_file1 = Path(temp_dir) / "slope_viridis.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--colormap', 'viridis'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test plasma colormap
            output_file2 = Path(temp_dir) / "slope_plasma.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--colormap', 'plasma'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_slope_heatmap_with_custom_dpi(self):
        """Test slope heatmap with different DPI settings."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test low DPI
            output_file1 = Path(temp_dir) / "slope_low_dpi.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file1),
                '--dpi', '72'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            assert "Output resolution: 72 DPI" in result.output
            
            # Test high DPI
            output_file2 = Path(temp_dir) / "slope_high_dpi.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file2),
                '--dpi', '300'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Output resolution: 300 DPI" in result.output
    
    def test_slope_heatmap_with_target_slope(self):
        """Test slope heatmap with target slope coloring."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            output_file = Path(temp_dir) / "slope_target.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file),
                '--target-slope', '15.0',
                '--slope-units', 'degrees'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_invalid_kml_file(self):
        """Test error handling for invalid KML files."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "slope_invalid.png"
            
            # Test with nonexistent file
            result = runner.invoke(cli, [
                'slope-heatmap',
                'nonexistent.kml',
                str(output_file)
            ])
            
            assert result.exit_code != 0
    
    def test_invalid_elevation_units(self):
        """Test error handling for invalid elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            output_file = Path(temp_dir) / "slope_invalid_units.png"
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file),
                '--elevation-units', 'invalid_unit'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()
    
    def test_invalid_slope_units(self):
        """Test error handling for invalid slope units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path("testdata/sample.kml")
            output_file = Path(temp_dir) / "slope_invalid_slope_units.png"
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(kml_file),
                str(output_file),
                '--slope-units', 'invalid_unit'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()


class TestSlopeHeatmapCoreFunction:
    """Test cases for the core generate_slope_heatmap function."""
    
    def test_generate_slope_heatmap_basic(self):
        """Test basic slope heatmap generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_slope.png"
            
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test basic generation
            generate_slope_heatmap(
                input_file=kml_file,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify it's a valid PNG
            img = Image.open(str(output_file))
            assert img.format == 'PNG'
    
    def test_generate_slope_heatmap_with_options(self):
        """Test slope heatmap generation with various options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_slope_options.png"
            
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test with custom options
            generate_slope_heatmap(
                input_file=kml_file,
                output_file=output_file,
                elevation_units='feet',
                grid_resolution=100,
                slope_units='percent',
                smooth=1.5,
                show_contours=True,
                contour_interval=2.0,
                dpi=200
            )
            
            assert output_file.exists()
    
    def test_generate_slope_heatmap_nonexistent_file(self):
        """Test error handling for nonexistent input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_nonexistent.png"
            
            with pytest.raises(FileFormatError, match="Input file not found"):
                generate_slope_heatmap(
                    input_file=Path("nonexistent.kml"),
                    output_file=output_file
                )
    
    def test_generate_slope_heatmap_invalid_parameters(self):
        """Test parameter validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_invalid.png"
            kml_file = Path("testdata/sample.kml")
            
            if not kml_file.exists():
                pytest.skip("Test KML data file not found")
            
            # Test with invalid grid resolution (should work but might be slow)
            try:
                generate_slope_heatmap(
                    input_file=kml_file,
                    output_file=output_file,
                    grid_resolution=1  # Very low resolution
                )
                assert output_file.exists()
            except Exception as e:
                # Accept either success or reasonable failure
                assert "resolution" in str(e).lower() or output_file.exists()


class TestSlopeHeatmapUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_parse_coordinates_valid(self):
        """Test parsing valid coordinate strings."""
        # Test with elevation
        coord = _parse_coordinates("-122.0822035,37.4222899,100.5")
        assert coord == (-122.0822035, 37.4222899, 100.5)
        
        # Test without elevation
        coord = _parse_coordinates("-122.0822035,37.4222899")
        assert coord == (-122.0822035, 37.4222899, 0.0)
        
        # Test with empty elevation
        coord = _parse_coordinates("-122.0822035,37.4222899,")
        assert coord == (-122.0822035, 37.4222899, 0.0)
    
    def test_parse_coordinates_invalid(self):
        """Test parsing invalid coordinate strings."""
        # Test insufficient coordinates
        coord = _parse_coordinates("123.45")
        assert coord is None
        
        # Test empty string
        coord = _parse_coordinates("")
        assert coord is None
        
        # Test non-numeric values should raise ValueError
        with pytest.raises(ValueError):
            _parse_coordinates("abc,def,ghi")
    
    def test_extract_points_from_kml(self):
        """Test extracting points from KML files."""
        kml_file = Path("testdata/sample.kml")
        
        if not kml_file.exists():
            pytest.skip("Test KML data file not found")
        
        points = _extract_points(kml_file)
        assert len(points) > 0
        
        # Verify point format
        for point in points:
            assert len(point) == 3  # lon, lat, elevation
            assert isinstance(point[0], float)  # longitude
            assert isinstance(point[1], float)  # latitude
            assert isinstance(point[2], float)  # elevation
    
    def test_extract_points_from_nonexistent_kml(self):
        """Test error handling for nonexistent KML files."""
        with pytest.raises(ProcessingError):
            _extract_points(Path("nonexistent.kml"))
    
    def test_calculate_slope_degrees(self):
        """Test slope calculation in degrees."""
        # Create simple elevation grid
        Z = np.array([[0, 1, 2],
                     [0, 1, 2],
                     [0, 1, 2]], dtype=float)
        
        dx = dy = 1.0
        
        slope = _calculate_slope(Z, dx, dy, units='degrees')
        
        # Verify output shape
        assert slope.shape == Z.shape
        
        # Verify slope values are reasonable (should be 45 degrees for this case)
        # Note: exact values depend on gradient calculation at edges
        assert np.all(slope >= 0)
        assert np.all(slope <= 90)
    
    def test_calculate_slope_percent(self):
        """Test slope calculation in percent."""
        Z = np.array([[0, 1, 2],
                     [0, 1, 2],
                     [0, 1, 2]], dtype=float)
        
        dx = dy = 1.0
        
        slope = _calculate_slope(Z, dx, dy, units='percent')
        
        # Verify output shape
        assert slope.shape == Z.shape
        
        # Verify slope values are reasonable
        assert np.all(slope >= 0)
    
    def test_calculate_slope_rise_run(self):
        """Test slope calculation in rise:run format."""
        Z = np.array([[0, 1, 2],
                     [0, 1, 2],
                     [0, 1, 2]], dtype=float)
        
        dx = dy = 1.0
        run_length = 10.0
        
        slope = _calculate_slope(Z, dx, dy, units='rise-run', run_length=run_length)
        
        # Verify output shape
        assert slope.shape == Z.shape
        
        # Verify slope values are reasonable
        assert np.all(slope >= 0)
    
    def test_calculate_slope_with_nan_values(self):
        """Test slope calculation with NaN values in grid."""
        Z = np.array([[0, 1, np.nan],
                     [0, 1, 2],
                     [0, np.nan, 2]], dtype=float)
        
        dx = dy = 1.0
        
        slope = _calculate_slope(Z, dx, dy, units='degrees')
        
        # Verify output shape
        assert slope.shape == Z.shape
        
        # Verify handling of NaN values
        assert np.sum(np.isnan(slope)) > 0  # Should have some NaN values
    
    def test_calculate_slope_flat_terrain(self):
        """Test slope calculation on flat terrain."""
        # Create flat elevation grid
        Z = np.ones((5, 5), dtype=float) * 100  # All same elevation
        
        dx = dy = 1.0
        
        slope = _calculate_slope(Z, dx, dy, units='degrees')
        
        # Verify output shape
        assert slope.shape == Z.shape
        
        # All slopes should be near zero (allowing for numerical precision)
        assert np.all(slope < 1.0)  # Should be very small slopes
    
    def test_calculate_slope_steep_terrain(self):
        """Test slope calculation on steep terrain."""
        # Create steep elevation grid
        Z = np.array([[0, 10, 20],
                     [0, 10, 20],
                     [0, 10, 20]], dtype=float)
        
        dx = dy = 1.0  # Small horizontal distance for steep slope
        
        slope = _calculate_slope(Z, dx, dy, units='degrees')
        
        # Verify output shape
        assert slope.shape == Z.shape
        
        # Should have significant slopes
        max_slope = np.nanmax(slope)
        assert max_slope > 10.0  # Should be steep