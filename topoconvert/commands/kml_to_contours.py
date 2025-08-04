"""Convert KML points to DXF contours."""
import click
from pathlib import Path
from topoconvert.core.contours import generate_contours
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the kml-to-dxf-contours command with the CLI."""
    @cli.command('kml-to-dxf-contours')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path(), required=False)
    @click.option('--interval', '-i', type=float, default=1.0,
                  help='Contour interval in feet (default: 1.0)')
    @click.option('--label/--no-label', default=True,
                  help='Add elevation labels to contours (default: label)')
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML (default: meters)')
    @click.option('--grid-resolution', type=int, default=100,
                  help='Grid density for interpolation (100 = 100x100 grid, higher = smoother contours, default: 100)')
    @click.option('--label-height', type=float, default=2.0,
                  help='Text size for elevation labels in drawing units (default: 2.0)')
    @click.option('--no-translate', is_flag=True,
                  help="Don't translate coordinates to origin (default: translate)")
    @click.option('--target-epsg', type=int, default=None,
                  help='Target EPSG code for projection (default: auto-detect UTM)')
    def kml_to_contours(input_file, output_file, interval, label, 
                       elevation_units, grid_resolution, label_height, no_translate,
                       target_epsg):
        """Convert KML points to DXF contours.
        
        INPUT_FILE: Path to input KML file containing point data
        OUTPUT_FILE: Path to output DXF file
        """
        
        try:
            input_path = Path(input_file)
            
            # Use provided output file or create default name
            if output_file is None:
                output_path = input_path.with_suffix('.dxf')
            else:
                output_path = Path(output_file)
            
            # Generate contours
            generate_contours(
                input_file=input_path,
                output_file=output_path,
                elevation_units=elevation_units,
                contour_interval=interval,
                grid_resolution=grid_resolution,
                add_labels=label,
                label_height=label_height,
                translate_to_origin=not no_translate,
                target_epsg=target_epsg,
                wgs84=False,  # Contour generation requires projected coordinates
                progress_callback=None
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Contour generation failed: {e}")