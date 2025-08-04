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