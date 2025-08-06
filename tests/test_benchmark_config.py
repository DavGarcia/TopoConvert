"""Test benchmark configuration and utilities."""

import pytest
from pathlib import Path
import tempfile

from tests.benchmark_config import (
    BENCHMARK_THRESHOLDS,
    BenchmarkDatasets,
    BenchmarkThresholds,
    get_threshold,
    BenchmarkReporter
)


class TestBenchmarkThresholds:
    """Test benchmark threshold configuration."""
    
    def test_benchmark_thresholds_structure(self):
        """Test that benchmark thresholds are properly structured."""
        assert 'small_dataset' in BENCHMARK_THRESHOLDS
        assert 'medium_dataset' in BENCHMARK_THRESHOLDS
        assert 'large_dataset' in BENCHMARK_THRESHOLDS
        assert 'stress_dataset' in BENCHMARK_THRESHOLDS
        
        # Check small dataset has expected commands
        small_thresholds = BENCHMARK_THRESHOLDS['small_dataset']
        assert 'kml_to_dxf_contours' in small_thresholds
        assert 'kml_to_points' in small_thresholds
        assert 'csv_to_kml' in small_thresholds
    
    def test_get_threshold_function(self):
        """Test get_threshold utility function."""
        threshold = get_threshold('small_dataset', 'kml_to_dxf_contours')
        
        assert threshold is not None
        assert isinstance(threshold, BenchmarkThresholds)
        assert threshold.max_time_seconds > 0
        assert threshold.max_memory_mb > 0
        assert threshold.description != ""
    
    def test_get_threshold_invalid(self):
        """Test get_threshold with invalid parameters."""
        threshold = get_threshold('nonexistent_dataset', 'some_command')
        assert threshold is None
        
        threshold = get_threshold('small_dataset', 'nonexistent_command')
        assert threshold is None


class TestBenchmarkDatasets:
    """Test benchmark dataset generation."""
    
    def test_small_dataset_generation(self, temp_dir):
        """Test small dataset generation."""
        datasets = BenchmarkDatasets.small_dataset(temp_dir)
        
        assert 'kml' in datasets
        assert 'csv' in datasets
        
        kml_file = datasets['kml']
        csv_file = datasets['csv']
        
        assert kml_file.exists()
        assert csv_file.exists()
        
        # Check KML content
        kml_content = kml_file.read_text()
        assert '<?xml version="1.0"' in kml_content
        assert '<kml xmlns=' in kml_content
        assert '<coordinates>' in kml_content
        assert 'Small Dataset' in kml_content
        
        # Check CSV content
        csv_content = csv_file.read_text()
        lines = csv_content.strip().split('\n')
        assert lines[0] == 'x,y,z'  # Header
        assert len(lines) > 1  # Has data rows
    
    def test_medium_dataset_generation(self, temp_dir):
        """Test medium dataset generation."""
        datasets = BenchmarkDatasets.medium_dataset(temp_dir)
        
        assert 'kml' in datasets
        assert 'csv_part1' in datasets
        assert 'csv_part2' in datasets
        assert 'csv_part3' in datasets
        
        kml_file = datasets['kml']
        assert kml_file.exists()
        
        # Check that KML has more points than small dataset
        kml_content = kml_file.read_text()
        placemark_count = kml_content.count('<Placemark>')
        assert placemark_count == 500  # Medium dataset size
        
        # Check CSV parts exist and have content
        for i in range(1, 4):
            csv_file = datasets[f'csv_part{i}']
            assert csv_file.exists()
            csv_content = csv_file.read_text()
            lines = csv_content.strip().split('\n')
            assert len(lines) == 101  # 100 data rows + header
    
    def test_large_dataset_generation(self, temp_dir):
        """Test large dataset generation."""
        datasets = BenchmarkDatasets.large_dataset(temp_dir)
        
        assert 'kml' in datasets
        kml_file = datasets['kml']
        assert kml_file.exists()
        
        # Check that KML has large number of points
        kml_content = kml_file.read_text()
        placemark_count = kml_content.count('<Placemark>')
        assert placemark_count == 5000  # Large dataset size
    
    def test_stress_dataset_generation(self, temp_dir):
        """Test stress dataset generation."""
        datasets = BenchmarkDatasets.stress_dataset(temp_dir)
        
        assert 'kml' in datasets
        assert 'csv' in datasets
        
        kml_file = datasets['kml']
        csv_file = datasets['csv']
        
        assert kml_file.exists()
        assert csv_file.exists()
        
        # Check file sizes are reasonable for stress testing
        kml_size = kml_file.stat().st_size
        csv_size = csv_file.stat().st_size
        
        assert kml_size > 1024 * 1024  # At least 1MB
        assert csv_size > 500 * 1024   # At least 500KB
    
    def test_points_to_kml_conversion(self):
        """Test internal points to KML conversion."""
        points = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
        kml_content = BenchmarkDatasets._points_to_kml(points, "Test Document")
        
        assert '<?xml version="1.0"' in kml_content
        assert '<name>Test Document</name>' in kml_content
        assert '<coordinates>1.000000,2.000000,3.00</coordinates>' in kml_content
        assert '<coordinates>4.000000,5.000000,6.00</coordinates>' in kml_content
        assert kml_content.count('<Placemark>') == 2
    
    def test_points_to_csv_conversion(self):
        """Test internal points to CSV conversion."""
        points = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
        csv_content = BenchmarkDatasets._points_to_csv(points)
        
        lines = csv_content.strip().split('\n')
        assert lines[0] == 'x,y,z'
        assert lines[1] == '1.000000,2.000000,3.00'
        assert lines[2] == '4.000000,5.000000,6.00'


