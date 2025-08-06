"""Configuration and utilities for performance benchmarking."""

import pytest
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import tempfile
from dataclasses import dataclass, asdict

from tests.edge_case_generators import generate_large_point_dataset


@dataclass
class BenchmarkThresholds:
    """Performance thresholds for different operations."""
    max_time_seconds: float
    max_memory_mb: float
    max_memory_increase_mb: float
    description: str


# Performance thresholds for different commands and dataset sizes
BENCHMARK_THRESHOLDS = {
    # Small datasets (< 100 points)
    'small_dataset': {
        'kml_to_dxf_contours': BenchmarkThresholds(2.0, 50, 20, "Contour generation from small KML"),
        'kml_to_dxf_mesh': BenchmarkThresholds(3.0, 60, 30, "Mesh generation from small KML"),
        'kml_to_points': BenchmarkThresholds(1.0, 30, 10, "Point extraction from small KML"),
        'csv_to_kml': BenchmarkThresholds(1.0, 30, 10, "CSV to KML conversion"),
        'slope_heatmap': BenchmarkThresholds(5.0, 80, 40, "Slope heatmap from small dataset"),
    },
    
    # Medium datasets (100-1000 points)
    'medium_dataset': {
        'kml_to_dxf_contours': BenchmarkThresholds(10.0, 100, 50, "Contour generation from medium KML"),
        'kml_to_dxf_mesh': BenchmarkThresholds(15.0, 120, 60, "Mesh generation from medium KML"),
        'kml_to_points': BenchmarkThresholds(3.0, 60, 30, "Point extraction from medium KML"),
        'multi_csv_to_dxf': BenchmarkThresholds(5.0, 80, 40, "Multiple CSV to DXF combination"),
        'multi_csv_to_kml': BenchmarkThresholds(5.0, 80, 40, "Multiple CSV to KML combination"),
        'slope_heatmap': BenchmarkThresholds(20.0, 150, 80, "Slope heatmap from medium dataset"),
    },
    
    # Large datasets (1000-10000 points)
    'large_dataset': {
        'kml_to_dxf_contours': BenchmarkThresholds(60.0, 300, 200, "Contour generation from large KML"),
        'kml_to_dxf_mesh': BenchmarkThresholds(90.0, 400, 250, "Mesh generation from large KML"),
        'kml_to_points': BenchmarkThresholds(15.0, 150, 100, "Point extraction from large KML"),
        'slope_heatmap': BenchmarkThresholds(120.0, 500, 300, "Slope heatmap from large dataset"),
    },
    
    # Stress test datasets (10000+ points)
    'stress_dataset': {
        'kml_to_points': BenchmarkThresholds(60.0, 500, 400, "Point extraction stress test"),
        'csv_to_kml': BenchmarkThresholds(30.0, 300, 200, "CSV to KML stress test"),
    }
}


