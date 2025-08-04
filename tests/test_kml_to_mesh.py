"""Tests for KML to mesh conversion."""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import ezdxf

from topoconvert.cli import cli
from topoconvert.core.mesh import generate_mesh
from topoconvert.core.exceptions import TopoConvertError, FileFormatError, ProcessingError


class TestKmlToMeshCommand:
    """Test cases for kml-to-dxf-mesh command."""
    
    def test_command_exists(self):
        """Test that the kml-to-dxf-mesh command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-to-dxf-mesh', '--help'])
        assert result.exit_code == 0
        assert 'Generate 3D TIN mesh from KML points' in result.output
        assert 'Creates a Delaunay triangulated irregular network' in result.output
    
    def test_command_arguments_and_options(self):
        """Test that all expected arguments and options are available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['kml-to-dxf-mesh', '--help'])
        assert result.exit_code == 0
        
        # Check required arguments
        assert 'INPUT_FILE' in result.output
        assert 'OUTPUT_FILE' in result.output
        
        # Check all options
        assert '--elevation-units' in result.output
        assert '--translate / --no-translate' in result.output
        assert '--use-reference-point' in result.output
        assert '--layer-name' in result.output
        assert '--mesh-color' in result.output
        assert '--no-wireframe' in result.output
        assert '--wireframe-color' in result.output
        assert '--target-epsg' in result.output
    
    def test_basic_mesh_generation(self):
        """Test basic KML to mesh conversion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh.dxf"
            
            # Skip if test data doesn't exist
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify DXF file is valid and contains mesh data
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            
            # Should contain 3DFACE entities for the mesh
            faces = list(msp.query('3DFACE'))
            assert len(faces) > 0, "Mesh should contain 3D faces"
    
    def test_mesh_with_wireframe(self):
        """Test mesh generation with wireframe edges."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_wireframe.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file),
                '--wireframe-color', '5'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify wireframe lines are included
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            
            faces = list(msp.query('3DFACE'))
            lines = list(msp.query('LINE'))
            
            assert len(faces) > 0, "Should contain mesh faces"
            assert len(lines) > 0, "Should contain wireframe lines"
    
    def test_mesh_without_wireframe(self):
        """Test mesh generation without wireframe edges."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_no_wireframe.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file),
                '--no-wireframe'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify only faces, no wireframe lines
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            
            faces = list(msp.query('3DFACE'))
            lines = list(msp.query('LINE'))
            
            assert len(faces) > 0, "Should contain mesh faces"
            assert len(lines) == 0, "Should not contain wireframe lines"
    
    def test_elevation_units_conversion(self):
        """Test mesh generation with different elevation units."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_feet.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file),
                '--elevation-units', 'feet'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_custom_layer_and_colors(self):
        """Test mesh generation with custom layer name and colors."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_custom.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file),
                '--layer-name', 'CUSTOM_MESH',
                '--mesh-color', '3',
                '--wireframe-color', '6'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify custom layer exists
            doc = ezdxf.readfile(str(output_file))
            assert 'CUSTOM_MESH' in doc.layers
    
    def test_projection_options(self):
        """Test mesh generation with projection options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_projected.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Test with specific EPSG code
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file),
                '--target-epsg', '26914'  # NAD83 / UTM Zone 14N
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
    
    def test_translation_options(self):
        """Test mesh generation with different translation options."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Test with no translation
            output_file1 = Path(temp_dir) / "test_mesh_no_translate.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file1),
                '--no-translate'
            ])
            assert result.exit_code == 0
            assert output_file1.exists()
            
            # Test with reference point translation
            output_file2 = Path(temp_dir) / "test_mesh_ref_point.dxf"
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file2),
                '--use-reference-point'
            ])
            assert result.exit_code == 0
            assert output_file2.exists()
    
    def test_default_output_filename(self):
        """Test that default output filename is generated correctly."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Copy input file to temp directory to test default output
            temp_input = Path(temp_dir) / "input_points.kml"
            temp_input.write_text(input_file.read_text())
            
            # Run without specifying output file
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(temp_input)
            ])
            
            assert result.exit_code == 0
            
            # Check that default output file was created
            default_output = temp_input.with_suffix('.dxf')
            assert default_output.exists()
    
    def test_invalid_input_file(self):
        """Test error handling for invalid input file."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-to-dxf-mesh',
            'nonexistent_file.kml',
            'output.dxf'
        ])
        
        assert result.exit_code != 0
        assert 'does not exist' in result.output or 'No such file' in result.output
    
    def test_invalid_elevation_units(self):
        """Test error handling for invalid elevation units."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'kml-to-dxf-mesh',
            'testdata/sample_points.kml',
            'output.dxf',
            '--elevation-units', 'invalid'
        ])
        
        assert result.exit_code != 0
        assert 'Invalid value' in result.output or 'invalid' in result.output.lower()
    
    def test_invalid_color_values(self):
        """Test error handling for invalid color values."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_output.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Test negative mesh color
            result = runner.invoke(cli, [
                'kml-to-dxf-mesh',
                str(input_file),
                str(output_file),
                '--mesh-color', '-1'
            ])
            
            assert result.exit_code != 0


class TestMeshCoreFunction:
    """Test cases for the core mesh generation function."""
    
    def test_generate_mesh_basic(self):
        """Test basic mesh generation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Test basic mesh generation
            generate_mesh(
                input_file=input_file,
                output_file=output_file,
                elevation_units='meters',
                translate_to_origin=True,
                layer_name='TEST_MESH',
                mesh_color=8
            )
            
            assert output_file.exists()
            
            # Verify mesh content
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            faces = list(msp.query('3DFACE'))
            assert len(faces) > 0
    
    def test_generate_mesh_parameter_validation(self):
        """Test parameter validation in mesh generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Test invalid elevation units
            with pytest.raises(ValueError, match="elevation_units must be"):
                generate_mesh(
                    input_file=input_file,
                    output_file=output_file,
                    elevation_units='invalid'
                )
            
            # Test negative color values
            with pytest.raises(ValueError, match="Color indices must be non-negative"):
                generate_mesh(
                    input_file=input_file,
                    output_file=output_file,
                    mesh_color=-1
                )
            
            with pytest.raises(ValueError, match="Color indices must be non-negative"):
                generate_mesh(
                    input_file=input_file,
                    output_file=output_file,
                    wireframe_color=-5
                )
    
    def test_generate_mesh_nonexistent_file(self):
        """Test error handling for nonexistent input files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("nonexistent_file.kml")
            output_file = Path(temp_dir) / "test_mesh.dxf"
            
            with pytest.raises((FileNotFoundError, ProcessingError)):
                generate_mesh(
                    input_file=input_file,
                    output_file=output_file
                )
    
    def test_generate_mesh_with_wireframe(self):
        """Test mesh generation with wireframe enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_wireframe.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            generate_mesh(
                input_file=input_file,
                output_file=output_file,
                add_wireframe=True,
                wireframe_color=5
            )
            
            assert output_file.exists()
            
            # Verify wireframe content
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            faces = list(msp.query('3DFACE'))
            lines = list(msp.query('LINE'))
            
            assert len(faces) > 0, "Should contain mesh faces"
            assert len(lines) > 0, "Should contain wireframe lines"
    
    def test_generate_mesh_projection_options(self):
        """Test mesh generation with different projection options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_projected.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            # Test with specific EPSG code
            generate_mesh(
                input_file=input_file,
                output_file=output_file,
                target_epsg=26914,  # NAD83 / UTM Zone 14N
                wgs84=False
            )
            
            assert output_file.exists()
    
    def test_mesh_triangulation_quality(self):
        """Test that generated mesh has proper triangulation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path("testdata/sample_points.kml")
            output_file = Path(temp_dir) / "test_mesh_quality.dxf"
            
            if not input_file.exists():
                pytest.skip("Test data file testdata/sample_points.kml not found")
            
            generate_mesh(
                input_file=input_file,
                output_file=output_file
            )
            
            assert output_file.exists()
            
            # Verify mesh quality
            doc = ezdxf.readfile(str(output_file))
            msp = doc.modelspace()
            faces = list(msp.query('3DFACE'))
            
            # Each face should have exactly 4 vertices (3D face representation)
            for face in faces:
                # DXF 3DFACE has 4 vertices (even for triangles, 4th vertex equals 3rd)
                assert hasattr(face.dxf, 'vtx0')
                assert hasattr(face.dxf, 'vtx1')
                assert hasattr(face.dxf, 'vtx2')
                assert hasattr(face.dxf, 'vtx3')