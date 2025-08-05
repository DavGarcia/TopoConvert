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
            result = generate_contours(
                input_file=input_path,
                output_file=output_path,
                elevation_units=elevation_units,
                contour_interval=interval,
                grid_resolution=grid_resolution,
                add_labels=label,
                label_height=label_height,
                translate_to_origin=not no_translate,
                target_epsg=target_epsg,
                wgs84=False  # Contour generation requires projected coordinates
            )
            
            # Display results
            click.echo(f"\nCreated {result.output_file}")
            click.echo(f"- {result.contour_count} contour polylines")
            click.echo(f"- {result.elevation_levels} elevation levels")
            
            if result.translated_to_origin and result.reference_point:
                ref_x, ref_y, ref_z = result.reference_point
                click.echo(f"- Translated to origin (reference: {ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)")
                if result.elevation_range:
                    click.echo(f"- Original elevation range: {result.elevation_range[0]:.1f} to {result.elevation_range[1]:.1f} ft")
            
            # Output coordinate system info
            click.echo(f"- Coordinates in {result.coordinate_system}")
            
            # Show contour details
            if result.details:
                start = result.details.get('contour_start', 0)
                end = result.details.get('contour_end', 0)
                click.echo(f"- Contours from {start:.1f} to {end:.1f} ft at {result.contour_interval} ft intervals")
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Contour generation failed: {e}")