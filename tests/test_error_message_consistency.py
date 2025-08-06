"""Test error message clarity and exit code consistency across all corruption types."""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from typing import Dict, List, Tuple
import re

from tests.edge_case_generators import (
    KMLCorruption, CSVCorruption, DXFCorruption,
    generate_corrupted_kml, generate_corrupted_csv
)
from topoconvert.cli import cli


class TestErrorMessageConsistency:
    """Test that error messages are consistent and informative across all file types."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_exit_code_consistency_across_formats(self):
        """Test that exit codes are consistent across different file format corruptions."""
        # Test scenarios: (command, input_file, output_file, corruption_generator, corruption_type)
        test_scenarios = [
            # KML corruption scenarios
            ('kml-to-dxf-contours', 'input.kml', 'output.dxf', 
             generate_corrupted_kml, KMLCorruption.MALFORMED_XML),
            ('kml-to-dxf-mesh', 'input.kml', 'output.dxf', 
             generate_corrupted_kml, KMLCorruption.INVALID_COORDINATES),
            ('kml-to-points', 'input.kml', 'output.csv', 
             generate_corrupted_kml, KMLCorruption.MISSING_ELEMENTS),
            ('slope-heatmap', 'input.kml', 'output.png', 
             generate_corrupted_kml, KMLCorruption.TRUNCATED_FILE),
            
            # CSV corruption scenarios
            ('csv-to-kml', 'input.csv', 'output.kml', 
             generate_corrupted_csv, CSVCorruption.WRONG_COLUMNS),
            ('multi-csv-to-kml', 'input.csv', 'output.kml', 
             generate_corrupted_csv, CSVCorruption.INVALID_DATA_TYPES),
            ('multi-csv-to-dxf', 'input.csv', 'output.dxf', 
             generate_corrupted_csv, CSVCorruption.ENCODING_ISSUES),
        ]
        
        exit_codes = []
        command_details = []
        
        for command, input_filename, output_filename, generator_func, corruption_type in test_scenarios:
            input_file = self.temp_path / input_filename
            output_file = self.temp_path / output_filename
            
            # Generate corrupted input file
            if generator_func == generate_corrupted_kml:
                generator_func(input_file, corruption_type=corruption_type, point_count=5, seed=42)
            else:
                generator_func(input_file, corruption_type=corruption_type, row_count=5, seed=42)
            
            # Run command
            if command == 'kml-to-points':
                cmd_args = [command, str(input_file), str(output_file), '--format', 'csv']
            else:
                cmd_args = [command, str(input_file), str(output_file)]
            
            result = self.runner.invoke(cli, cmd_args)
            
            exit_codes.append(result.exit_code)
            command_details.append((command, corruption_type.value, result.exit_code))
        
        # All commands should fail with non-zero exit codes
        non_zero_codes = [code for code in exit_codes if code != 0]
        assert len(non_zero_codes) == len(exit_codes), (
            f"Some commands returned exit code 0 when they should have failed. "
            f"Details: {command_details}"
        )
        
        # Exit codes should be consistent (mostly the same value)
        unique_codes = set(exit_codes)
        assert len(unique_codes) <= 2, (
            f"Too many different exit codes found: {unique_codes}. "
            f"Expected consistent exit codes. Details: {command_details}"
        )
        
        # The most common exit code should be 1 (standard error)
        from collections import Counter
        code_counts = Counter(exit_codes)
        most_common_code = code_counts.most_common(1)[0][0]
        assert most_common_code == 1, (
            f"Expected most common exit code to be 1, but got {most_common_code}. "
            f"Code distribution: {dict(code_counts)}"
        )
    
    def test_error_message_informativeness(self):
        """Test that error messages contain sufficient information for debugging."""
        # Test each type of corruption with different commands
        error_scenarios = [
            # (generator_func, corruption_type, command, input_ext, output_ext, expected_keywords)
            (generate_corrupted_kml, KMLCorruption.MALFORMED_XML, 'kml-to-dxf-contours', 
             '.kml', '.dxf', ['error', 'xml', 'parse', 'malformed']),
            (generate_corrupted_kml, KMLCorruption.INVALID_COORDINATES, 'slope-heatmap', 
             '.kml', '.png', ['error', 'coordinate', 'invalid', 'value']),
            (generate_corrupted_csv, CSVCorruption.WRONG_COLUMNS, 'csv-to-kml', 
             '.csv', '.kml', ['error', 'column', 'missing', 'required']),
            (generate_corrupted_csv, CSVCorruption.INVALID_DATA_TYPES, 'csv-to-kml', 
             '.csv', '.kml', ['error', 'convert', 'invalid', 'type', 'supported', 'instances']),
            (generate_corrupted_csv, CSVCorruption.ENCODING_ISSUES, 'csv-to-kml', 
             '.csv', '.kml', ['error', 'encoding', 'decode', 'utf']),
        ]
        
        for generator_func, corruption_type, command, input_ext, output_ext, expected_keywords in error_scenarios:
            input_file = self.temp_path / f"test{input_ext}"
            output_file = self.temp_path / f"output{output_ext}"
            
            # Generate corrupted file
            if generator_func == generate_corrupted_kml:
                generator_func(input_file, corruption_type=corruption_type, point_count=5, seed=42)
            else:
                generator_func(input_file, corruption_type=corruption_type, row_count=5, seed=42)
            
            # Run command
            result = self.runner.invoke(cli, [command, str(input_file), str(output_file)])
            
            # Should fail
            assert result.exit_code != 0, (
                f"Command {command} should have failed for {corruption_type.value}"
            )
            
            # Error message should contain expected keywords (at least one)
            output_lower = result.output.lower()
            matching_keywords = [kw for kw in expected_keywords if kw in output_lower]
            assert len(matching_keywords) > 0, (
                f"Command {command} with {corruption_type.value} corruption "
                f"should contain at least one of {expected_keywords} in error message. "
                f"Actual output: {repr(result.output)}"
            )
            
            # Error message should not be empty
            assert len(result.output.strip()) > 0, (
                f"Command {command} should produce error output for {corruption_type.value}"
            )
    
    def test_error_message_structure(self):
        """Test that error messages follow a consistent structure."""
        # Generate a few corruption scenarios
        test_cases = [
            (generate_corrupted_kml, KMLCorruption.MALFORMED_XML, 'kml-to-dxf-contours', '.kml', '.dxf'),
            (generate_corrupted_csv, CSVCorruption.WRONG_COLUMNS, 'csv-to-kml', '.csv', '.kml'),
        ]
        
        error_patterns = []
        
        for generator_func, corruption_type, command, input_ext, output_ext in test_cases:
            input_file = self.temp_path / f"test{input_ext}"
            output_file = self.temp_path / f"output{output_ext}"
            
            # Generate corrupted file
            if generator_func == generate_corrupted_kml:
                generator_func(input_file, corruption_type=corruption_type, point_count=5, seed=42)
            else:
                generator_func(input_file, corruption_type=corruption_type, row_count=5, seed=42)
            
            # Run command
            result = self.runner.invoke(cli, [command, str(input_file), str(output_file)])
            
            assert result.exit_code != 0
            
            # Analyze error message structure
            output_lines = result.output.strip().split('\n')
            error_patterns.append({
                'command': command,
                'corruption': corruption_type.value,
                'line_count': len(output_lines),
                'starts_with_error': output_lines[0].lower().startswith('error'),
                'contains_colon': ':' in output_lines[0],
                'output': result.output
            })
        
        # Error messages should generally start with "Error"
        error_starters = [p for p in error_patterns if p['starts_with_error']]
        assert len(error_starters) >= len(error_patterns) // 2, (
            f"Expected most error messages to start with 'Error'. "
            f"Patterns: {error_patterns}"
        )
        
        # Error messages should contain colons (structured format)
        colon_messages = [p for p in error_patterns if p['contains_colon']]
        assert len(colon_messages) >= len(error_patterns) // 2, (
            f"Expected most error messages to contain colons for structure. "
            f"Patterns: {error_patterns}"
        )
    
    def test_no_stack_traces_in_error_output(self):
        """Test that error messages don't contain Python stack traces."""
        # Stack traces indicate unhandled exceptions, which are not user-friendly
        test_cases = [
            (generate_corrupted_kml, KMLCorruption.MALFORMED_XML, 'kml-to-dxf-contours', '.kml', '.dxf'),
            (generate_corrupted_csv, CSVCorruption.INVALID_DATA_TYPES, 'csv-to-kml', '.csv', '.kml'),
        ]
        
        for generator_func, corruption_type, command, input_ext, output_ext in test_cases:
            input_file = self.temp_path / f"test{input_ext}"
            output_file = self.temp_path / f"output{output_ext}"
            
            # Generate corrupted file
            if generator_func == generate_corrupted_kml:
                generator_func(input_file, corruption_type=corruption_type, point_count=5, seed=42)
            else:
                generator_func(input_file, corruption_type=corruption_type, row_count=5, seed=42)
            
            # Run command
            result = self.runner.invoke(cli, [command, str(input_file), str(output_file)])
            
            assert result.exit_code != 0
            
            # Should not contain Python stack trace indicators
            # Note: "line X, column Y" is a valid XML parsing error message, not a stack trace
            stack_trace_indicators = [
                'Traceback (most recent call last):',
                'File "/', 'File ".',  # Absolute and relative file paths in stack traces
                'TypeError:', 'ValueError:', 'AttributeError:',
                '  File ', '    at ',
                'raise ', 'in <module>'
            ]
            
            output = result.output
            for indicator in stack_trace_indicators:
                assert indicator not in output, (
                    f"Command {command} with {corruption_type.value} corruption "
                    f"should not expose stack traces. Found '{indicator}' in output: "
                    f"{repr(output)}"
                )


