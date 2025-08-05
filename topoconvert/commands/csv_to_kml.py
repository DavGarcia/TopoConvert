"""Convert CSV data to KML format."""
import click
from pathlib import Path
from topoconvert.core.csv_kml import convert_csv_to_kml
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the csv-to-kml command with the CLI."""
    @cli.command('csv-to-kml')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--add-labels/--no-labels', default=True,
                  help='Add labels to KML placemarks (default: add labels)')
    @click.option('--x-column', '-x', default='Longitude',
                  help='Column name for longitude/X coordinates (default: Longitude)')
    @click.option('--y-column', '-y', default='Latitude',
                  help='Column name for latitude/Y coordinates (default: Latitude)')
    @click.option('--z-column', '-z', default='Elevation',
                  help='Column name for elevation/Z coordinates (default: Elevation)')
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in CSV (default: meters)')
    @click.option('--point-style', type=click.Choice(['circle', 'pin', 'square']),
                  default='circle',
                  help='Point style in KML (default: circle)')
    @click.option('--point-color', default='ff00ff00',
                  help='Point color in AABBGGRR format (default: ff00ff00 = green)')
    @click.option('--point-scale', type=float, default=0.8,
                  help='Point scale factor (default: 0.8)')
    @click.option('--kml-name', default=None,
                  help='Name for KML document (default: input filename)')
    def csv_to_kml(input_file, output_file, add_labels, x_column, y_column, z_column,
                   elevation_units, point_style, point_color, point_scale, kml_name):
        """Convert CSV survey data to KML format.
        
        INPUT_FILE: Path to input CSV file
        OUTPUT_FILE: Path to output KML file
        """
        try:
            # Convert CSV to KML
            result = convert_csv_to_kml(
                input_file=Path(input_file),
                output_file=Path(output_file),
                elevation_units=elevation_units,
                point_style=point_style,
                point_color=point_color,
                point_scale=point_scale,
                add_labels=add_labels,
                kml_name=kml_name,
                x_column=x_column,
                y_column=y_column,
                z_column=z_column
            )
            
            # Display results
            click.echo(f"\nCreated KML file: {result.output_file}")
            click.echo(f"- {result.valid_points} GPS points written")
            click.echo(f"- Elevation units: {result.elevation_units}")
            click.echo(f"- Point style: {result.point_style}")
            if result.has_labels:
                click.echo("- Elevation labels included")
            
            # Print coordinate bounds
            if result.coordinate_bounds:
                bounds = result.coordinate_bounds
                click.echo(f"- Latitude range: {bounds['latitude'][0]:.6f} to {bounds['latitude'][1]:.6f}")
                click.echo(f"- Longitude range: {bounds['longitude'][0]:.6f} to {bounds['longitude'][1]:.6f}")
                
                if 'elevation' in bounds:
                    elev_range = bounds['elevation']
                    click.echo(f"- Elevation range: {elev_range[0]:.2f} to {elev_range[1]:.2f} {result.elevation_units}")
                elif not result.details.get('has_elevation', True):
                    click.echo(f"- Elevation: 0.00 {result.elevation_units} (no elevation data)")
            
            # Display warnings if any
            if result.warnings:
                for warning in result.warnings:
                    click.echo(f"Warning: {warning}", err=True)
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"CSV to KML conversion failed: {e}")