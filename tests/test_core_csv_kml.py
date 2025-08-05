"""Tests for CSV to KML conversion module."""
import pytest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from topoconvert.core.exceptions import FileFormatError, ProcessingError


def test_csv_kml_module_exists():
    """Test that csv_kml module can be imported."""
    try:
        from topoconvert.core import csv_kml
        assert hasattr(csv_kml, 'convert_csv_to_kml')
    except ImportError as e:
        pytest.fail(f"Failed to import csv_kml module: {e}")


def test_convert_csv_to_kml_validates_input():
    """Test that convert_csv_to_kml validates input file."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError, match="File not found"):
        convert_csv_to_kml(
            input_file=Path("nonexistent.csv"),
            output_file=Path("output.kml")
        )


def test_convert_csv_to_kml_validates_parameters(sample_csv_file):
    """Test parameter validation."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "output.kml"
        
        # Test invalid elevation units
        with pytest.raises(ValueError, match="elevation_units"):
            convert_csv_to_kml(
                input_file=sample_csv_file,
                output_file=output_file,
                elevation_units="invalid"
            )
        
        # Test invalid point style
        with pytest.raises(ValueError, match="point_style"):
            convert_csv_to_kml(
                input_file=sample_csv_file,
                output_file=output_file,
                point_style="invalid"
            )
        
        # Test invalid color format
        with pytest.raises(ValueError, match="color"):
            convert_csv_to_kml(
                input_file=sample_csv_file,
                output_file=output_file,
                point_color="invalid"
            )
        
        # Test invalid point scale
        with pytest.raises(ValueError, match="point_scale"):
            convert_csv_to_kml(
                input_file=sample_csv_file,
                output_file=output_file,
                point_scale=-1.0
            )


def test_convert_csv_to_kml_with_sample_data(sample_csv_file, temp_dir):
    """Test CSV to KML conversion with sample data."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    output_file = temp_dir / "output.kml"
    
    # Actually convert CSV to KML
    convert_csv_to_kml(
        input_file=sample_csv_file,
        output_file=output_file,
        x_column='x',
        y_column='y',
        z_column='z',
        elevation_units='meters',
        add_labels=True
    )
    
    # Verify output file was created
    assert output_file.exists()
    
    # Verify it's valid XML/KML
    tree = ET.parse(output_file)
    root = tree.getroot()
    assert 'kml' in root.tag
    
    # Check for placemarks
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    placemarks = root.findall('.//kml:Placemark', ns)
    assert len(placemarks) >= 2  # Sample CSV has at least 2 points


def test_convert_csv_to_kml_custom_columns(temp_dir):
    """Test conversion with custom column names."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Create CSV with custom column names
    csv_content = """lon,lat,alt,name
-122.0822035,37.4222899,100.0,Point 1
-122.0844278,37.4222007,110.0,Point 2
-122.0856534,37.4219842,120.0,Point 3
"""
    csv_file = temp_dir / "custom_columns.csv"
    csv_file.write_text(csv_content)
    
    output_file = temp_dir / "output.kml"
    
    convert_csv_to_kml(
        input_file=csv_file,
        output_file=output_file,
        x_column='lon',
        y_column='lat',
        z_column='alt'
    )
    
    assert output_file.exists()
    
    # Verify KML contains points
    tree = ET.parse(output_file)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    placemarks = root.findall('.//kml:Placemark', ns)
    assert len(placemarks) == 3
    
    # Check coordinates
    coordinates = root.findall('.//kml:coordinates', ns)
    assert len(coordinates) == 3
    # Verify first point has correct coordinates
    coord_text = coordinates[0].text.strip()
    # Should be longitude,latitude,elevation
    assert coord_text.startswith('-122.0822035,37.4222899')


def test_convert_csv_to_kml_empty_csv(temp_dir):
    """Test handling of empty CSV file."""
    # Create empty CSV
    csv_file = temp_dir / "empty.csv"
    csv_file.write_text("")
    
    output_file = temp_dir / "output.kml"
    
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    with pytest.raises(ProcessingError, match="No columns to parse from file"):
        convert_csv_to_kml(
            input_file=csv_file,
            output_file=output_file
        )


