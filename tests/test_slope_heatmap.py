"""Tests for slope heatmap generation."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import numpy as np
from PIL import Image

from topoconvert.cli import cli
from topoconvert.core.slope_heatmap import generate_slope_heatmap, _extract_points, _calculate_slope, _parse_coordinates, _create_target_colormap
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
    
    def test_basic_slope_heatmap_generation(self, simple_kml):
        """Test basic slope heatmap generation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "slope_output.png"
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(simple_kml),
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
    
    def test_slope_heatmap_with_default_output(self, simple_kml):
        """Test slope heatmap with default output filename."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy KML file to temp directory so default output goes there
            temp_kml = Path(temp_dir) / "test_input.kml"
            temp_kml.write_text(simple_kml.read_text())
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(temp_kml)
                # No output file specified - should use default
            ])
            
            assert result.exit_code == 0
            
            # Check default output file was created
            default_output = temp_kml.with_suffix('.png')
            assert default_output.exists()
    
    def test_slope_heatmap_with_elevation_units(self, grid_kml):
        """Test slope heatmap with different elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with meters (default)
            output_file1 = Path(temp_dir) / "slope_meters.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file1),
                '--elevation-units', 'meters'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with feet
            output_file2 = Path(temp_dir) / "slope_feet.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file2),
                '--elevation-units', 'feet'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_slope_heatmap_with_different_slope_units(self, grid_kml):
        """Test slope heatmap with different slope units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test degrees (default)
            output_file1 = Path(temp_dir) / "slope_degrees.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file1),
                '--slope-units', 'degrees'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test percent
            output_file2 = Path(temp_dir) / "slope_percent.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file2),
                '--slope-units', 'percent'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            
            # Test rise-run
            output_file3 = Path(temp_dir) / "slope_rise_run.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file3),
                '--slope-units', 'rise-run',
                '--run-length', '12.0'
            ])
            
            assert result.exit_code == 0
            assert output_file3.exists()
    
    def test_slope_heatmap_with_grid_resolution(self, grid_kml):
        """Test slope heatmap with different grid resolutions."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test low resolution
            output_file1 = Path(temp_dir) / "slope_low_res.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
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
                str(grid_kml),
                str(output_file2),
                '--grid-resolution', '300'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Grid resolution: 300x300" in result.output
    
    def test_slope_heatmap_with_smoothing(self, grid_kml):
        """Test slope heatmap with different smoothing values."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test no smoothing
            output_file1 = Path(temp_dir) / "slope_no_smooth.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file1),
                '--smooth', '0'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with smoothing
            output_file2 = Path(temp_dir) / "slope_smooth.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file2),
                '--smooth', '2.0'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Smoothing applied: sigma=2.0" in result.output
    
    def test_slope_heatmap_with_contours(self, grid_kml):
        """Test slope heatmap with and without contours."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with contours (default)
            output_file1 = Path(temp_dir) / "slope_with_contours.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file1),
                '--contour-interval', '10.0'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test without contours
            output_file2 = Path(temp_dir) / "slope_no_contours.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file2),
                '--no-contours'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_slope_heatmap_with_custom_colormap(self, grid_kml):
        """Test slope heatmap with different colormaps."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test viridis colormap
            output_file1 = Path(temp_dir) / "slope_viridis.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file1),
                '--colormap', 'viridis'
            ])
            
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test plasma colormap
            output_file2 = Path(temp_dir) / "slope_plasma.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
                str(output_file2),
                '--colormap', 'plasma'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_slope_heatmap_with_custom_dpi(self, grid_kml):
        """Test slope heatmap with different DPI settings."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test low DPI
            output_file1 = Path(temp_dir) / "slope_low_dpi.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
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
                str(grid_kml),
                str(output_file2),
                '--dpi', '300'
            ])
            
            assert result.exit_code == 0
            assert output_file2.exists()
            assert "Output resolution: 300 DPI" in result.output
    
    def test_slope_heatmap_with_target_slope(self, grid_kml):
        """Test slope heatmap with target slope coloring."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "slope_target.png"
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(grid_kml),
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
    
    def test_invalid_elevation_units(self, simple_kml):
        """Test error handling for invalid elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "slope_invalid_units.png"
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(simple_kml),
                str(output_file),
                '--elevation-units', 'invalid_unit'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()
    
    def test_invalid_slope_units(self, simple_kml):
        """Test error handling for invalid slope units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "slope_invalid_slope_units.png"
            
            result = runner.invoke(cli, [
                'slope-heatmap',
                str(simple_kml),
                str(output_file),
                '--slope-units', 'invalid_unit'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()


class TestSlopeHeatmapCoreFunction:
    """Test cases for the core generate_slope_heatmap function."""
    
    def test_generate_slope_heatmap_basic(self, simple_kml):
        """Test basic slope heatmap generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_slope.png"
            
            # Test basic generation
            generate_slope_heatmap(
                input_file=simple_kml,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify it's a valid PNG
            img = Image.open(str(output_file))
            assert img.format == 'PNG'
    
    def test_generate_slope_heatmap_with_options(self, grid_kml):
        """Test slope heatmap generation with various options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_slope_options.png"
            
            # Test with custom options
            generate_slope_heatmap(
                input_file=grid_kml,
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
    
    def test_generate_slope_heatmap_invalid_parameters(self, simple_kml):
        """Test parameter validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_invalid.png"
            
            # Test with invalid grid resolution (should raise ValueError)
            with pytest.raises(ValueError, match="Grid resolution must be positive"):
                generate_slope_heatmap(
                    input_file=simple_kml,
                    output_file=output_file,
                    grid_resolution=0  # Invalid: zero resolution
                )


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
    
    def test_extract_points_from_kml(self, simple_kml):
        """Test extracting points from KML files."""
        points = _extract_points(simple_kml)
        assert len(points) == 3  # We know simple_kml has 3 points
        
        # Verify point format
        for point in points:
            assert len(point) == 3  # lon, lat, elevation
            assert isinstance(point[0], float)  # longitude
            assert isinstance(point[1], float)  # latitude
            assert isinstance(point[2], float)  # elevation
        
        # Verify specific values from our test file
        assert points[0] == (-122.0, 37.0, 100.0)
        assert points[1] == (-122.001, 37.0, 110.0)
        assert points[2] == (-122.0, 37.001, 120.0)
    
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


class TestSlopeComputationFunctions:
    """Test cases for pure computation functions (matplotlib-independent)."""
    
    def test_compute_slope_from_points_basic(self):
        """Test basic slope computation from points."""
        from topoconvert.core.slope_heatmap import compute_slope_from_points
        
        points = [
            (-122.0, 37.0, 100.0),  # 100 meters
            (-122.001, 37.0, 101.0),  # 101 meters
            (-122.0, 37.001, 102.0),  # 102 meters
        ]
        
        # Test meters (should convert to feet internally)
        result_m = compute_slope_from_points(
            points=points,
            elevation_units='meters'
        )
        
        # Verify result structure
        assert 'slope_grid' in result_m
        assert 'elevation_grid' in result_m
        assert 'x_coords' in result_m
        assert 'y_coords' in result_m
        assert 'slope_stats' in result_m
        assert result_m['slope_grid'].shape[0] > 0
        assert result_m['slope_grid'].shape[1] > 0
    
    def test_compute_slope_from_points_with_smoothing(self):
        """Test computation with gaussian smoothing."""
        from topoconvert.core.slope_heatmap import compute_slope_from_points
        
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 150.0),  # Sharp elevation change
            (-122.0, 37.001, 110.0),
            (-122.001, 37.001, 160.0),
        ]
        
        # Without smoothing
        result_no_smooth = compute_slope_from_points(
            points=points,
            smooth=0.0
        )
        
        # With smoothing
        result_smooth = compute_slope_from_points(
            points=points,
            smooth=2.0
        )
        
        # Smoothed result should have different (typically lower) max slope
        assert result_smooth['slope_grid'].shape == result_no_smooth['slope_grid'].shape
        # The exact relationship depends on the data, but they should be different
        smooth_max = np.nanmax(result_smooth['slope_grid'])
        no_smooth_max = np.nanmax(result_no_smooth['slope_grid'])
        # With smoothing, max slope is typically lower
        assert smooth_max <= no_smooth_max
    
    def test_compute_slope_from_points_insufficient_data(self):
        """Test error handling for insufficient points."""
        from topoconvert.core.slope_heatmap import compute_slope_from_points
        from topoconvert.core.exceptions import ProcessingError
        
        # Too few points
        points = [
            (-122.0, 37.0, 100.0),
            (-122.001, 37.0, 110.0),
        ]  # Only 2 points
        
        with pytest.raises(ProcessingError, match="Need at least 3 points"):
            compute_slope_from_points(points=points)
    
    def test_compute_slope_from_points_empty_data(self):
        """Test error handling for empty points."""
        from topoconvert.core.slope_heatmap import compute_slope_from_points
        from topoconvert.core.exceptions import ProcessingError
        
        with pytest.raises(ProcessingError, match="No points provided"):
            compute_slope_from_points(points=[])
    
    def test_compute_slope_from_points_synthetic_patterns(self):
        """Test computation with known slope patterns."""
        from topoconvert.core.slope_heatmap import compute_slope_from_points
        
        # Create a simple inclined plane (should have uniform slope)
        points = []
        for i in range(5):
            for j in range(5):
                lon = -122.0 + i * 0.001
                lat = 37.0 + j * 0.001
                elev = 100.0 + i * 10.0 + j * 5.0  # Linear elevation increase
                points.append((lon, lat, elev))
        
        result = compute_slope_from_points(
            points=points,
            grid_resolution=20,
            slope_units='degrees'
        )
        
        # For a linear incline, slopes should be relatively uniform
        valid_slopes = result['slope_grid'][~np.isnan(result['slope_grid'])]
        if len(valid_slopes) > 0:
            slope_std = np.std(valid_slopes)
            # Standard deviation should be reasonable for uniform slope
            # (allowing for edge effects and interpolation artifacts)
            assert slope_std < 20.0  # Degrees


