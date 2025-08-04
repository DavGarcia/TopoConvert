"""Extract point data from KML files."""
import click
from pathlib import Path
from topoconvert.core.points import extract_points
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the kml-to-points command with the CLI."""
    @cli.command('kml-to-points')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path(), required=False)
    @click.option('--format', '-f', type=click.Choice(['dxf', 'csv', 'json', 'txt']),
                  default='csv', help='Output format (default: csv)')
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML (default: meters)')
    @click.option('--translate/--no-translate', default=True,
                  help='Translate coordinates to origin (DXF only, default: translate)')
    @click.option('--use-reference-point', is_flag=True,
                  help='Use first point as reference for translation (DXF only)')
    @click.option('--layer-name', default='GPS_POINTS',
                  help='Layer name for DXF output (default: GPS_POINTS)')
    @click.option('--point-color', type=int, default=7,
                  help='AutoCAD color index for DXF points (default: 7)')
    def kml_to_points(input_file, output_file, format, elevation_units, translate,
                     use_reference_point, layer_name, point_color):
        """Extract point data from KML files.
        
        Extract points from KML and save in various formats including DXF 3D point cloud,
        CSV with lat/lon/elevation, JSON structured data, or plain text format.
        
        INPUT_FILE: Path to input KML file
        OUTPUT_FILE: Path to output file (optional, defaults to input name with new extension)
        """
        try:
            input_path = Path(input_file)
            
            # Generate default output filename if not provided
            if output_file is None:
                extension_map = {
                    'dxf': '.dxf',
                    'csv': '.csv',
                    'json': '.json',
                    'txt': '.txt'
                }
                output_path = input_path.with_suffix(extension_map[format])
            else:
                output_path = Path(output_file)
            
            # Extract points
            extract_points(
                input_file=input_path,
                output_file=output_path,
                output_format=format,
                elevation_units=elevation_units,
                translate_to_origin=translate,
                use_reference_point=use_reference_point,
                layer_name=layer_name,
                point_color=point_color,
                progress_callback=None
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Point extraction failed: {e}")