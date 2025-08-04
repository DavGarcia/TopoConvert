"""Merge multiple CSV files into a single KML with folders."""
import click
import pandas as pd
from pathlib import Path
from typing import List, Optional, Callable, Tuple
from xml.etree import ElementTree as ET
from xml.dom import minidom

from topoconvert.core.exceptions import ProcessingError, TopoConvertError


# Color palette for different datasets (AABBGGRR format)
KML_COLORS = [
    'ff0080ff',  # Orange
    'ff00ff00',  # Green  
    'ffff0000',  # Blue
    'ff00ffff',  # Yellow
    'ffff00ff',  # Magenta
    'ff0000ff',  # Red
    'ffffff00',  # Cyan
    'ff800080',  # Purple
    'ff008080',  # Olive
    'ff808000',  # Teal
]

# Icon styles for different datasets
ICON_STYLES = [
    'http://maps.google.com/mapfiles/kml/paddle/1.png',
    'http://maps.google.com/mapfiles/kml/paddle/2.png',
    'http://maps.google.com/mapfiles/kml/paddle/3.png',
    'http://maps.google.com/mapfiles/kml/paddle/4.png',
    'http://maps.google.com/mapfiles/kml/paddle/5.png',
    'http://maps.google.com/mapfiles/kml/paddle/6.png',
    'http://maps.google.com/mapfiles/kml/paddle/7.png',
    'http://maps.google.com/mapfiles/kml/paddle/8.png',
    'http://maps.google.com/mapfiles/kml/paddle/9.png',
    'http://maps.google.com/mapfiles/kml/paddle/10.png',
]


def merge_csv_to_kml(
    csv_files: List[Path],
    output_file: Path,
    elevation_units: str = 'meters',
    point_scale: float = 1.0,
    add_labels: bool = True,
    x_column: str = 'Longitude',
    y_column: str = 'Latitude', 
    z_column: str = 'Elevation',
    progress_callback: Optional[Callable] = None
) -> None:
    """
    Merge multiple CSV files into a single KML with separate folders.
    
    Args:
        csv_files: List of input CSV file paths
        output_file: Output KML file path
        elevation_units: Units of elevation in CSV files
        point_scale: Scale factor for point icons
        add_labels: Whether to add labels to placemarks
        x_column: Column name for X coordinate
        y_column: Column name for Y coordinate
        z_column: Column name for Z coordinate
        progress_callback: Optional progress callback
    """
    if not csv_files:
        raise ProcessingError("No CSV files provided")
    
    # Create KML root elements
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')
    
    # Add document name
    doc_name = ET.SubElement(document, 'name')
    doc_name.text = output_file.stem
    
    # Add description
    doc_desc = ET.SubElement(document, 'description')
    doc_desc.text = f'Combined survey data from {len(csv_files)} CSV files'
    
    # Create styles for each dataset
    for idx in range(len(csv_files)):
        color = KML_COLORS[idx % len(KML_COLORS)]
        icon_href = ICON_STYLES[idx % len(ICON_STYLES)]
        
        # Create style for points
        style = ET.SubElement(document, 'Style', id=f'pointStyle{idx}')
        icon_style = ET.SubElement(style, 'IconStyle')
        color_elem = ET.SubElement(icon_style, 'color')
        color_elem.text = color
        scale_elem = ET.SubElement(icon_style, 'scale')
        scale_elem.text = str(point_scale)
        icon = ET.SubElement(icon_style, 'Icon')
        href = ET.SubElement(icon, 'href')
        href.text = icon_href
        
        # Label style
        label_style = ET.SubElement(style, 'LabelStyle')
        label_color = ET.SubElement(label_style, 'color')
        label_color.text = color
        label_scale = ET.SubElement(label_style, 'scale')
        label_scale.text = str(0.7)
    
    # Process each CSV file
    total_points = 0
    
    for idx, csv_file in enumerate(csv_files):
        if progress_callback:
            progress = int((idx / len(csv_files)) * 90)
            progress_callback(f"Processing {csv_file.name}", progress)
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            
            # Validate columns
            for col in [x_column, y_column, z_column]:
                if col not in df.columns:
                    raise ProcessingError(f"Column '{col}' not found in {csv_file.name}")
            
            # Create folder for this dataset
            folder = ET.SubElement(document, 'Folder')
            folder_name = ET.SubElement(folder, 'name')
            folder_name.text = csv_file.stem
            
            folder_desc = ET.SubElement(folder, 'description')
            folder_desc.text = f'{len(df)} points from {csv_file.name}'
            
            # Add placemarks for each point
            for idx_point, row in df.iterrows():
                placemark = ET.SubElement(folder, 'Placemark')
                
                # Name
                name = ET.SubElement(placemark, 'name')
                if add_labels:
                    # Try to use point ID or number
                    if 'Name' in df.columns and pd.notna(row['Name']):
                        name.text = str(row['Name'])
                    elif 'ID' in df.columns and pd.notna(row['ID']):
                        name.text = f"Point {row['ID']}"
                    else:
                        name.text = f"Point {idx_point + 1}"
                else:
                    name.text = ""
                
                # Style reference
                style_url = ET.SubElement(placemark, 'styleUrl')
                style_url.text = f'#pointStyle{idx}'
                
                # Add extended data for all columns
                extended_data = ET.SubElement(placemark, 'ExtendedData')
                for col in df.columns:
                    if pd.notna(row[col]):
                        data = ET.SubElement(extended_data, 'Data', name=col)
                        value = ET.SubElement(data, 'value')
                        value.text = str(row[col])
                
                # Point coordinates
                point = ET.SubElement(placemark, 'Point')
                
                # Altitude mode
                altitude_mode = ET.SubElement(point, 'altitudeMode')
                altitude_mode.text = 'relativeToGround'
                
                # Coordinates (lon,lat,elevation)
                coords = ET.SubElement(point, 'coordinates')
                
                # Convert elevation if needed
                elevation = float(row[z_column])
                if elevation_units == 'feet':
                    elevation *= 0.3048  # Convert to meters for KML
                
                coords.text = f"{row[x_column]},{row[y_column]},{elevation}"
            
            total_points += len(df)
            click.echo(f"Processed {csv_file.stem}: {len(df)} points")
            
        except Exception as e:
            raise ProcessingError(f"Error processing {csv_file.name}: {e}")
    
    if progress_callback:
        progress_callback("Writing KML file", 95)
    
    # Pretty print the KML
    kml_str = ET.tostring(kml, encoding='unicode')
    dom = minidom.parseString(kml_str)
    pretty_kml = dom.toprettyxml(indent='  ')
    
    # Remove extra blank lines
    lines = [line for line in pretty_kml.split('\n') if line.strip()]
    pretty_kml = '\n'.join(lines)
    
    # Write to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_kml)
    except Exception as e:
        raise ProcessingError(f"Failed to write KML file: {e}")
    
    # Summary
    click.echo(f"\nCreated combined KML: {output_file}")
    click.echo(f"- {len(csv_files)} input files in separate folders")
    click.echo(f"- {total_points} total points")
    click.echo(f"- Each dataset has unique icon and color")
    if elevation_units == 'feet':
        click.echo(f"- Elevations converted from feet to meters")