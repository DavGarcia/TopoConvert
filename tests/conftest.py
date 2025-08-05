"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path
import tempfile
import shutil


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