"""Convert KML contour lines to DXF format."""
import click
from pathlib import Path
from topoconvert.core.kml_contours import convert_kml_contours_to_dxf
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the kml-contours-to-dxf command with the CLI."""
    @cli.command('kml-contours-to-dxf')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML (default: meters)')
    @click.option('--label/--no-label', default=True,
                  help='Add elevation labels to contours (default: label)')
    @click.option('--label-height', type=float, default=6.0,
                  help='Text size for elevation labels in drawing units (default: 6.0)')
    @click.option('--translate/--no-translate', default=True,
                  help='Translate coordinates to origin (default: translate)')
    @click.option('--target-epsg', type=int, default=None,
                  help='Target EPSG code for projection (default: auto-detect UTM)')
    @click.option('--wgs84', is_flag=True,
                  help='Keep coordinates in WGS84 (no projection)')
    def kml_contours_to_dxf(input_file, output_file, elevation_units,
                           label, label_height, translate, target_epsg, wgs84):
        """Convert KML contour LineStrings to DXF format.
        
        Reads KML files with LineString elements representing contour lines.
        Determines elevation from coordinate altitudes or ExtendedData fields.
        Creates separate layers for each elevation and optionally adds text labels.
        
        INPUT_FILE: Path to input KML file with contour lines
        OUTPUT_FILE: Path to output DXF file
        """
        try:
            # Validate projection options
            if target_epsg and wgs84:
                raise click.ClickException("Cannot use both --target-epsg and --wgs84")
                
            # Convert KML contours to DXF with sensible defaults
            convert_kml_contours_to_dxf(
                input_file=Path(input_file),
                output_file=Path(output_file),
                z_source='auto',  # Auto-detect elevation source
                z_units=elevation_units,
                target_epsg=target_epsg,
                add_labels=label,
                layer_prefix='CT_',
                decimals=1,
                z_field=None,  # Auto-detect
                altitude_tolerance=1e-6,
                translate_to_origin=translate,
                target_epsg_feet=False,
                progress_callback=None,
                label_height=label_height,
                wgs84=wgs84
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Contour conversion failed: {e}")