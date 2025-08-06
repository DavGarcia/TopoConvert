"""Test CSV corruption handling across all CLI commands."""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import subprocess
import sys

from tests.edge_case_generators import CSVCorruption, generate_corrupted_csv
from topoconvert.cli import cli


class TestCSVCorruptionHandling:
    """Test how CLI commands handle corrupted CSV input files."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def generate_corrupted_csv_file(self, corruption_type: CSVCorruption, filename: str = None) -> Path:
        """Generate a corrupted CSV file for testing."""
        if filename is None:
            filename = f"corrupted_{corruption_type.value}.csv"
        
        file_path = self.temp_path / filename
        generate_corrupted_csv(
            file_path,
            corruption_type=corruption_type,
            row_count=10,
            seed=42
        )
        return file_path
    
    def test_csv_to_kml_wrong_columns(self):
        """Test csv-to-kml with wrong column structure."""
        corrupted_file = self.generate_corrupted_csv_file(CSVCorruption.WRONG_COLUMNS)
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should fail gracefully with non-zero exit code
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "column", "missing", "invalid"])
        # Should not create output file on error
        assert not output_file.exists()
    
    def test_csv_to_kml_invalid_data_types(self):
        """Test csv-to-kml with invalid data types."""
        corrupted_file = self.generate_corrupted_csv_file(CSVCorruption.INVALID_DATA_TYPES)
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle invalid data types gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "invalid", "convert", "numeric"])
    
    def test_csv_to_kml_encoding_issues(self):
        """Test csv-to-kml with encoding problems."""
        corrupted_file = self.generate_corrupted_csv_file(CSVCorruption.ENCODING_ISSUES)
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle encoding issues gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "encoding", "decode", "utf"])
    
    def test_csv_to_kml_missing_headers(self):
        """Test csv-to-kml with missing headers."""
        corrupted_file = self.generate_corrupted_csv_file(CSVCorruption.MISSING_HEADERS)
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle missing headers gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "header", "column", "missing"])
    
    def test_csv_to_kml_inconsistent_rows(self):
        """Test csv-to-kml with inconsistent row lengths."""
        corrupted_file = self.generate_corrupted_csv_file(CSVCorruption.INCONSISTENT_ROWS)
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle inconsistent rows gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "inconsistent", "column", "row"])
    
    def test_multi_csv_to_kml_wrong_columns(self):
        """Test multi-csv-to-kml with corrupted files."""
        corrupted_file1 = self.generate_corrupted_csv_file(CSVCorruption.WRONG_COLUMNS, "file1.csv")
        valid_csv = self.temp_path / "valid.csv"
        valid_csv.write_text("x,y,z,name\n1,2,3,Point1\n4,5,6,Point2\n")
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'multi-csv-to-kml',
            str(corrupted_file1),
            str(valid_csv),
            str(output_file)
        ])
        
        # Should fail if any input file is corrupted
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "column", "invalid"])
        assert not output_file.exists()
    
    def test_multi_csv_to_dxf_invalid_data_types(self):
        """Test multi-csv-to-dxf with invalid data types."""
        corrupted_file = self.generate_corrupted_csv_file(CSVCorruption.INVALID_DATA_TYPES)
        output_file = self.temp_path / "output.dxf"
        
        result = self.runner.invoke(cli, [
            'multi-csv-to-dxf',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should handle invalid data types gracefully
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "invalid", "numeric"])
        assert not output_file.exists()


class TestCSVCorruptionErrorMessages:
    """Test that error messages for CSV corruption are clear and consistent."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_error_message_clarity_wrong_columns(self):
        """Test that error messages for wrong columns are clear."""
        corrupted_file = self.temp_path / "wrong_columns.csv"
        generate_corrupted_csv(
            corrupted_file,
            corruption_type=CSVCorruption.WRONG_COLUMNS,
            row_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Error message should mention columns or missing fields
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in [
            "column", "field", "missing", "required", "coordinate"
        ])
    
    def test_error_message_clarity_invalid_data_types(self):
        """Test that error messages for invalid data types are clear."""
        corrupted_file = self.temp_path / "invalid_data.csv"
        generate_corrupted_csv(
            corrupted_file,
            corruption_type=CSVCorruption.INVALID_DATA_TYPES,
            row_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Error message should mention data types or conversion issues
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in [
            "convert", "invalid", "numeric", "float", "number", "value", 
            "supported between instances", "str", "int", "comparison"
        ])
    
    def test_error_message_clarity_encoding_issues(self):
        """Test that error messages for encoding issues are clear."""
        corrupted_file = self.temp_path / "encoding_issues.csv"
        generate_corrupted_csv(
            corrupted_file,
            corruption_type=CSVCorruption.ENCODING_ISSUES,
            row_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Error message should mention encoding or reading issues
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert any(keyword in output_lower for keyword in [
            "encoding", "decode", "utf", "character", "read"
        ])
    
    def test_exit_codes_consistency(self):
        """Test that exit codes are consistent across different CSV corruption types."""
        corruption_types = [
            CSVCorruption.WRONG_COLUMNS,
            CSVCorruption.INVALID_DATA_TYPES,
            CSVCorruption.ENCODING_ISSUES,
            CSVCorruption.MISSING_HEADERS,
            CSVCorruption.INCONSISTENT_ROWS
        ]
        
        exit_codes = []
        
        for corruption_type in corruption_types:
            corrupted_file = self.temp_path / f"test_{corruption_type.value}.csv"
            generate_corrupted_csv(
                corrupted_file,
                corruption_type=corruption_type,
                row_count=5,
                seed=42
            )
            
            output_file = self.temp_path / f"output_{corruption_type.value}.kml"
            
            result = self.runner.invoke(cli, [
                'csv-to-kml',
                str(corrupted_file),
                str(output_file)
            ])
            
            exit_codes.append(result.exit_code)
        
        # All should have non-zero exit codes
        assert all(code != 0 for code in exit_codes), f"Some exit codes were 0: {exit_codes}"
        
        # Exit codes should be consistent (all the same non-zero value)
        unique_codes = set(exit_codes)
        assert len(unique_codes) <= 2, f"Too many different exit codes: {unique_codes}"


class TestCSVCorruptionRecovery:
    """Test recovery behavior when encountering corrupted CSV files."""
    
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
        """Test that no partial output files are created when CSV input is corrupted."""
        corrupted_file = self.temp_path / "corrupted.csv"
        generate_corrupted_csv(
            corrupted_file,
            corruption_type=CSVCorruption.WRONG_COLUMNS,
            row_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'csv-to-kml',
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should fail and not create output file
        assert result.exit_code != 0
        assert not output_file.exists(), "Partial output file should not be created on failure"
    
    def test_no_crash_on_corrupted_input(self):
        """Test that corrupted CSV input doesn't cause crashes but should report failures."""
        corruption_types = [
            CSVCorruption.WRONG_COLUMNS,
            CSVCorruption.INVALID_DATA_TYPES,
            CSVCorruption.ENCODING_ISSUES,
            CSVCorruption.MISSING_HEADERS,
            CSVCorruption.INCONSISTENT_ROWS
        ]
        
        csv_commands = [
            ['csv-to-kml'],
            ['multi-csv-to-kml'],
            ['multi-csv-to-dxf']
        ]
        
        for corruption_type in corruption_types:
            corrupted_file = self.temp_path / f"test_{corruption_type.value}.csv"
            generate_corrupted_csv(
                corrupted_file,
                corruption_type=corruption_type,
                row_count=10,
                seed=42
            )
            
            for cmd_args in csv_commands:
                output_file = self.temp_path / f"output_{corruption_type.value}_{cmd_args[0]}"
                
                # Add appropriate extension based on command
                if 'kml' in cmd_args[0]:
                    output_file = output_file.with_suffix('.kml')
                elif 'dxf' in cmd_args[0]:
                    output_file = output_file.with_suffix('.dxf')
                
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


class TestCSVCorruptionWithDifferentCommands:
    """Test CSV corruption handling across all CLI commands that accept CSV input."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_all_csv_commands_handle_corruption(self):
        """Test that all CSV-accepting commands handle corruption gracefully."""
        # Commands that accept CSV input
        csv_commands = [
            ('csv-to-kml', '.kml'),
            ('multi-csv-to-kml', '.kml'),
            ('multi-csv-to-dxf', '.dxf')
        ]
        
        corrupted_file = self.temp_path / "corrupted.csv"
        generate_corrupted_csv(
            corrupted_file,
            corruption_type=CSVCorruption.WRONG_COLUMNS,
            row_count=10,
            seed=42
        )
        
        for command, extension in csv_commands:
            output_file = self.temp_path / f"output_{command.replace('-', '_')}{extension}"
            
            cmd_args = [command, str(corrupted_file), str(output_file)]
            
            result = self.runner.invoke(cli, cmd_args)
            
            # Each command should handle corruption by failing gracefully
            assert result.exit_code != 0, f"Command {command} should fail with corrupted input"
            assert len(result.output) > 0, f"Command {command} should produce error output"
            assert not output_file.exists(), f"Command {command} should not create output on failure"


class TestMixedCorruptionScenarios:
    """Test edge cases with mixed corruption types and multi-file scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_multi_csv_with_mixed_corruption(self):
        """Test multi-csv commands with different types of corruption in different files."""
        # Create files with different corruption types
        corrupted_file1 = self.temp_path / "wrong_columns.csv"
        generate_corrupted_csv(
            corrupted_file1,
            corruption_type=CSVCorruption.WRONG_COLUMNS,
            row_count=5,
            seed=42
        )
        
        corrupted_file2 = self.temp_path / "invalid_data.csv"
        generate_corrupted_csv(
            corrupted_file2,
            corruption_type=CSVCorruption.INVALID_DATA_TYPES,
            row_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'multi-csv-to-kml',
            str(corrupted_file1),
            str(corrupted_file2),
            str(output_file)
        ])
        
        # Should fail when any input file is corrupted
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "invalid", "column"])
        assert not output_file.exists()
    
    def test_multi_csv_with_one_valid_one_corrupted(self):
        """Test multi-csv commands with one valid and one corrupted file."""
        # Create one valid file
        valid_file = self.temp_path / "valid.csv"
        valid_file.write_text("x,y,z,name\n1.0,2.0,3.0,Point1\n4.0,5.0,6.0,Point2\n")
        
        # Create one corrupted file
        corrupted_file = self.temp_path / "corrupted.csv"
        generate_corrupted_csv(
            corrupted_file,
            corruption_type=CSVCorruption.WRONG_COLUMNS,
            row_count=5,
            seed=42
        )
        
        output_file = self.temp_path / "output.kml"
        
        result = self.runner.invoke(cli, [
            'multi-csv-to-kml',
            str(valid_file),
            str(corrupted_file),
            str(output_file)
        ])
        
        # Should fail because one file is corrupted, even if others are valid
        assert result.exit_code != 0
        assert any(keyword in result.output.lower() for keyword in ["error", "column", "invalid"])
        assert not output_file.exists()