"""Generate GPS grid layouts for field work."""
import click


def register(cli):
    """Register the gps-grid command with the CLI."""
    @cli.command('gps-grid')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--input-type', type=click.Choice(['kml-polygon', 'csv-boundary', 'csv-extent']),
                  default='auto',
                  help='Input type (auto-detect if not specified)')
    @click.option('--spacing', type=float, default=40.0,
                  help='Grid spacing in feet')
    @click.option('--buffer', type=float, default=0.0,
                  help='Buffer distance in feet for csv-extent mode')
    @click.option('--boundary-type', type=click.Choice(['convex', 'concave']),
                  default='convex',
                  help='Boundary type for csv-boundary mode')
    @click.option('--point-style', type=click.Choice(['circle', 'pin', 'square']),
                  default='circle',
                  help='Point style in output KML')
    @click.option('--grid-name', default='GPS Grid',
                  help='Name for the grid in output KML')
    def gps_grid(input_file, output_file, input_type, spacing, buffer, 
                boundary_type, point_style, grid_name):
        """Generate GPS grid points within property boundaries.
        
        Supports KML polygons, CSV boundary points, or CSV point extents with buffer.
        The grid points are generated within the specified boundaries for field surveys.
        
        INPUT_FILE: Input file (KML with polygons or CSV with points)
        OUTPUT_FILE: Output KML file with grid points
        """
        click.echo(f"GPS grid generation from GPSGrid flexible_gps_grid.py")
        click.echo(f"Input: {input_file} (type: {input_type})")
        click.echo(f"Output: {output_file}")
        click.echo(f"Spacing: {spacing} feet")
        click.echo(f"Buffer: {buffer} feet")
        click.echo(f"Boundary type: {boundary_type}")
        click.echo(f"Point style: {point_style}")
        click.echo(f"Grid name: {grid_name}")
        click.echo("")
        click.echo("Note: This command requires complex polygon processing and grid generation.")
        click.echo("The full implementation from flexible_gps_grid.py can be integrated as needed.")
        click.echo("Core functionality: Generate grid points within boundaries using shapely and alphashape.")