class BenchmarkDatasets:
    """Generator for standardized benchmark datasets."""
    
    @staticmethod
    def small_dataset(temp_dir: Path) -> Dict[str, Path]:
        """Generate small dataset files for benchmarking."""
        datasets = {}
        
        # Small KML (10 points)
        points = generate_large_point_dataset(
            count=10,
            bounds=(-122.5, 37.7, -122.3, 37.8),
            elevation_range=(0, 100),
            seed=42
        )
        kml_content = BenchmarkDatasets._points_to_kml(points, "Small Dataset")
        kml_file = temp_dir / "small_dataset.kml"
        kml_file.write_text(kml_content)
        datasets['kml'] = kml_file
        
        # Small CSV
        csv_content = BenchmarkDatasets._points_to_csv(points[:5])
        csv_file = temp_dir / "small_dataset.csv"
        csv_file.write_text(csv_content)
        datasets['csv'] = csv_file
        
        return datasets
    
    @staticmethod
    def medium_dataset(temp_dir: Path) -> Dict[str, Path]:
        """Generate medium dataset files for benchmarking."""
        datasets = {}
        
        # Medium KML (500 points)
        points = generate_large_point_dataset(
            count=500,
            bounds=(-122.5, 37.7, -122.3, 37.8),
            elevation_range=(0, 200),
            seed=42
        )
        kml_content = BenchmarkDatasets._points_to_kml(points, "Medium Dataset")
        kml_file = temp_dir / "medium_dataset.kml"
        kml_file.write_text(kml_content)
        datasets['kml'] = kml_file
        
        # Multiple CSV files for multi-file operations
        chunk_size = 100
        for i in range(3):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size
            chunk_points = points[start_idx:end_idx]
            csv_content = BenchmarkDatasets._points_to_csv(chunk_points)
            csv_file = temp_dir / f"medium_dataset_part{i+1}.csv"
            csv_file.write_text(csv_content)
            datasets[f'csv_part{i+1}'] = csv_file
        
        return datasets
    
    @staticmethod
    def large_dataset(temp_dir: Path) -> Dict[str, Path]:
        """Generate large dataset files for benchmarking."""
        datasets = {}
        
        # Large KML (5000 points)
        points = generate_large_point_dataset(
            count=5000,
            bounds=(-122.5, 37.7, -122.3, 37.8),
            elevation_range=(0, 500),
            seed=42
        )
        kml_content = BenchmarkDatasets._points_to_kml(points, "Large Dataset")
        kml_file = temp_dir / "large_dataset.kml"
        kml_file.write_text(kml_content)
        datasets['kml'] = kml_file
        
        return datasets
    
    @staticmethod
    def stress_dataset(temp_dir: Path) -> Dict[str, Path]:
        """Generate stress test dataset files for benchmarking."""
        datasets = {}
        
        # Stress test KML (50000 points)
        points = generate_large_point_dataset(
            count=50000,
            bounds=(-122.5, 37.7, -122.3, 37.8),
            elevation_range=(0, 1000),
            seed=42
        )
        kml_content = BenchmarkDatasets._points_to_kml(points, "Stress Test Dataset")
        kml_file = temp_dir / "stress_dataset.kml"
        kml_file.write_text(kml_content)
        datasets['kml'] = kml_file
        
        # Large CSV for stress testing
        csv_content = BenchmarkDatasets._points_to_csv(points[:20000])
        csv_file = temp_dir / "stress_dataset.csv"
        csv_file.write_text(csv_content)
        datasets['csv'] = csv_file
        
        return datasets
    
    @staticmethod
    def _points_to_kml(points: List[tuple], document_name: str) -> str:
        """Convert points to KML format."""
        kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{document_name}</name>'''
        
        for i, (x, y, z) in enumerate(points):
            kml_content += f'''
    <Placemark>
      <name>Point {i+1}</name>
      <Point>
        <coordinates>{x:.6f},{y:.6f},{z:.2f}</coordinates>
      </Point>
    </Placemark>'''
        
        kml_content += '''
  </Document>