def test_convert_csv_to_kml_missing_columns(temp_dir):
    """Test handling of CSV with missing required columns."""
    # Create CSV without required columns
    csv_content = """name,value
Point 1,100
Point 2,200
"""
    csv_file = temp_dir / "missing_columns.csv"
    csv_file.write_text(csv_content)
    
    output_file = temp_dir / "output.kml"
    
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    with pytest.raises(ProcessingError, match="Missing required columns"):
        convert_csv_to_kml(
            input_file=csv_file,
            output_file=output_file
        )


def test_convert_csv_to_kml_invalid_coordinates(temp_dir):
    """Test handling of invalid coordinate values."""
    # Create CSV with invalid coordinates
    csv_content = """x,y,z,name
invalid,37.4222899,100.0,Point 1
-122.0844278,invalid,110.0,Point 2
"""
    csv_file = temp_dir / "invalid_coords.csv"
    csv_file.write_text(csv_content)
    
    output_file = temp_dir / "output.kml"
    
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Invalid coordinates will be caught during writing phase
    with pytest.raises(ProcessingError, match="Error writing KML"):
        convert_csv_to_kml(
            input_file=csv_file,
            output_file=output_file,
            x_column='x',
            y_column='y',
            z_column='z'
        )


def test_convert_csv_to_kml_styling_options(sample_csv_file, temp_dir):
    """Test various styling options."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    output_file = temp_dir / "styled.kml"
    
    convert_csv_to_kml(
        input_file=sample_csv_file,
        output_file=output_file,
        x_column='x',
        y_column='y',
        z_column='z',
        point_style='pin',
        point_color='ff0000ff',  # Red
        point_scale=1.5,
        add_labels=False,
        kml_name='Test Points'
    )
    
    assert output_file.exists()
    
    # Verify style elements in KML
    tree = ET.parse(output_file)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # Check document name
    doc_name = root.find('.//kml:Document/kml:name', ns)
    assert doc_name is not None
    assert doc_name.text == 'Test Points'
    
    # Check for style elements
    styles = root.findall('.//kml:Style', ns)
    assert len(styles) > 0


def test_convert_csv_to_kml_elevation_units(sample_csv_file, temp_dir):
    """Test elevation unit conversion."""
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Test with meters
    output_meters = temp_dir / "meters.kml"
    convert_csv_to_kml(
        input_file=sample_csv_file,
        output_file=output_meters,
        x_column='x',
        y_column='y',
        z_column='z',
        elevation_units='meters'
    )
    
    # Test with feet
    output_feet = temp_dir / "feet.kml"
    convert_csv_to_kml(
        input_file=sample_csv_file,
        output_file=output_feet,
        x_column='x',
        y_column='y',
        z_column='z',
        elevation_units='feet'
    )
    
    assert output_meters.exists()
    assert output_feet.exists()
    
    # The actual elevation values should differ by conversion factor
    # but both files should be valid KML


def test_convert_csv_to_kml_missing_elevation_graceful(temp_dir):
    """Test graceful handling of missing elevation column."""
    # Create CSV without elevation column
    csv_content = """x,y,name
-122.0822035,37.4222899,Point 1
-122.0844278,37.4222007,Point 2
"""
    csv_file = temp_dir / "no_elevation.csv"
    csv_file.write_text(csv_content)
    
    output_file = temp_dir / "output.kml"
    
    from topoconvert.core.csv_kml import convert_csv_to_kml
    
    # Should handle missing elevation gracefully (use 0)
    convert_csv_to_kml(
        input_file=csv_file,
        output_file=output_file,
        x_column='x',
        y_column='y',
        z_column='z'  # Column doesn't exist
    )
    
    assert output_file.exists()
    
    # Verify KML has points with zero elevation
    tree = ET.parse(output_file)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    coordinates = root.findall('.//kml:coordinates', ns)
    assert len(coordinates) == 2
    
    # Check that elevation defaults to 0
    for coord in coordinates:
        coord_parts = coord.text.strip().split(',')
        assert len(coord_parts) == 3
        assert float(coord_parts[2]) == 0.0