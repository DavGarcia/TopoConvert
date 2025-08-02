"""Generate GPS grid layouts for field work."""
import click


def register(cli):
    """Register the gps-grid command with the CLI."""
    @cli.command('gps-grid')
    @click.argument('output_file', type=click.Path())
    @click.option('--bounds', '-b', nargs=4, type=float, required=True,
                  metavar='MIN_X MIN_Y MAX_X MAX_Y',
                  help='Grid bounds in projected coordinates')
    @click.option('--spacing', '-s', type=float, default=100.0,
                  help='Grid spacing in meters')
    @click.option('--format', '-f', 
                  type=click.Choice(['kml', 'csv', 'dxf']),
                  default='kml',
                  help='Output format')
    @click.option('--label-format', '-l', default='A{row}-{col}',
                  help='Grid point label format')
    def gps_grid(output_file, bounds, spacing, format, label_format):
        """Generate GPS grid layout for field surveys.
        
        OUTPUT_FILE: Path to output file
        """
        # Implementation will be added later
        click.echo(f"Generating GPS grid to {output_file}")
        click.echo(f"Bounds: X({bounds[0]}, {bounds[2]}) Y({bounds[1]}, {bounds[3]})")
        click.echo(f"Spacing: {spacing}m")
        click.echo(f"Format: {format}")
        click.echo(f"Label format: {label_format}")
        click.echo("Note: Implementation pending")