class TestTargetColormap:
    """Test cases for target colormap functionality."""
    
    def test_create_target_colormap_returns_tuple(self):
        """Test that _create_target_colormap returns (colormap, normalizer) tuple."""
        target_slope = 15.0
        vmin = 0.0
        vmax = 30.0
        
        result = _create_target_colormap(target_slope, vmin, vmax)
        
        # Should return a tuple
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        cmap, norm = result
        
        # Check colormap
        from matplotlib.colors import LinearSegmentedColormap, Normalize
        assert isinstance(cmap, LinearSegmentedColormap)
        
        # Check normalizer
        assert isinstance(norm, Normalize)
        assert norm.vmin == vmin
        assert norm.vmax == vmax
    
    def test_create_target_colormap_target_at_middle(self):
        """Test target colormap when target is in the middle of range."""
        target_slope = 15.0
        vmin = 0.0
        vmax = 30.0
        
        cmap, norm = _create_target_colormap(target_slope, vmin, vmax)
        
        # Verify the normalizer range
        assert norm.vmin == vmin
        assert norm.vmax == vmax
        
        # Test that colormap produces expected colors at key points
        # At vmin (0) should be green-ish
        low_color = cmap(norm(vmin))
        # At target (15) should be yellow-ish
        target_color = cmap(norm(target_slope))  
        # At vmax (30) should be red-ish
        high_color = cmap(norm(vmax))
        
        # Yellow has high red and green, low blue
        assert target_color[0] > 0.5  # Red component
        assert target_color[1] > 0.5  # Green component
        assert target_color[2] < 0.5  # Blue component
    
    def test_create_target_colormap_target_at_edges(self):
        """Test target colormap when target is at the edges of range."""
        vmin = 0.0
        vmax = 30.0
        
        # Target at minimum
        target_at_min = vmin
        cmap1, norm1 = _create_target_colormap(target_at_min, vmin, vmax)
        
        assert norm1.vmin == vmin
        assert norm1.vmax == vmax
        
        # Target at maximum
        target_at_max = vmax
        cmap2, norm2 = _create_target_colormap(target_at_max, vmin, vmax)
        
        assert norm2.vmin == vmin
        assert norm2.vmax == vmax
    
    def test_create_target_colormap_clamping_behavior(self):
        """Test that target values outside range are handled properly."""
        vmin = 10.0
        vmax = 20.0
        
        # Target below minimum
        target_below = 5.0
        cmap1, norm1 = _create_target_colormap(target_below, vmin, vmax)
        assert norm1.vmin == vmin
        assert norm1.vmax == vmax
        
        # Target above maximum  
        target_above = 25.0
        cmap2, norm2 = _create_target_colormap(target_above, vmin, vmax)
        assert norm2.vmin == vmin
        assert norm2.vmax == vmax
    
    def test_create_target_colormap_different_ranges(self):
        """Test target colormap with different value ranges."""
        test_cases = [
            (5.0, 0.0, 10.0),      # Small range
            (50.0, 0.0, 100.0),    # Large range  
            (1.5, 1.0, 2.0),       # Very small range
            (0.0, -10.0, 10.0),    # Range including negative
        ]
        
        for target, vmin, vmax in test_cases:
            cmap, norm = _create_target_colormap(target, vmin, vmax)
            
            # Should always return valid colormap and normalizer
            assert cmap is not None
            assert norm is not None
            assert norm.vmin == vmin
            assert norm.vmax == vmax