"""Convert KML contour lines to DXF format."""
import click
from pathlib import Path
from topoconvert.core.kml_contours import convert_kml_contours_to_dxf
from topoconvert.core.exceptions import TopoConvertError
from topoconvert.core.utils import create_progress_callback


def register(cli):
    """Register the kml-contours-to-dxf command with the CLI."""
    @cli.command('kml-contours-to-dxf')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--z-source', type=click.Choice(['auto', 'altitude', 'extended']),
                  default='auto',
                  help='Where to read contour elevation from')
    @click.option('--z-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML')
    @click.option('--target-epsg', type=int, default=26914,
                  help='EPSG code for projection (default: 26914 for UTM Zone 14N)')
    @click.option('--add-labels', is_flag=True,
                  help='Add text labels with elevation values')
    @click.option('--layer-prefix', default='CT_',
                  help='Prefix for per-elevation layers')
    @click.option('--decimals', type=int, default=1,
                  help='Decimal places for elevation text and layer names')
    @click.option('--z-field', default=None,
                  help='ExtendedData field name for elevation')
    @click.option('--altitude-tolerance', type=float, default=1e-6,
                  help='Tolerance for constant altitude along contour')
    @click.option('--translate/--no-translate', default=True,
                  help='Translate coordinates to origin')
    @click.option('--target-epsg-feet', is_flag=True,
                  help='Target EPSG coordinates are in feet')
    def kml_contours_to_dxf(input_file, output_file, z_source, z_units, target_epsg,
                           add_labels, layer_prefix, decimals, z_field, 
                           altitude_tolerance, translate, target_epsg_feet):
        """Convert KML contour LineStrings to DXF format.
        
        Reads KML files with LineString elements representing contour lines.
        Determines elevation from coordinate altitudes or ExtendedData fields.
        Creates separate layers for each elevation and optionally adds text labels.
        
        INPUT_FILE: Path to input KML file with contour lines
        OUTPUT_FILE: Path to output DXF file
        """
        try:
            # Create progress callback
            progress = create_progress_callback("Converting contours", length=100)
            
            # Convert KML contours to DXF
            convert_kml_contours_to_dxf(
                input_file=Path(input_file),
                output_file=Path(output_file),
                z_source=z_source,
                z_units=z_units,
                target_epsg=target_epsg,
                add_labels=add_labels,
                layer_prefix=layer_prefix,
                decimals=decimals,
                z_field=z_field,
                altitude_tolerance=altitude_tolerance,
                translate_to_origin=translate,
                target_epsg_feet=target_epsg_feet,
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
            raise click.ClickException(f"Contour conversion failed: {e}")