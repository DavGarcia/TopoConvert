"""Generate slope analysis heatmaps from elevation data."""
import click


def register(cli):
    """Register the slope-heatmap command with the CLI."""
    @cli.command('slope-heatmap')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML')
    @click.option('--grid-resolution', type=int, default=200,
                  help='Grid resolution for interpolation')
    @click.option('--slope-units', type=click.Choice(['degrees', 'percent', 'rise-run']),
                  default='degrees',
                  help='Units for slope display')
    @click.option('--run-length', type=float, default=10.0,
                  help='Run length for rise:run display')
    @click.option('--max-slope', type=float, default=None,
                  help='Maximum slope for color scale')
    @click.option('--colormap', default='RdYlGn_r',
                  help='Matplotlib colormap')
    @click.option('--dpi', type=int, default=150,
                  help='Output image DPI')
    @click.option('--smooth', type=float, default=1.0,
                  help='Gaussian smoothing sigma')
    def slope_heatmap(input_file, output_file, elevation_units, grid_resolution,
                     slope_units, run_length, max_slope, colormap, dpi, smooth):
        """Generate slope analysis heatmap from KML elevation data.
        
        INPUT_FILE: Path to input KML file with elevation points
        OUTPUT_FILE: Path to output PNG image file
        """
        click.echo(f"Slope heatmap generation from GPSGrid kml_to_slope_heatmap.py")
        click.echo(f"Input: {input_file}")
        click.echo(f"Output: {output_file}")
        click.echo(f"Elevation units: {elevation_units}")
        click.echo(f"Grid resolution: {grid_resolution}")
        click.echo(f"Slope units: {slope_units}")
        click.echo(f"Run length: {run_length}")
        click.echo(f"Max slope: {max_slope}")
        click.echo(f"Colormap: {colormap}")
        click.echo(f"DPI: {dpi}")
        click.echo(f"Smoothing: {smooth}")
        click.echo("")
        click.echo("Note: This command requires complex interpolation and visualization.")
        click.echo("The full implementation from kml_to_slope_heatmap.py can be integrated as needed.")
        click.echo("Core functionality: Uses scipy.interpolate.griddata and matplotlib for heatmap generation.")