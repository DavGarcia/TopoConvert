"""Convert KML data to CSV format."""
import click


def register(cli):
    """Register the kml-to-csv command with the CLI."""
    @cli.command('kml-to-csv')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--include-attributes/--no-attributes', default=True,
                  help='Include KML attributes in CSV')
    @click.option('--coordinate-format', '-c', 
                  type=click.Choice(['separate', 'wkt']),
                  default='separate',
                  help='How to format coordinates in CSV')
    def kml_to_csv(input_file, output_file, include_attributes, coordinate_format):
        """Convert KML data to CSV format.
        
        INPUT_FILE: Path to input KML file
        OUTPUT_FILE: Path to output CSV file
        """
        # Implementation will be added later
        click.echo(f"Converting {input_file} to {output_file}")
        click.echo(f"Include attributes: {include_attributes}")
        click.echo(f"Coordinate format: {coordinate_format}")
        click.echo("Note: Implementation pending")