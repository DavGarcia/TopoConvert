"""Pytest configuration and fixtures for TopoConvert testing."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Iterator, List, Tuple, Generator
import psutil
import time
import functools

from tests.edge_case_generators import (
    generate_large_point_dataset,
    generate_corrupted_kml,
    generate_corrupted_csv,
    KMLCorruption,
    CSVCorruption
)
from tests.benchmark_config import (
    BENCHMARK_THRESHOLDS,
    BenchmarkDatasets
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_kml_content():
    """Sample KML content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0822035425683,37.42228990140251,0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 2</name>
      <Point>
        <coordinates>-122.0844277547694,37.42220071045159,10</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """x,y,z,name
-122.0822035,37.4222899,0.0,Point 1
-122.0844278,37.4222007,10.0,Point 2
-122.0856534,37.4219842,20.0,Point 3
"""


@pytest.fixture
def sample_kml_file(temp_dir, sample_kml_content):
    """Create a sample KML file."""
    kml_path = temp_dir / "sample.kml"
    kml_path.write_text(sample_kml_content)
    return kml_path


@pytest.fixture
def sample_csv_file(temp_dir, sample_csv_content):
    """Create a sample CSV file."""
    csv_path = temp_dir / "sample.csv"
    csv_path.write_text(sample_csv_content)
    return csv_path


# Fixtures for test KML files
@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_kml(fixtures_dir):
    """Return path to simple 3-point KML file."""
    return fixtures_dir / "simple_3points.kml"


@pytest.fixture
def grid_kml(fixtures_dir):
    """Return path to 4x4 grid KML file."""
    return fixtures_dir / "grid_4x4.kml"


@pytest.fixture
def sparse_kml(fixtures_dir):
    """Return path to sparse data KML file."""
    return fixtures_dir / "sparse_data.kml"


@pytest.fixture
def steep_kml(fixtures_dir):
    """Return path to steep slope KML file."""
    return fixtures_dir / "steep_slope.kml"


@pytest.fixture
def no_elevation_kml(fixtures_dir):
    """Return path to no elevation KML file."""
    return fixtures_dir / "no_elevation.kml"


@pytest.fixture
def empty_kml(fixtures_dir):
    """Return path to empty KML file."""
    return fixtures_dir / "empty.kml"


@pytest.fixture
def invalid_coords_kml(fixtures_dir):
    """Return path to KML with invalid coordinates."""
    return fixtures_dir / "invalid_coords.kml"


# Edge case testing fixtures
@pytest.fixture
def large_point_dataset() -> List[Tuple[float, float, float]]:
    """Generate a large point dataset for stress testing."""
    return generate_large_point_dataset(
        count=1000,
        bounds=(-122.5, 37.7, -122.3, 37.8),  # San Francisco area
        elevation_range=(0, 500),
        seed=42  # Reproducible results
    )


@pytest.fixture
def very_large_point_dataset() -> List[Tuple[float, float, float]]:
    """Generate a very large point dataset for memory stress testing."""
    return generate_large_point_dataset(
        count=50000,
        bounds=(-122.5, 37.7, -122.3, 37.8),
        elevation_range=(0, 500),
        seed=42
    )


@pytest.fixture
def corrupted_kml_files(temp_dir) -> dict:
    """Generate various corrupted KML files for testing."""
    corrupted_files = {}
    
    for corruption_type in KMLCorruption:
        file_path = temp_dir / f"corrupted_{corruption_type.value}.kml"
        generate_corrupted_kml(
            file_path,
            corruption_type=corruption_type,
            point_count=5,
            seed=42
        )
        corrupted_files[corruption_type] = file_path
    
    return corrupted_files


@pytest.fixture
def corrupted_csv_files(temp_dir) -> dict:
    """Generate various corrupted CSV files for testing."""
    corrupted_files = {}
    
    for corruption_type in CSVCorruption:
        file_path = temp_dir / f"corrupted_{corruption_type.value}.csv"
        generate_corrupted_csv(
            file_path,
            corruption_type=corruption_type,
            row_count=5,
            seed=42
        )
        corrupted_files[corruption_type] = file_path
    
    return corrupted_files


class MemoryMonitor:
    """Context manager for monitoring memory usage during tests."""
    
    def __init__(self, max_memory_mb: float = None):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.initial_memory = None
        self.peak_memory = None
        self.final_memory = None
    
    def __enter__(self):
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        if self.max_memory_mb and self.peak_memory > self.max_memory_mb:
            raise MemoryError(
                f"Peak memory usage {self.peak_memory:.2f}MB exceeded "
                f"limit {self.max_memory_mb:.2f}MB"
            )
    
    def update_peak(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
    
    @property
    def memory_increase(self) -> float:
        """Get memory increase from initial to final."""
        if self.initial_memory is None or self.final_memory is None:
            return 0.0
        return self.final_memory - self.initial_memory


@pytest.fixture
def memory_monitor():
    """Fixture for memory monitoring."""
    return MemoryMonitor


@pytest.fixture
def extreme_coordinates() -> List[Tuple[float, float, float]]:
    """Generate points with extreme coordinate values for boundary testing."""
    return [
        # Near poles
        (0, 89.9, 0),
        (0, -89.9, 0),
        # Near antimeridian
        (179.9, 0, 0),
        (-179.9, 0, 0),
        # Very high elevations
        (0, 0, 8848),  # Everest height
        (0, 0, -428),  # Dead Sea level
        # Precision limits
        (123.123456789, 45.987654321, 1234.56789),
    ]


@pytest.fixture 
def minimal_datasets() -> dict:
    """Generate minimal datasets for boundary condition testing."""
    return {
        'single_point': [(0, 0, 0)],
        'two_points': [(0, 0, 0), (1, 1, 10)],
        'collinear_points': [(0, 0, 0), (1, 1, 5), (2, 2, 10)],
        'identical_points': [(0, 0, 0), (0, 0, 0), (0, 0, 0)],
        'zero_elevation': [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
    }


def memory_limit(max_memory_mb: float):
    """Decorator to enforce memory limits on test functions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with MemoryMonitor(max_memory_mb=max_memory_mb):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Performance benchmark configurations
@pytest.fixture(scope="session")
def benchmark_config():
    """Configuration for performance benchmarks."""
    return {
        'min_rounds': 3,
        'max_time': 10.0,  # seconds
        'disable_gc': True,
        'warmup': True,
        'warmup_iterations': 1,
    }


# Benchmark dataset fixtures
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


@pytest.fixture
def performance_thresholds():
    """Access to performance thresholds."""
    return BENCHMARK_THRESHOLDS