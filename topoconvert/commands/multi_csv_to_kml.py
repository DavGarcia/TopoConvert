"""Merge multiple CSV files into a single KML with folders."""
import click
from pathlib import Path
from topoconvert.core.combined_kml import merge_csv_to_kml
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the multi-csv-to-kml command with the CLI."""
    @cli.command('multi-csv-to-kml')
    @click.argument('csv_files', nargs=-1, required=True, 
                    type=click.Path(exists=True))
    @click.option('--output', '-o', type=click.Path(), required=True,
                  help='Output KML file path')
    @click.option('--add-labels/--no-labels', default=True,
                  help='Add labels to placemarks (default: add-labels)')
    @click.option('--x-column', '-x', default='Longitude',
                  help='Column name for longitude/X coordinates (default: Longitude)')
    @click.option('--y-column', '-y', default='Latitude',
                  help='Column name for latitude/Y coordinates (default: Latitude)')
    @click.option('--z-column', '-z', default='Elevation',
                  help='Column name for elevation/Z coordinates (default: Elevation)')
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in CSV (default: meters)')
    @click.option('--point-scale', type=float, default=1.0,
                  help='Point icon scale factor (default: 1.0)')
    def csv_to_combined_kml(csv_files, output, add_labels, x_column, y_column, 
                           z_column, elevation_units, point_scale):
        """Merge CSV files to KML with separate folders.
        
        Each CSV file is placed in its own KML folder with a unique icon style
        and color for easy identification. All point attributes are preserved
        in ExtendedData. Ideal for comparing multiple survey datasets.
        
        CSV_FILES: Paths to input CSV files (multiple files)
        """
        try:
            # Convert to Path objects
            csv_paths = [Path(f) for f in csv_files]
            
            # Merge CSV files to KML
            result = merge_csv_to_kml(
                csv_files=csv_paths,
                output_file=Path(output),
                elevation_units=elevation_units,
                point_scale=point_scale,
                add_labels=add_labels,
                x_column=x_column,
                y_column=y_column,
                z_column=z_column
            )
            
            # Display results
            click.echo(f"\nCreated combined KML: {result.output_file}")
            click.echo(f"- {result.input_file_count} input files in separate folders")
            click.echo(f"- {result.total_points} total points")
            click.echo(f"- Each dataset has unique icon and color")
            
            if result.elevations_converted:
                click.echo("- Elevations converted from feet to meters")
            
            # Show dataset details
            if 'datasets' in result.details:
                for name, count in result.details['datasets']:
                    click.echo(f"Processed {name}: {count} points")
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"CSV to KML merge failed: {e}")