</kml>'''
        return kml_content
    
    @staticmethod
    def _points_to_csv(points: List[tuple]) -> str:
        """Convert points to CSV format."""
        csv_content = "x,y,z\n"
        for x, y, z in points:
            csv_content += f"{x:.6f},{y:.6f},{z:.2f}\n"
        return csv_content


# Pytest fixtures for benchmark datasets
@pytest.fixture
def small_benchmark_data(temp_dir):
    """Small dataset for performance baseline."""
    return BenchmarkDatasets.small_dataset(temp_dir)


@pytest.fixture
def medium_benchmark_data(temp_dir):
    """Medium dataset for performance testing."""
    return BenchmarkDatasets.medium_dataset(temp_dir)


@pytest.fixture
def large_benchmark_data(temp_dir):
    """Large dataset for performance testing."""
    return BenchmarkDatasets.large_dataset(temp_dir)


@pytest.fixture
def stress_benchmark_data(temp_dir):
    """Stress test dataset for memory and performance limits."""
    return BenchmarkDatasets.stress_dataset(temp_dir)


# Benchmark configuration fixtures
@pytest.fixture(scope="session")
def benchmark_config():
    """Configuration for pytest-benchmark."""
    return {
        'min_rounds': 3,
        'max_time': 30.0,  # Max 30 seconds per benchmark
        'min_time': 0.1,   # Min 100ms per benchmark
        'warmup': True,
        'warmup_iterations': 1,
        'disable_gc': True,
        'sort': 'mean',
        'group_by': 'func',
        'compare': {
            'fail_if_slower': 0.5,  # Fail if 50% slower than baseline
            'fail_if_faster': False,
        }
    }


@pytest.fixture
def performance_thresholds():
    """Access to performance thresholds."""
    return BENCHMARK_THRESHOLDS


def get_threshold(dataset_size: str, command: str) -> Optional[BenchmarkThresholds]:
    """Get performance threshold for a specific command and dataset size."""
    if dataset_size in BENCHMARK_THRESHOLDS:
        return BENCHMARK_THRESHOLDS[dataset_size].get(command)
    return None


class BenchmarkReporter:
    """Utility for reporting benchmark results."""
    
    def __init__(self, results_file: Optional[Path] = None):
        self.results_file = results_file or Path("benchmark_results.json")
        self.results = []
    
    def add_result(
        self,
        test_name: str,
        dataset_size: str,
        command: str,
        execution_time: float,
        memory_usage: float,
        passed: bool,
        threshold: Optional[BenchmarkThresholds] = None
    ):
        """Add a benchmark result."""
        result = {
            'test_name': test_name,
            'dataset_size': dataset_size,
            'command': command,
            'execution_time': execution_time,
            'memory_usage': memory_usage,
            'passed': passed,
            'timestamp': pytest.current_time if hasattr(pytest, 'current_time') else 0,
        }
        
        if threshold:
            result['threshold'] = asdict(threshold)
        
        self.results.append(result)
    
    def save_results(self):
        """Save benchmark results to file."""
        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def load_baseline(self) -> Optional[Dict]:
        """Load baseline results for comparison."""
        baseline_file = self.results_file.parent / "benchmark_baseline.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        return None
    
    def create_baseline(self):
        """Create a new baseline from current results."""
        baseline_file = self.results_file.parent / "benchmark_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(self.results, f, indent=2)


# Pytest benchmark helper decorators
def benchmark_command(dataset_size: str, command: str, memory_limit_mb: Optional[float] = None):
    """Decorator for benchmarking CLI commands."""
    def decorator(func):
        def wrapper(benchmark, performance_thresholds, *args, **kwargs):
            threshold = get_threshold(dataset_size, command)
            
            # Set memory limit if specified
            if memory_limit_mb:
                import psutil
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024
            
            # Run benchmark
            result = benchmark(func, *args, **kwargs)
            
            # Check thresholds
            if threshold:
                if benchmark.stats.mean > threshold.max_time_seconds:
                    pytest.fail(
                        f"Benchmark exceeded time threshold: "
                        f"{benchmark.stats.mean:.2f}s > {threshold.max_time_seconds}s"
                    )
            
            return result
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# Configuration for CI/CD integration
CI_BENCHMARK_CONFIG = {
    'small_dataset': {
        'timeout': 60,  # 1 minute
        'memory_limit': 100,  # 100MB
    },
    'medium_dataset': {
        'timeout': 300,  # 5 minutes
        'memory_limit': 200,  # 200MB
    },
    'large_dataset': {
        'timeout': 600,  # 10 minutes
        'memory_limit': 500,  # 500MB
    },
    'stress_dataset': {
        'timeout': 1200,  # 20 minutes
        'memory_limit': 1000,  # 1GB
    }
}