"""Utilities for generating edge case test data."""

import random
import tempfile
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Optional, Union
import xml.etree.ElementTree as ET
import pandas as pd


class KMLCorruption(Enum):
    """Types of KML file corruption for testing."""
    MALFORMED_XML = "malformed_xml"
    INVALID_COORDINATES = "invalid_coordinates"
    MISSING_ELEMENTS = "missing_elements"
    TRUNCATED_FILE = "truncated_file"


class CSVCorruption(Enum):
    """Types of CSV file corruption for testing."""
    WRONG_COLUMNS = "wrong_columns"
    INVALID_DATA_TYPES = "invalid_data_types"
    ENCODING_ISSUES = "encoding_issues"
    MISSING_HEADERS = "missing_headers"
    INCONSISTENT_ROWS = "inconsistent_rows"


class DXFCorruption(Enum):
    """Types of DXF file corruption for testing.
    
    Note: Currently TopoConvert CLI commands do not accept DXF as input,
    so these generators are provided for future functionality or testing
    DXF reading capabilities if they are added.
    """
    MALFORMED_HEADER = "malformed_header"
    INVALID_ENTITIES = "invalid_entities"
    MISSING_SECTIONS = "missing_sections"
    TRUNCATED_FILE = "truncated_file"
    INVALID_COORDINATES = "invalid_coordinates"


CorruptionType = Union[KMLCorruption, CSVCorruption, DXFCorruption]


def generate_large_point_dataset(
    count: int = 10000,
    bounds: Tuple[float, float, float, float] = (-180, -90, 180, 90),
    elevation_range: Tuple[float, float] = (0, 1000),
    seed: Optional[int] = None
) -> List[Tuple[float, float, float]]:
    """Generate large dataset of random points for stress testing.
    
    Args:
        count: Number of points to generate
        bounds: (min_x, min_y, max_x, max_y) coordinate bounds
        elevation_range: (min_elevation, max_elevation) range
        seed: Random seed for reproducible results
        
    Returns:
        List of (x, y, z) coordinate tuples
    """
    if seed is not None:
        random.seed(seed)
    
    min_x, min_y, max_x, max_y = bounds
    min_z, max_z = elevation_range
    
    points = []
    for _ in range(count):
        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)
        z = random.uniform(min_z, max_z)
        points.append((x, y, z))
    
    return points


def generate_corrupted_kml(
    output_path: Path,
    corruption_type: KMLCorruption,
    point_count: int = 10,
    seed: Optional[int] = None
) -> None:
    """Generate corrupted KML file for testing error handling.
    
    Args:
        output_path: Path where corrupted KML will be written
        corruption_type: Type of corruption to introduce
        point_count: Number of points in the base file
        seed: Random seed for reproducible results
    """
    if seed is not None:
        random.seed(seed)
    
    if corruption_type == KMLCorruption.MALFORMED_XML:
        _generate_malformed_xml_kml(output_path, point_count)
    elif corruption_type == KMLCorruption.INVALID_COORDINATES:
        _generate_invalid_coordinates_kml(output_path, point_count)
    elif corruption_type == KMLCorruption.MISSING_ELEMENTS:
        _generate_missing_elements_kml(output_path, point_count)
    elif corruption_type == KMLCorruption.TRUNCATED_FILE:
        _generate_truncated_kml(output_path, point_count)
    else:
        raise ValueError(f"Unknown KML corruption type: {corruption_type}")


def generate_corrupted_csv(
    output_path: Path,
    corruption_type: CSVCorruption,
    row_count: int = 10,
    seed: Optional[int] = None
) -> None:
    """Generate corrupted CSV file for testing error handling.
    
    Args:
        output_path: Path where corrupted CSV will be written
        corruption_type: Type of corruption to introduce
        row_count: Number of rows in the base file
        seed: Random seed for reproducible results
    """
    if seed is not None:
        random.seed(seed)
    
    if corruption_type == CSVCorruption.WRONG_COLUMNS:
        _generate_wrong_columns_csv(output_path, row_count)
    elif corruption_type == CSVCorruption.INVALID_DATA_TYPES:
        _generate_invalid_data_types_csv(output_path, row_count)
    elif corruption_type == CSVCorruption.ENCODING_ISSUES:
        _generate_encoding_issues_csv(output_path, row_count)
    elif corruption_type == CSVCorruption.MISSING_HEADERS:
        _generate_missing_headers_csv(output_path, row_count)
    elif corruption_type == CSVCorruption.INCONSISTENT_ROWS:
        _generate_inconsistent_rows_csv(output_path, row_count)
    else:
        raise ValueError(f"Unknown CSV corruption type: {corruption_type}")


