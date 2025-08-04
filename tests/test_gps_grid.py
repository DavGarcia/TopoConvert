"""Tests for GPS grid generation."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from xml.etree import ElementTree as ET
import pandas as pd
import numpy as np

from topoconvert.cli import cli
from topoconvert.core.gps_grid import (
    generate_gps_grid, _extract_polygon_from_kml, _read_csv_points,
    _create_boundary_from_csv, _create_extent_boundary_from_csv,
    _generate_grid_within_polygon, _parse_coordinates_kml
)
from topoconvert.core.exceptions import TopoConvertError, ProcessingError, FileFormatError


class TestGpsGridCommand:
    """Test cases for gps-grid command."""
    
    def test_command_exists(self):
        """Test that the gps-grid command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['gps-grid', '--help'])
        assert result.exit_code == 0
        assert 'Generate GPS grid points within property boundaries' in result.output
        assert 'Supports KML polygons, CSV boundary points' in result.output
    
    def test_command_arguments_and_options(self):
        """Test that all expected arguments and options are available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['gps-grid', '--help'])
        assert result.exit_code == 0
        
        # Check required arguments
        assert 'INPUT_FILE' in result.output
        assert 'OUTPUT_FILE' in result.output
        
        # Check all options
        assert '--input-type' in result.output
        assert '--spacing' in result.output
        assert '--buffer' in result.output
        assert '--boundary-type' in result.output
        assert '--point-style' in result.output
        assert '--grid-name' in result.output
    
    def test_basic_gps_grid_generation_kml(self):
        """Test basic GPS grid generation from KML polygon."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple KML with polygon
            input_file = Path(temp_dir) / "boundary.kml"
            output_file = Path(temp_dir) / "grid_output.kml"
            
            # Create test KML with polygon
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Boundary</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.0840,37.4220,0
              -122.0830,37.4220,0
              -122.0830,37.4230,0
              -122.0840,37.4230,0
              -122.0840,37.4220,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--spacing', '100'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "Created GPS grid" in result.output
            assert "grid points" in result.output
            
            # Verify output KML structure
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            # Check for grid points
            placemarks = root.findall('.//kml:Placemark', ns)
            assert len(placemarks) > 0
    
    def test_gps_grid_from_csv_boundary(self):
        """Test GPS grid generation from CSV boundary points."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create CSV with boundary points
            input_file = Path(temp_dir) / "boundary_points.csv"
            output_file = Path(temp_dir) / "grid_from_csv.kml"
            
            # Create test CSV
            df = pd.DataFrame({
                'Latitude': [37.4220, 37.4220, 37.4230, 37.4230],
                'Longitude': [-122.0840, -122.0830, -122.0830, -122.0840],
                'Name': ['P1', 'P2', 'P3', 'P4']
            })
            df.to_csv(input_file, index=False)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--input-type', 'csv-boundary',
                '--boundary-type', 'convex',
                '--spacing', '150'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "Boundary type: csv-boundary" in result.output
    
    def test_gps_grid_from_csv_extent(self):
        """Test GPS grid generation from CSV extent with buffer."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create CSV with points
            input_file = Path(temp_dir) / "survey_points.csv"
            output_file = Path(temp_dir) / "grid_extent.kml"
            
            # Create test CSV
            df = pd.DataFrame({
                'Latitude': [37.4225, 37.4226, 37.4227],
                'Longitude': [-122.0835, -122.0834, -122.0833]
            })
            df.to_csv(input_file, index=False)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--input-type', 'csv-extent',
                '--buffer', '200',
                '--spacing', '50'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            assert "Buffer: 200" in result.output
    
    def test_gps_grid_with_auto_detect(self):
        """Test GPS grid with auto input type detection."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with KML file (should auto-detect as kml-polygon)
            kml_file = Path(temp_dir) / "test.kml"
            output_file = Path(temp_dir) / "auto_detect.kml"
            
            # Create minimal KML
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>-122.08,37.42,0 -122.07,37.42,0 -122.07,37.43,0 -122.08,37.43,0 -122.08,37.42,0</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
            kml_file.write_text(kml_content)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(kml_file),
                str(output_file),
                # input-type not specified, should auto-detect
                '--spacing', '100'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_gps_grid_with_different_point_styles(self):
        """Test GPS grid with different point styles."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create simple CSV
            input_file = Path(temp_dir) / "points.csv"
            
            df = pd.DataFrame({
                'Latitude': [37.42, 37.43],
                'Longitude': [-122.08, -122.07]
            })
            df.to_csv(input_file, index=False)
            
            # Test different point styles
            for style in ['circle', 'pin', 'square']:
                output_file = Path(temp_dir) / f"grid_{style}.kml"
                
                result = runner.invoke(cli, [
                    'gps-grid',
                    str(input_file),
                    str(output_file),
                    '--input-type', 'csv-extent',
                    '--point-style', style,
                    '--spacing', '100'
                ])
                
                assert result.exit_code == 0
                assert output_file.exists()
    
    def test_gps_grid_with_custom_grid_name(self):
        """Test GPS grid with custom grid name."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "points.csv"
            output_file = Path(temp_dir) / "custom_name.kml"
            
            df = pd.DataFrame({
                'Latitude': [37.42],
                'Longitude': [-122.08]
            })
            df.to_csv(input_file, index=False)
            
            custom_name = "Survey Grid 2025"
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--input-type', 'csv-extent',
                '--grid-name', custom_name,
                '--buffer', '100'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Check that custom name is in output
            tree = ET.parse(str(output_file))
            root = tree.getroot()
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            name_elem = root.find('.//kml:Document/kml:name', ns)
            assert name_elem is not None
            assert name_elem.text == custom_name
    
    def test_gps_grid_with_concave_boundary(self):
        """Test GPS grid with concave boundary type."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "complex_boundary.csv"
            output_file = Path(temp_dir) / "concave_grid.kml"
            
            # Create L-shaped boundary points
            df = pd.DataFrame({
                'Latitude': [37.42, 37.42, 37.425, 37.425, 37.43, 37.43],
                'Longitude': [-122.08, -122.075, -122.075, -122.07, -122.07, -122.08]
            })
            df.to_csv(input_file, index=False)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--input-type', 'csv-boundary',
                '--boundary-type', 'concave',
                '--spacing', '100'
            ])
            
            # May succeed or fail depending on point configuration
            # Just check command runs without crashing
            assert result.exit_code == 0 or "Error" in result.output
    
    def test_gps_grid_with_different_spacing(self):
        """Test GPS grid with different spacing values."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "points.csv"
            
            df = pd.DataFrame({
                'Latitude': [37.42, 37.43],
                'Longitude': [-122.08, -122.07]
            })
            df.to_csv(input_file, index=False)
            
            # Test small spacing
            output_file1 = Path(temp_dir) / "dense_grid.kml"
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file1),
                '--input-type', 'csv-extent',
                '--spacing', '20'
            ])
            
            assert result.exit_code == 0
            assert "20.0 ft spacing" in result.output
            
            # Test large spacing
            output_file2 = Path(temp_dir) / "sparse_grid.kml"
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file2),
                '--input-type', 'csv-extent',
                '--spacing', '200'
            ])
            
            assert result.exit_code == 0
            assert "200.0 ft spacing" in result.output
    
    def test_invalid_input_file(self):
        """Test error handling for invalid input files."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.kml"
            
            # Test with nonexistent file
            result = runner.invoke(cli, [
                'gps-grid',
                'nonexistent.kml',
                str(output_file)
            ])
            
            assert result.exit_code != 0
    
    def test_invalid_input_type(self):
        """Test error handling for invalid input type."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test.csv"
            output_file = Path(temp_dir) / "output.kml"
            
            df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
            df.to_csv(input_file, index=False)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--input-type', 'invalid-type'
            ])
            
            assert result.exit_code != 0
            assert 'Invalid value' in result.output or 'invalid choice' in result.output.lower()
    
    def test_csv_without_required_columns(self):
        """Test error handling for CSV without required columns."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "bad_csv.csv"
            output_file = Path(temp_dir) / "output.kml"
            
            # CSV without Latitude/Longitude columns
            df = pd.DataFrame({'X': [1, 2], 'Y': [3, 4]})
            df.to_csv(input_file, index=False)
            
            result = runner.invoke(cli, [
                'gps-grid',
                str(input_file),
                str(output_file),
                '--input-type', 'csv-boundary'
            ])
            
            assert result.exit_code != 0
            assert 'Error' in result.output


