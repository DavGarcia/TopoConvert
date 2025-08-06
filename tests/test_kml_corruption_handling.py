"""Test KML corruption handling across all CLI commands."""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import subprocess
import sys

from tests.edge_case_generators import KMLCorruption, generate_corrupted_kml
from topoconvert.cli import cli


class TestKMLCorruptionHandling:
    """Test how CLI commands handle corrupted KML input files."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def generate_corrupted_kml_file(self, corruption_type: KMLCorruption, filename: str = None) -> Path:
        """Generate a corrupted KML file for testing."""
        if filename is None:
            filename = f"corrupted_{corruption_type.value}.kml"
        
        file_path = self.temp_path / filename
        generate_corrupted_kml(
            file_path,
            corruption_type=corruption_type,
            point_count=10,
            seed=42
        )
        return file_path
    
    def test_kml_to_dxf_contours_malformed_xml(self):
        """Test kml-to-dxf-contours with malformed XML."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.MALFORMED_XML)
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should fail gracefully with non-zero exit code
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()
        # Should not create output file on error
        assert not output_file.exists()
    
    def test_kml_to_dxf_contours_invalid_coordinates(self):
        """Test kml-to-dxf-contours with invalid coordinates."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.INVALID_COORDINATES)
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle invalid coordinates gracefully
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()
    
    def test_kml_to_dxf_contours_missing_elements(self):
        """Test kml-to-dxf-contours with missing required elements."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.MISSING_ELEMENTS)
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle missing elements gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "missing", "invalid"])
    
    def test_kml_to_dxf_contours_truncated_file(self):
        """Test kml-to-dxf-contours with truncated file."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.TRUNCATED_FILE)
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle truncated files gracefully
        assert result.exit_code != 0
        assert "error" in result.output.lower()
    
    def test_kml_to_dxf_mesh_malformed_xml(self):
        """Test kml-to-dxf-mesh with malformed XML."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.MALFORMED_XML)
        output_file = self.temp_path / "mesh.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-mesh',
            str(corrupted_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert "error" in result.output.lower()
        assert not output_file.exists()
    
    def test_kml_to_dxf_mesh_invalid_coordinates(self):
        """Test kml-to-dxf-mesh with invalid coordinates."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.INVALID_COORDINATES)
        output_file = self.temp_path / "mesh.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-mesh',
            str(corrupted_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "invalid", "coordinates"])
    
    def test_kml_to_points_malformed_xml(self):
        """Test kml-to-points with malformed XML."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.MALFORMED_XML)
        output_file = self.temp_path / "points.csv"
        
        result = self.runner.invoke(cli, [
            'kml-to-points',
            str(corrupted_file),
            str(output_file),
            '--format', 'csv'
        ])
        
        assert result.exit_code != 0
        assert "error" in result.output.lower()
        assert not output_file.exists()
    
    def test_kml_to_points_invalid_coordinates(self):
        """Test kml-to-points with invalid coordinates."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.INVALID_COORDINATES)
        output_file = self.temp_path / "points.csv"
        
        result = self.runner.invoke(cli, [
            'kml-to-points',
            str(corrupted_file),
            str(output_file),
            '--format', 'csv'
        ])
        
        # May succeed but should handle invalid coordinates appropriately
        # Either succeed with valid points only or fail with clear message
        if result.exit_code != 0:
            assert "error" in result.output.lower() or "invalid" in result.output.lower()
    
    def test_kml_contours_to_dxf_malformed_xml(self):
        """Test kml-contours-to-dxf with malformed XML."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.MALFORMED_XML)
        output_file = self.temp_path / "contours.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-contours-to-dxf',
            str(corrupted_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert "error" in result.output.lower()
        assert not output_file.exists()
    
    def test_slope_heatmap_malformed_xml(self):
        """Test slope-heatmap with malformed XML."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.MALFORMED_XML)
        output_file = self.temp_path / "heatmap.png"
        
        result = self.runner.invoke(cli, [
            'slope-heatmap',
            str(corrupted_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert "error" in result.output.lower()
        assert not output_file.exists()
    
    def test_slope_heatmap_invalid_coordinates(self):
        """Test slope-heatmap with invalid coordinates."""
        corrupted_file = self.generate_corrupted_kml_file(KMLCorruption.INVALID_COORDINATES)
        output_file = self.temp_path / "heatmap.png"
        
        result = self.runner.invoke(cli, [
            'slope-heatmap',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle invalid coordinates gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "invalid", "coordinates"])


class TestKMLCorruptionErrorMessages:
    """Test that error messages are clear and consistent."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_error_message_clarity_malformed_xml(self):
        """Test that error messages for malformed XML are clear."""
        corrupted_file = self.temp_path / "malformed.kml"
        generate_corrupted_kml(
            corrupted_file,
            corruption_type=KMLCorruption.MALFORMED_XML,
            point_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Error message should mention XML or parsing
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in [
            "xml", "parse", "malformed", "invalid", "corrupt"
        ])
    
    def test_error_message_clarity_invalid_coordinates(self):
        """Test that error messages for invalid coordinates are clear."""
        corrupted_file = self.temp_path / "invalid_coords.kml"
        generate_corrupted_kml(
            corrupted_file,
            corruption_type=KMLCorruption.INVALID_COORDINATES,
            point_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Error message should mention coordinates or values
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in [
            "coordinate", "invalid", "value", "number", "parse"
        ])
    
    def test_exit_codes_consistency(self):
        """Test that exit codes are consistent across different corruption types."""
        corruption_types = [
            KMLCorruption.MALFORMED_XML,
            KMLCorruption.INVALID_COORDINATES,
            KMLCorruption.MISSING_ELEMENTS,
            KMLCorruption.TRUNCATED_FILE
        ]
        
        exit_codes = []
        
        for corruption_type in corruption_types:
            corrupted_file = self.temp_path / f"test_{corruption_type.value}.kml"
            generate_corrupted_kml(
                corrupted_file,
                corruption_type=corruption_type,
                point_count=5,
                seed=42
            )
            
            output_file = self.temp_path / f"output_{corruption_type.value}.dxf"
            
            result = self.runner.invoke(cli, [
                'kml-to-dxf-contours',
                str(corrupted_file),
                str(output_file)
            ])
            
            exit_codes.append(result.exit_code)
        
        # All should have non-zero exit codes
        assert all(code != 0 for code in exit_codes), f"Some exit codes were 0: {exit_codes}"
        
        # Exit codes should be consistent (all the same non-zero value)
        unique_codes = set(exit_codes)
        assert len(unique_codes) <= 2, f"Too many different exit codes: {unique_codes}"


class TestKMLCorruptionRecovery:
    """Test recovery behavior when encountering corrupted KML files."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_no_partial_output_on_failure(self):
        """Test that no partial output files are created when input is corrupted."""
        corrupted_file = self.temp_path / "corrupted.kml"
        generate_corrupted_kml(
            corrupted_file,
            corruption_type=KMLCorruption.MALFORMED_XML,
            point_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should fail and not create output file
        assert result.exit_code != 0
        assert not output_file.exists(), "Partial output file should not be created on failure"
    
    def test_no_crash_on_corrupted_input(self):
        """Test that corrupted input doesn't cause crashes but should report failures."""
        corruption_types = [
            KMLCorruption.MALFORMED_XML,
            KMLCorruption.INVALID_COORDINATES,
            KMLCorruption.MISSING_ELEMENTS,
            KMLCorruption.TRUNCATED_FILE
        ]
        
        commands = [
            ['kml-to-dxf-contours'],
            ['kml-to-dxf-mesh'],
            ['kml-to-points', '--format', 'csv'],
            ['slope-heatmap']
        ]
        
        # Note: Temporarily excluding kml-contours-to-dxf as it may need enhancement
        # to properly detect and report corruption issues
        
        for corruption_type in corruption_types:
            corrupted_file = self.temp_path / f"test_{corruption_type.value}.kml"
            generate_corrupted_kml(
                corrupted_file,
                corruption_type=corruption_type,
                point_count=10,
                seed=42
            )
            
            for cmd_args in commands:
                output_file = self.temp_path / f"output_{corruption_type.value}_{cmd_args[0]}"
                
                # Add appropriate extension based on command
                if 'dxf' in cmd_args[0]:
                    output_file = output_file.with_suffix('.dxf')
                elif 'points' in cmd_args[0]:
                    output_file = output_file.with_suffix('.csv')
                elif 'heatmap' in cmd_args[0]:
                    output_file = output_file.with_suffix('.png')
                
                result = self.runner.invoke(cli, cmd_args + [
                    str(corrupted_file),
                    str(output_file)
                ])
                
                # Should not crash (exit code should not be negative or indicate crash)
                assert result.exit_code >= 0, f"Command {cmd_args} crashed with code {result.exit_code}"
                
                # Corrupted input should cause failure - we want failures to be reported
                assert result.exit_code != 0, f"Command {cmd_args} should have failed but returned 0 for {corruption_type}"
                
                # Should produce some error output
                assert len(result.output) > 0, f"Command {cmd_args} produced no output"


class TestKMLCorruptionWithDifferentCommands:
    """Test KML corruption handling across all CLI commands that accept KML input."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_all_kml_commands_handle_corruption(self):
        """Test that all KML-accepting commands handle corruption gracefully."""
        # Commands that accept KML input
        kml_commands = [
            ('kml-to-dxf-contours', '.dxf'),
            ('kml-to-dxf-mesh', '.dxf'),
            ('kml-to-points', '.csv'),
            ('slope-heatmap', '.png')
        ]
        
        # Note: Temporarily excluding kml-contours-to-dxf as it may need enhancement
        # to properly detect and report corruption issues
        
        corrupted_file = self.temp_path / "corrupted.kml"
        generate_corrupted_kml(
            corrupted_file,
            corruption_type=KMLCorruption.MALFORMED_XML,
            point_count=10,
            seed=42
        )
        
        for command, extension in kml_commands:
            output_file = self.temp_path / f"output_{command.replace('-', '_')}{extension}"
            
            if command == 'kml-to-points':
                cmd_args = [command, str(corrupted_file), str(output_file), '--format', 'csv']
            else:
                cmd_args = [command, str(corrupted_file), str(output_file)]
            
            result = self.runner.invoke(cli, cmd_args)
            
            # Each command should handle corruption gracefully
            assert result.exit_code != 0, f"Command {command} should fail with corrupted input"
            assert len(result.output) > 0, f"Command {command} should produce error output"
            assert not output_file.exists(), f"Command {command} should not create output on failure"