def _generate_malformed_xml_kml(output_path: Path, point_count: int) -> None:
    """Generate KML with malformed XML structure."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Corrupted Test Data</name>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0822035425683,37.42228990140251,0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 2</name>
      <Point>
        <!-- Missing closing coordinates tag -->
        <coordinates>-122.084,37.423,10
      </Point>
    </Placemark>
    <!-- Missing closing Document tag -->
  </Document>
<!-- Missing closing kml tag -->'''
    
    output_path.write_text(content)


def _generate_invalid_coordinates_kml(output_path: Path, point_count: int) -> None:
    """Generate KML with invalid coordinate values."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Invalid Coordinates Test</name>'''
    
    invalid_coords = [
        "999,999,0",  # Out of valid lat/lon range
        "invalid,coordinates,here",  # Non-numeric
        "NaN,37.42,0",  # NaN values
        "-190,95,0",  # Beyond valid ranges
        "text,more_text,also_text",  # All text
    ]
    
    for i in range(min(point_count, len(invalid_coords))):
        content += f'''
    <Placemark>
      <name>Point {i+1}</name>
      <Point>
        <coordinates>{invalid_coords[i]}</coordinates>
      </Point>
    </Placemark>'''
    
    content += '''
  </Document>
</kml>'''
    
    output_path.write_text(content)


def _generate_missing_elements_kml(output_path: Path, point_count: int) -> None:
    """Generate KML with missing required elements."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <!-- Missing name element -->
      <Point>
        <!-- Missing coordinates element -->
      </Point>
    </Placemark>
    <Placemark>
      <name>Point 2</name>
      <!-- Missing Point element entirely -->
    </Placemark>
  </Document>
</kml>'''
    
    output_path.write_text(content)


def _generate_truncated_kml(output_path: Path, point_count: int) -> None:
    """Generate truncated KML file."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Truncated File</name>
    <Placemark>
      <name>Point 1</name>
      <Point>
        <coordinates>-122.0822035425683,37.42228990140251,0</coordin'''
    
    # Deliberately truncated
    output_path.write_text(content)


def _generate_wrong_columns_csv(output_path: Path, row_count: int) -> None:
    """Generate CSV with unexpected column structure."""
    # Use columns that don't match expected survey data format
    columns = ['id', 'description', 'color', 'size', 'category']
    
    data = []
    for i in range(row_count):
        row = [
            f"item_{i}",
            f"Description for item {i}",
            f"color_{i % 3}",
            random.randint(1, 10),
            f"category_{i % 2}"
        ]
        data.append(row)
    
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(output_path, index=False)


def _generate_invalid_data_types_csv(output_path: Path, row_count: int) -> None:
    """Generate CSV with invalid data types in coordinate columns."""
    data = []
    invalid_values = ['text', 'NaN', 'null', 'invalid', '##ERROR##']
    
    for i in range(row_count):
        # Mix valid and invalid values
        if i % 3 == 0:  # Every third row has invalid data
            x = random.choice(invalid_values)
            y = random.choice(invalid_values)
            z = random.choice(invalid_values)
        else:
            x = random.uniform(-180, 180)
            y = random.uniform(-90, 90)
            z = random.uniform(0, 1000)
        
        data.append([x, y, z])
    
    df = pd.DataFrame(data, columns=['Longitude', 'Latitude', 'Elevation'])
    df.to_csv(output_path, index=False)


def _generate_encoding_issues_csv(output_path: Path, row_count: int) -> None:
    """Generate CSV with encoding problems."""
    # Create content with mixed encodings and special characters
    content = "Longitude,Latitude,Elevation,Name\n"
    
    special_chars = ['café', 'naïve', 'résumé', 'Москва', '北京', '🌍']
    
    for i in range(row_count):
        x = random.uniform(-180, 180)
        y = random.uniform(-90, 90)
        z = random.uniform(0, 1000)
        name = random.choice(special_chars)
        
        content += f"{x},{y},{z},{name}\n"
    
    # Write with problematic encoding
    with open(output_path, 'wb') as f:
        # Mix of UTF-8 and Latin-1 bytes to create encoding confusion
        f.write(content[:50].encode('utf-8'))
        f.write(content[50:].encode('latin-1', errors='ignore'))


def _generate_missing_headers_csv(output_path: Path, row_count: int) -> None:
    """Generate CSV without header row."""
    data = []
    for i in range(row_count):
        x = random.uniform(-180, 180)
        y = random.uniform(-90, 90)
        z = random.uniform(0, 1000)
        data.append([x, y, z])
    
    # Write without header (just data rows)
    with open(output_path, 'w') as f:
        for row in data:
            f.write(f"{row[0]},{row[1]},{row[2]}\n")


def _generate_inconsistent_rows_csv(output_path: Path, row_count: int) -> None:
    """Generate CSV with inconsistent number of columns per row."""
    content = "Longitude,Latitude,Elevation,Name\n"
    
    for i in range(row_count):
        x = random.uniform(-180, 180)
        y = random.uniform(-90, 90)
        z = random.uniform(0, 1000)
        
        if i % 3 == 0:
            # Missing columns
            content += f"{x},{y}\n"
        elif i % 3 == 1:
            # Extra columns
            content += f"{x},{y},{z},name_{i},extra1,extra2\n"
        else:
            # Normal row
            content += f"{x},{y},{z},name_{i}\n"
    
    output_path.write_text(content)


def generate_corrupted_dxf(
    output_path: Path,
    corruption_type: DXFCorruption,
    entity_count: int = 10,
    seed: Optional[int] = None
) -> None:
    """Generate corrupted DXF files for testing.
    
    Note: Currently TopoConvert CLI commands do not accept DXF as input,
    so this is provided for future functionality or testing DXF reading
    capabilities if they are added.
    
    Args:
        output_path: Path where corrupted DXF file will be created
        corruption_type: Type of corruption to introduce
        entity_count: Number of entities to include
        seed: Random seed for reproducible results
    """
    if seed is not None:
        random.seed(seed)
    
    if corruption_type == DXFCorruption.MALFORMED_HEADER:
        _generate_malformed_header_dxf(output_path, entity_count)
    elif corruption_type == DXFCorruption.INVALID_ENTITIES:
        _generate_invalid_entities_dxf(output_path, entity_count)
    elif corruption_type == DXFCorruption.MISSING_SECTIONS:
        _generate_missing_sections_dxf(output_path, entity_count)
    elif corruption_type == DXFCorruption.TRUNCATED_FILE:
        _generate_truncated_dxf(output_path, entity_count)
    elif corruption_type == DXFCorruption.INVALID_COORDINATES:
        _generate_invalid_coordinates_dxf(output_path, entity_count)
    else:
        raise ValueError(f"Unknown DXF corruption type: {corruption_type}")


def _generate_malformed_header_dxf(output_path: Path, entity_count: int) -> None:
    """Generate DXF with malformed header section."""
    content = '''0
