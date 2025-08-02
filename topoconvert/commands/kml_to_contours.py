"""Convert KML points to DXF contours."""
import click
from pathlib import Path
from topoconvert.core.contours import generate_contours
from topoconvert.core.exceptions import TopoConvertError
from topoconvert.core.utils import create_progress_callback


def register(cli):
    """Register the kml-to-contours command with the CLI."""
    @cli.command('kml-to-contours')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--interval', '-i', type=float, default=1.0,
                  help='Contour interval in feet')
    @click.option('--label/--no-label', default=True,
                  help='Add elevation labels to contours')
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML')
    @click.option('--grid-resolution', type=int, default=100,
                  help='Grid resolution for interpolation')
    @click.option('--label-height', type=float, default=2.0,
                  help='Text height for labels')
    @click.option('--no-translate', is_flag=True,
                  help="Don't translate coordinates to origin")
    def kml_to_contours(input_file, output_file, interval, label, 
                       elevation_units, grid_resolution, label_height, no_translate):
        """Convert KML points to DXF contours.
        
        INPUT_FILE: Path to input KML file containing point data
        OUTPUT_FILE: Path to output DXF file
        """
        try:
            # Create progress callback
            progress = create_progress_callback("Generating contours", length=100)
            
            # Generate contours
            generate_contours(
                input_file=Path(input_file),
                output_file=Path(output_file),
                elevation_units=elevation_units,
                contour_interval=interval,
                grid_resolution=grid_resolution,
                add_labels=label,
                label_height=label_height,
                translate_to_origin=not no_translate,
                progress_callback=progress
            )
            
            # Close progress bar
            if hasattr(progress, 'close'):
                progress.close()
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Contour generation failed: {e}")