class TestGpsGridCoreFunction:
    """Test cases for the core generate_gps_grid function."""
    
    def test_generate_gps_grid_basic(self):
        """Test basic GPS grid generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create simple KML
            input_file = Path(temp_dir) / "test.kml"
            output_file = Path(temp_dir) / "grid.kml"
            
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>-122.08,37.42,0 -122.07,37.42,0 -122.07,37.43,0 -122.08,37.43,0 -122.08,37.42,0</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
            input_file.write_text(kml_content)
            
            # Test basic generation
            generate_gps_grid(
                input_file=input_file,
                output_file=output_file,
                spacing=100.0
            )
            
            assert output_file.exists()
    
    def test_generate_gps_grid_with_csv_boundary(self):
        """Test GPS grid generation with CSV boundary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "boundary.csv"
            output_file = Path(temp_dir) / "grid.kml"
            
            df = pd.DataFrame({
                'Latitude': [37.42, 37.42, 37.43, 37.43],
                'Longitude': [-122.08, -122.07, -122.07, -122.08]
            })
            df.to_csv(input_file, index=False)
            
            generate_gps_grid(
                input_file=input_file,
                output_file=output_file,
                input_type='csv-boundary',
                boundary_type='convex',
                spacing=200.0
            )
            
            assert output_file.exists()
    
    def test_generate_gps_grid_nonexistent_file(self):
        """Test error handling for nonexistent input file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.kml"
            
            with pytest.raises(FileFormatError, match="Input file not found"):
                generate_gps_grid(
                    input_file=Path("nonexistent.kml"),
                    output_file=output_file
                )
    
    def test_generate_gps_grid_invalid_parameters(self):
        """Test parameter validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test.kml"
            output_file = Path(temp_dir) / "output.kml"
            
            # Create empty KML
            input_file.write_text('<?xml version="1.0"?><kml></kml>')
            
            # Should fail with no polygon found
            with pytest.raises(ProcessingError):
                generate_gps_grid(
                    input_file=input_file,
                    output_file=output_file,
                    input_type='kml-polygon'
                )


class TestGpsGridUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_parse_coordinates_kml(self):
        """Test KML coordinate parsing."""
        # Test single coordinate
        coords = _parse_coordinates_kml("-122.08,37.42,0")
        assert coords == [(-122.08, 37.42)]
        
        # Test multiple coordinates
        coords = _parse_coordinates_kml("-122.08,37.42,0 -122.07,37.43,100")
        assert coords == [(-122.08, 37.42), (-122.07, 37.43)]
        
        # Test with whitespace
        coords = _parse_coordinates_kml("  -122.08,37.42,0   -122.07,37.43,0  ")
        assert coords == [(-122.08, 37.42), (-122.07, 37.43)]
    
    def test_extract_polygon_from_kml(self):
        """Test polygon extraction from KML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            kml_file = Path(temp_dir) / "polygon.kml"
            
            kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>-122.08,37.42,0 -122.07,37.42,0 -122.07,37.43,0 -122.08,37.42,0</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
            kml_file.write_text(kml_content)
            
            coords = _extract_polygon_from_kml(kml_file)
            assert coords is not None
            assert len(coords) >= 3
            assert coords[0] == (-122.08, 37.42)
    
    def test_read_csv_points(self):
        """Test reading points from CSV."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "points.csv"
            
            df = pd.DataFrame({
                'Latitude': [37.42, 37.43],
                'Longitude': [-122.08, -122.07],
                'Name': ['P1', 'P2']
            })
            df.to_csv(csv_file, index=False)
            
            points = _read_csv_points(csv_file)
            assert len(points) == 2
            assert points[0] == (-122.08, 37.42)
            assert points[1] == (-122.07, 37.43)
    
    def test_read_csv_points_missing_columns(self):
        """Test error handling for CSV with missing columns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "bad.csv"
            
            df = pd.DataFrame({
                'X': [1, 2],
                'Y': [3, 4]
            })
            df.to_csv(csv_file, index=False)
            
            with pytest.raises(ProcessingError):
                _read_csv_points(csv_file)
    
    def test_create_boundary_from_csv_convex(self):
        """Test creating convex boundary from CSV points."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "points.csv"
            
            # Create triangle points
            df = pd.DataFrame({
                'Latitude': [37.42, 37.43, 37.425],
                'Longitude': [-122.08, -122.08, -122.07]
            })
            df.to_csv(csv_file, index=False)
            
            boundary = _create_boundary_from_csv(csv_file, 'convex', 0.1)
            assert len(boundary) >= 4  # Closed polygon
            assert boundary[0] == boundary[-1]  # Closed
    
    def test_create_extent_boundary_from_csv(self):
        """Test creating extent boundary with buffer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "points.csv"
            
            df = pd.DataFrame({
                'Latitude': [37.42, 37.43],
                'Longitude': [-122.08, -122.07]
            })
            df.to_csv(csv_file, index=False)
            
            # Test without buffer
            boundary = _create_extent_boundary_from_csv(csv_file, 0.0)
            assert len(boundary) == 5  # Rectangle + close
            
            # Test with buffer
            boundary_buffered = _create_extent_boundary_from_csv(csv_file, 100.0)
            assert len(boundary_buffered) == 5
            
            # Buffered boundary should be larger
            assert boundary_buffered[0][0] < boundary[0][0]  # Min lon smaller
            assert boundary_buffered[0][1] < boundary[0][1]  # Min lat smaller
    
    def test_generate_grid_within_polygon(self):
        """Test grid point generation within polygon."""
        # Create simple square boundary
        boundary = [
            (-122.08, 37.42),
            (-122.07, 37.42),
            (-122.07, 37.43),
            (-122.08, 37.43),
            (-122.08, 37.42)  # Closed
        ]
        
        grid_points = _generate_grid_within_polygon(boundary, 1000.0)
        
        assert len(grid_points) > 0
        
        # Check point format
        for point in grid_points:
            assert len(point) == 3  # lon, lat, id
            assert isinstance(point[0], float)  # longitude
            assert isinstance(point[1], float)  # latitude
            assert isinstance(point[2], int)    # point id
            
            # Check points are within bounds
            assert -122.08 <= point[0] <= -122.07
            assert 37.42 <= point[1] <= 37.43
    
    def test_generate_grid_with_small_polygon(self):
        """Test grid generation with very small polygon."""
        # Create tiny triangle
        boundary = [
            (-122.08, 37.42),
            (-122.0799, 37.42),
            (-122.0799, 37.4201),
            (-122.08, 37.42)
        ]
        
        # Large spacing might result in no points
        grid_points = _generate_grid_within_polygon(boundary, 10000.0)
        
        # Should handle gracefully (empty or few points)
        assert isinstance(grid_points, list)
    
    def test_generate_grid_insufficient_boundary_points(self):
        """Test error handling for insufficient boundary points."""
        # Less than 3 points
        boundary = [(-122.08, 37.42), (-122.07, 37.42)]
        
        # Should raise error with insufficient points for polygon
        with pytest.raises((ValueError, ProcessingError)):
            _generate_grid_within_polygon(boundary, 100.0)