class TestExitCodeMeanings:
    """Test that exit codes have consistent meanings across commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_exit_code_zero_for_success(self):
        """Test that successful operations return exit code 0."""
        # Create valid input files
        valid_kml = self.temp_path / "valid.kml"
        valid_kml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0822035425683,37.42228990140251,10</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 2</name>
      <Point>
        <coordinates>-122.0844277547694,37.42220071045159,20</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>''')
        
        valid_csv = self.temp_path / "valid.csv"
        valid_csv.write_text("Longitude,Latitude,Elevation,Name\n-122.0822,37.4223,10.0,Point1\n-122.0844,37.4222,20.0,Point2\n")
        
        # Test successful operations
        success_tests = [
            ('kml-to-points', str(valid_kml), str(self.temp_path / 'points.csv'), ['--format', 'csv']),
            ('csv-to-kml', str(valid_csv), str(self.temp_path / 'output.kml')),
        ]
        
        for test_case in success_tests:
            if len(test_case) == 4:
                command, input_file, output_file, extra_args = test_case
                result = self.runner.invoke(cli, [command, input_file, output_file] + extra_args)
            else:
                command, input_file, output_file = test_case
                result = self.runner.invoke(cli, [command, input_file, output_file])
            
            assert result.exit_code == 0, (
                f"Command {command} should return exit code 0 for valid input. "
                f"Got exit code {result.exit_code}. Output: {repr(result.output)}"
            )
    
    def test_exit_code_nonzero_for_errors(self):
        """Test that all error conditions return non-zero exit codes."""
        # Test file not found
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours', 
            str(self.temp_path / 'nonexistent.kml'),
            str(self.temp_path / 'output.dxf')
        ])
        
        assert result.exit_code != 0, (
            "Command should return non-zero exit code when input file doesn't exist"
        )
        
        # Test corrupted input
        corrupted_kml = self.temp_path / "corrupted.kml"
        generate_corrupted_kml(
            corrupted_kml,
            corruption_type=KMLCorruption.MALFORMED_XML,
            point_count=5,
            seed=42
        )
        
        result = self.runner.invoke(cli, [
            'kml-to-dxf-contours',
            str(corrupted_kml),
            str(self.temp_path / 'output.dxf')
        ])
        
        assert result.exit_code != 0, (
            "Command should return non-zero exit code for corrupted input"
        )
        
        # Test invalid output path (directory doesn't exist)
        valid_kml = self.temp_path / "valid.kml"
        valid_kml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0822,37.4223,10</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>''')
        
        result = self.runner.invoke(cli, [
            'kml-to-points',
            str(valid_kml),
            str(self.temp_path / 'nonexistent_dir' / 'output.csv'),
            '--format', 'csv'
        ])
        
        assert result.exit_code != 0, (
            "Command should return non-zero exit code when output directory doesn't exist"
        )