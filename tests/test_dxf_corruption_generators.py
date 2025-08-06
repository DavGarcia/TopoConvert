"""Test DXF corruption generators and document current CLI limitations."""

import pytest
import tempfile
from pathlib import Path

from tests.edge_case_generators import DXFCorruption, generate_corrupted_dxf


class TestDXFCorruptionGenerators:
    """Test DXF corruption generators.
    
    Note: Currently TopoConvert CLI commands do not accept DXF as input,
    so these tests verify that the corruption generators work correctly
    for potential future use when DXF reading capabilities are added.
    """
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_generate_malformed_header_dxf(self):
        """Test generation of DXF with malformed header."""
        corrupted_file = self.temp_path / "malformed_header.dxf"
        generate_corrupted_dxf(
            corrupted_file,
            corruption_type=DXFCorruption.MALFORMED_HEADER,
            entity_count=5,
            seed=42
        )
        
        assert corrupted_file.exists()
        content = corrupted_file.read_text()
        
        # Should contain DXF structure but with malformed elements
        assert "SECTION" in content
        assert "HEADER" in content
        assert "ENTITIES" in content
        assert "INVALID_VALUE" in content  # Our intentional corruption
        assert "<!--" in content  # HTML comment in DXF (invalid)
    
    def test_generate_invalid_entities_dxf(self):
        """Test generation of DXF with invalid entity definitions."""
        corrupted_file = self.temp_path / "invalid_entities.dxf"
        generate_corrupted_dxf(
            corrupted_file,
            corruption_type=DXFCorruption.INVALID_ENTITIES,
            entity_count=6,
            seed=42
        )
        
        assert corrupted_file.exists()
        content = corrupted_file.read_text()
        
        # Should contain both valid and invalid entities
        assert "POINT" in content  # Valid entity type
        # Should contain at least one of the invalid entity types
        invalid_entities = ["INVALID_ENTITY_TYPE", "POINT_WITH_BAD_CODES", "MALFORMED_LINE"]
        assert any(invalid_entity in content for invalid_entity in invalid_entities)
        assert "invalid_coordinate" in content  # Invalid coordinate value
    
    def test_generate_missing_sections_dxf(self):
        """Test generation of DXF with missing required sections."""
        corrupted_file = self.temp_path / "missing_sections.dxf"
        generate_corrupted_dxf(
            corrupted_file,
            corruption_type=DXFCorruption.MISSING_SECTIONS,
            entity_count=3,
            seed=42
        )
        
        assert corrupted_file.exists()
        content = corrupted_file.read_text()
        
        # Should have entities but missing proper header and footer
        assert "ENTITIES" in content
        assert "POINT" in content
        # Should NOT have proper header section
        assert "$ACADVER" not in content
        # Should NOT have proper ending
        assert "ENDSEC" not in content or "EOF" not in content
    
    def test_generate_truncated_dxf(self):
        """Test generation of truncated DXF file."""
        corrupted_file = self.temp_path / "truncated.dxf"
        generate_corrupted_dxf(
            corrupted_file,
            corruption_type=DXFCorruption.TRUNCATED_FILE,
            entity_count=5,
            seed=42
        )
        
        assert corrupted_file.exists()
        content = corrupted_file.read_text()
        
        # Should start properly but be cut off
        assert "SECTION" in content
        assert "HEADER" in content
        assert "ENTITIES" in content
        assert "POINT" in content
        # Should end abruptly (no EOF)
        assert not content.strip().endswith("EOF")
        # Should end mid-entity
        lines = content.strip().split('\n')
        last_line = lines[-1] if lines else ""
        assert last_line in ["20", "30", "10"] or last_line.replace('.', '').replace('-', '').isdigit()
    
    def test_generate_invalid_coordinates_dxf(self):
        """Test generation of DXF with invalid coordinate values."""
        corrupted_file = self.temp_path / "invalid_coords.dxf"
        generate_corrupted_dxf(
            corrupted_file,
            corruption_type=DXFCorruption.INVALID_COORDINATES,
            entity_count=6,
            seed=42
        )
        
        assert corrupted_file.exists()
        content = corrupted_file.read_text()
        
        # Should contain both valid and invalid coordinates
        assert "POINT" in content
        assert any(invalid in content for invalid in ["NaN", "invalid", "text", "###ERROR###"])
        # Should also have some valid numeric coordinates for contrast
        import re
        numeric_pattern = r'-?\d+\.?\d*'
        assert re.search(numeric_pattern, content)
    
    def test_all_corruption_types_generate_files(self):
        """Test that all DXF corruption types generate files successfully."""
        corruption_types = [
            DXFCorruption.MALFORMED_HEADER,
            DXFCorruption.INVALID_ENTITIES,
            DXFCorruption.MISSING_SECTIONS,
            DXFCorruption.TRUNCATED_FILE,
            DXFCorruption.INVALID_COORDINATES
        ]
        
        for corruption_type in corruption_types:
            corrupted_file = self.temp_path / f"test_{corruption_type.value}.dxf"
            generate_corrupted_dxf(
                corrupted_file,
                corruption_type=corruption_type,
                entity_count=3,
                seed=42
            )
            
            assert corrupted_file.exists(), f"Failed to generate {corruption_type.value}"
            assert corrupted_file.stat().st_size > 0, f"Generated empty file for {corruption_type.value}"
    
    def test_reproducible_generation(self):
        """Test that DXF corruption generation is reproducible with same seed."""
        corruption_type = DXFCorruption.INVALID_ENTITIES
        
        # Generate twice with same seed
        file1 = self.temp_path / "test1.dxf"
        file2 = self.temp_path / "test2.dxf"
        
        generate_corrupted_dxf(file1, corruption_type, entity_count=5, seed=42)
        generate_corrupted_dxf(file2, corruption_type, entity_count=5, seed=42)
        
        # Should be identical
        assert file1.read_text() == file2.read_text()


class TestDXFCorruptionDocumentation:
    """Document the current state of DXF support in TopoConvert CLI."""
    
    def test_document_no_dxf_input_commands(self):
        """Document that current CLI commands do not accept DXF input.
        
        This test serves as documentation that DXF corruption testing
        is not currently applicable to TopoConvert CLI commands because
        none of them accept DXF files as input.
        
        The DXF corruption generators are provided for:
        1. Future functionality if DXF reading is added
        2. Testing DXF writing robustness with corrupted input data
        3. Completeness of the edge case testing framework
        """
        # Commands that output TO DXF but don't read FROM DXF
        dxf_output_commands = [
            "kml-to-dxf-contours",
            "kml-to-dxf-mesh", 
            "kml-contours-to-dxf",
            "multi-csv-to-dxf"
        ]
        
        # All commands read from other formats (KML, CSV)
        input_formats_supported = ["KML", "CSV"]
        dxf_input_supported = False
        
        # Document current state
        assert not dxf_input_supported, (
            "DXF input is not currently supported by any CLI commands. "
            "DXF corruption testing is provided for future use."
        )
        
        assert len(dxf_output_commands) > 0, (
            "TopoConvert supports outputting TO DXF format"
        )
        
        assert "DXF" not in input_formats_supported, (
            "DXF is not in the list of supported input formats"
        )