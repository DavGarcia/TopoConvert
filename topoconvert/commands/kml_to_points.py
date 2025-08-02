"""Extract point data from KML files."""
import click


def register(cli):
    """Register the kml-to-points command with the CLI."""
    @cli.command('kml-to-points')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--format', '-f', type=click.Choice(['csv', 'json', 'txt']),
                  default='csv', help='Output format')
    def kml_to_points(input_file, output_file, format):
        """Extract point data from KML files.
        
        INPUT_FILE: Path to input KML file
        OUTPUT_FILE: Path to output file
        """
        # Implementation will be added later
        click.echo(f"Extracting points from {input_file} to {output_file}")
        click.echo(f"Output format: {format}")
        click.echo("Note: Implementation pending")