"""Tests for mesh core functionality with result types."""
import pytest
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
import ezdxf

from topoconvert.core.mesh import generate_mesh
from topoconvert.core.exceptions import ProcessingError
from topoconvert.core.result_types import MeshGenerationResult


class TestMeshWithResultTypes:
    """Test cases for mesh functionality returning result objects."""
    
    def create_kml_file(self, temp_dir, points):
        """Helper to create a KML file with points."""
        kml_file = Path(temp_dir) / "test_points.kml"
        
        # Create KML structure
        kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        document = ET.SubElement(kml, 'Document')
        
        for i, (lon, lat, elev) in enumerate(points):
            placemark = ET.SubElement(document, 'Placemark')
            name = ET.SubElement(placemark, 'name')
            name.text = f'Point {i+1}'
            point = ET.SubElement(placemark, 'Point')
            coordinates = ET.SubElement(point, 'coordinates')
            coordinates.text = f'{lon},{lat},{elev}'
        
        # Write KML
        tree = ET.ElementTree(kml)
        tree.write(str(kml_file), encoding='utf-8', xml_declaration=True)
        
        return kml_file
    
    def test_generate_mesh_returns_result(self):
        """Test that generate_mesh returns a MeshGenerationResult."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test KML with 4 points (forms 2 triangles)
            points = [
                (-122.0, 37.0, 100),
                (-122.1, 37.0, 150),
                (-122.1, 37.1, 200),
                (-122.0, 37.1, 120)
            ]
            input_file = self.create_kml_file(temp_dir, points)
            output_file = Path(temp_dir) / "output.dxf"
            
            # Generate mesh
            result = generate_mesh(
                input_file=input_file,
                output_file=output_file,
                elevation_units='meters',
                translate_to_origin=True,
                layer_name='TEST_MESH',
                add_wireframe=True
            )
            
            # Check result type
            assert isinstance(result, MeshGenerationResult)
            assert result.success is True
            assert result.output_file == str(output_file)
            assert result.face_count == 2  # 4 points form 2 triangles
            assert result.vertex_count == 4
            assert result.edge_count > 0  # Should have wireframe edges
            assert result.mesh_type == "TIN"
            assert result.has_wireframe is True
            assert result.layer_name == 'TEST_MESH'
            assert result.translated_to_origin is True
            assert result.reference_point is not None
            
            # Check output file exists
            assert output_file.exists()
            
            # Verify DXF structure
            doc = ezdxf.readfile(str(output_file))
            assert 'TEST_MESH' in doc.layers
            assert 'TEST_MESH_WIREFRAME' in doc.layers
    
    def test_result_contains_coordinate_info(self):
        """Test that result contains coordinate system and range info."""
        with tempfile.TemporaryDirectory() as temp_dir:
            points = [
                (-122.0, 37.0, 100),
                (-122.1, 37.0, 150),
                (-122.0, 37.1, 120)
            ]
            input_file = self.create_kml_file(temp_dir, points)
            output_file = Path(temp_dir) / "output.dxf"
            
            result = generate_mesh(input_file, output_file)
            
            # Check coordinate system
            assert "Auto-detected UTM zone" in result.coordinate_system
            assert "feet" in result.coordinate_system
            
            # Check coordinate ranges
            assert 'coordinate_ranges' in result.details
            ranges = result.details['coordinate_ranges']
            assert 'x' in ranges
            assert 'y' in ranges
            assert 'z' in ranges
            assert ranges['units'] == 'feet'
    
    def test_result_with_wgs84_coordinates(self):
        """Test result when using WGS84 coordinates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            points = [(-122.0, 37.0, 100), (-122.1, 37.0, 150), (-122.0, 37.1, 120)]
            input_file = self.create_kml_file(temp_dir, points)
            output_file = Path(temp_dir) / "output.dxf"
            
            result = generate_mesh(input_file, output_file, wgs84=True)
            
            assert result.coordinate_system == "WGS84 (degrees)"
            assert result.details['coordinate_ranges']['units'] == 'degrees'
    
    def test_result_without_wireframe(self):
        """Test result when wireframe is disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            points = [(-122.0, 37.0, 100), (-122.1, 37.0, 150), (-122.0, 37.1, 120)]
            input_file = self.create_kml_file(temp_dir, points)
            output_file = Path(temp_dir) / "output.dxf"
            
            result = generate_mesh(input_file, output_file, add_wireframe=False)
            
            assert result.has_wireframe is False
            assert result.edge_count == 0
            assert result.details.get('wireframe_layer') is None
    
    def test_insufficient_points_raises_error(self):
        """Test that < 3 points raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            points = [(-122.0, 37.0, 100), (-122.1, 37.0, 150)]
            input_file = self.create_kml_file(temp_dir, points)
            output_file = Path(temp_dir) / "output.dxf"
            
            with pytest.raises(ProcessingError, match="Need at least 3 points"):
                generate_mesh(input_file, output_file)
    
    def test_empty_kml_raises_error(self):
        """Test that empty KML raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = self.create_kml_file(temp_dir, [])
            output_file = Path(temp_dir) / "output.dxf"
            
            with pytest.raises(ProcessingError, match="No points found"):
                generate_mesh(input_file, output_file)
    
    def test_triangulation_info_in_details(self):
        """Test that triangulation info is included in details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            points = [
                (-122.0, 37.0, 100),
                (-122.1, 37.0, 150),
                (-122.1, 37.1, 200),
                (-122.0, 37.1, 120)
            ]
            input_file = self.create_kml_file(temp_dir, points)
            output_file = Path(temp_dir) / "output.dxf"
            
            result = generate_mesh(input_file, output_file)
            
            assert 'triangulation_info' in result.details
            tri_info = result.details['triangulation_info']
            assert tri_info['points_found'] == 4
            assert 'triangles_created' in tri_info