class TestBenchmarkReporter:
    """Test benchmark reporting functionality."""
    
    def test_benchmark_reporter_creation(self, temp_dir):
        """Test benchmark reporter creation."""
        results_file = temp_dir / "test_results.json"
        reporter = BenchmarkReporter(results_file)
        
        assert reporter.results_file == results_file
        assert reporter.results == []
    
    def test_add_result(self, temp_dir):
        """Test adding benchmark results."""
        results_file = temp_dir / "test_results.json"
        reporter = BenchmarkReporter(results_file)
        
        threshold = BenchmarkThresholds(5.0, 100.0, 50.0, "Test threshold")
        
        reporter.add_result(
            test_name="test_command",
            dataset_size="small_dataset",
            command="kml_to_points",
            execution_time=2.5,
            memory_usage=75.0,
            passed=True,
            threshold=threshold
        )
        
        assert len(reporter.results) == 1
        result = reporter.results[0]
        
        assert result['test_name'] == 'test_command'
        assert result['dataset_size'] == 'small_dataset'
        assert result['command'] == 'kml_to_points'
        assert result['execution_time'] == 2.5
        assert result['memory_usage'] == 75.0
        assert result['passed'] is True
        assert 'threshold' in result
    
    def test_save_and_load_results(self, temp_dir):
        """Test saving and loading benchmark results."""
        results_file = temp_dir / "test_results.json"
        reporter = BenchmarkReporter(results_file)
        
        # Add a result
        reporter.add_result(
            test_name="test_save_load",
            dataset_size="medium_dataset",
            command="csv_to_kml",
            execution_time=3.5,
            memory_usage=85.0,
            passed=True
        )
        
        # Save results
        reporter.save_results()
        assert results_file.exists()
        
        # Test content
        import json
        with open(results_file) as f:
            saved_data = json.load(f)
        
        assert len(saved_data) == 1
        assert saved_data[0]['test_name'] == 'test_save_load'
    
    def test_create_baseline(self, temp_dir):
        """Test baseline creation."""
        results_file = temp_dir / "test_results.json"
        reporter = BenchmarkReporter(results_file)
        
        reporter.add_result(
            test_name="baseline_test",
            dataset_size="small_dataset",
            command="kml_to_points",
            execution_time=1.0,
            memory_usage=50.0,
            passed=True
        )
        
        reporter.create_baseline()
        
        baseline_file = temp_dir / "benchmark_baseline.json"
        assert baseline_file.exists()
        
        import json
        with open(baseline_file) as f:
            baseline_data = json.load(f)
        
        assert len(baseline_data) == 1
        assert baseline_data[0]['test_name'] == 'baseline_test'


class TestBenchmarkFixtures:
    """Test benchmark fixture functionality."""
    
    def test_small_benchmark_data_fixture(self, small_benchmark_data):
        """Test small benchmark data fixture."""
        assert 'kml' in small_benchmark_data
        assert 'csv' in small_benchmark_data
        
        assert small_benchmark_data['kml'].exists()
        assert small_benchmark_data['csv'].exists()
    
    def test_medium_benchmark_data_fixture(self, medium_benchmark_data):
        """Test medium benchmark data fixture."""
        assert 'kml' in medium_benchmark_data
        assert 'csv_part1' in medium_benchmark_data
        
        for key, file_path in medium_benchmark_data.items():
            assert file_path.exists()
    
    def test_benchmark_config_fixture(self, benchmark_config):
        """Test benchmark configuration fixture."""
        assert 'min_rounds' in benchmark_config
        assert 'max_time' in benchmark_config
        assert 'warmup' in benchmark_config
        
        assert benchmark_config['min_rounds'] >= 1
        assert benchmark_config['max_time'] > 0
    
    def test_performance_thresholds_fixture(self, performance_thresholds):
        """Test performance thresholds fixture."""
        assert performance_thresholds is BENCHMARK_THRESHOLDS
        assert 'small_dataset' in performance_thresholds


class TestDatasetSizes:
    """Test dataset size consistency."""
    
    def test_dataset_size_progression(self, temp_dir):
        """Test that dataset sizes progress as expected."""
        small_data = BenchmarkDatasets.small_dataset(temp_dir)
        medium_data = BenchmarkDatasets.medium_dataset(temp_dir)
        large_data = BenchmarkDatasets.large_dataset(temp_dir)
        
        # Check KML file sizes
        small_size = small_data['kml'].stat().st_size
        medium_size = medium_data['kml'].stat().st_size
        large_size = large_data['kml'].stat().st_size
        
        assert small_size < medium_size < large_size
        
        # Check point counts by counting placemarks
        small_content = small_data['kml'].read_text()
        medium_content = medium_data['kml'].read_text()
        large_content = large_data['kml'].read_text()
        
        small_count = small_content.count('<Placemark>')
        medium_count = medium_content.count('<Placemark>')
        large_count = large_content.count('<Placemark>')
        
        assert small_count < medium_count < large_count
        assert small_count == 10
        assert medium_count == 500
        assert large_count == 5000