SECTION
2
HEADER
9
$ACADVER
1
AC1015
9
$INSBASE
10
0.0
20
0.0
30
INVALID_VALUE
<!-- This is not valid DXF syntax -->
0
ENDSEC
0
SECTION
2
ENTITIES
'''
    
    # Add some basic entities
    for i in range(entity_count):
        content += f'''0
POINT
8
0
10
{random.uniform(-100, 100)}
20
{random.uniform(-100, 100)}
30
{random.uniform(0, 100)}
'''
    
    content += '''0
ENDSEC
0
EOF'''
    
    output_path.write_text(content)


def _generate_invalid_entities_dxf(output_path: Path, entity_count: int) -> None:
    """Generate DXF with invalid entity definitions."""
    content = '''0
SECTION
2
HEADER
0
ENDSEC
0
SECTION
2
ENTITIES
'''
    
    invalid_entities = [
        "INVALID_ENTITY_TYPE",
        "POINT_WITH_BAD_CODES",
        "MALFORMED_LINE"
    ]
    
    for i in range(entity_count):
        if i % 3 == 0:
            # Invalid entity type
            content += f'''0
{random.choice(invalid_entities)}
8
0
10
invalid_coordinate
20
also_invalid
'''
        else:
            # Valid point for contrast
            content += f'''0
POINT
8
0
10
{random.uniform(-100, 100)}
20
{random.uniform(-100, 100)}
30
{random.uniform(0, 100)}
'''
    
    content += '''0
ENDSEC
0
EOF'''
    
    output_path.write_text(content)


def _generate_missing_sections_dxf(output_path: Path, entity_count: int) -> None:
    """Generate DXF with missing required sections."""
    # Missing HEADER section entirely
    content = '''0
SECTION
2
ENTITIES
'''
    
    # Add some entities
    for i in range(entity_count):
        content += f'''0
POINT
8
0
10
{random.uniform(-100, 100)}
20
{random.uniform(-100, 100)}
30
{random.uniform(0, 100)}
'''
    
    # Missing ENDSEC and EOF
    output_path.write_text(content)


def _generate_truncated_dxf(output_path: Path, entity_count: int) -> None:
    """Generate DXF file that is cut off mid-entity."""
    content = '''0
SECTION
2
HEADER
0
ENDSEC
0
SECTION
2
ENTITIES
0
POINT
8
0
10
50.0
20
25.0
30
10.0
0
POINT
8
0
10
75.0
20
'''
    
    # Truncate mid-entity (missing the rest)
    output_path.write_text(content)


def _generate_invalid_coordinates_dxf(output_path: Path, entity_count: int) -> None:
    """Generate DXF with invalid coordinate values."""
    content = '''0
SECTION
2
HEADER
0
ENDSEC
0
SECTION
2
ENTITIES
'''
    
    invalid_coords = ["NaN", "invalid", "text", "###ERROR###", "1e999"]
    
    for i in range(entity_count):
        # Mix valid and invalid coordinates
        if i % 2 == 0:
            content += f'''0
POINT
8
0
10
{random.choice(invalid_coords)}
20
{random.choice(invalid_coords)}
30
{random.choice(invalid_coords)}
'''
        else:
            content += f'''0
POINT
8
0
10
{random.uniform(-100, 100)}
20
{random.uniform(-100, 100)}
30
{random.uniform(0, 100)}
'''
    
    content += '''0
ENDSEC
0
EOF'''
    
    output_path.write_text(content)