"""Generate GPS grid layouts for field work."""
import click
from pathlib import Path
from topoconvert.core.gps_grid import generate_gps_grid
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the gps-grid command with the CLI."""
    @cli.command('gps-grid')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--input-type', type=click.Choice(['auto', 'kml-polygon', 'csv-boundary', 'csv-extent']),
                  default='auto',
                  help='Input type (default: auto-detect)')
    @click.option('--spacing', type=float, default=40.0,
                  help='Grid spacing in feet (default: 40.0)')
    @click.option('--buffer', type=float, default=0.0,
                  help='Buffer distance in feet for csv-extent mode (default: 0.0)')
    @click.option('--boundary-type', type=click.Choice(['convex', 'concave']),
                  default='convex',
                  help='Boundary type for csv-boundary mode (default: convex)')
    @click.option('--point-style', type=click.Choice(['circle', 'pin', 'square']),
                  default='circle',
                  help='Point style in output KML (default: circle)')
    @click.option('--grid-name', default='GPS Grid',
                  help='Name for the grid in output KML (default: GPS Grid)')
    def gps_grid(input_file, output_file, input_type, spacing, buffer, 
                boundary_type, point_style, grid_name):
        """Generate GPS grid points within property boundaries.
        
        Supports KML polygons, CSV boundary points, or CSV point extents with buffer.
        The grid points are generated within the specified boundaries for field surveys.
        
        INPUT_FILE: Input file (KML with polygons or CSV with points)
        OUTPUT_FILE: Output KML file with grid points
        """
        try:
            # Generate GPS grid
            generate_gps_grid(
                input_file=Path(input_file),
                output_file=Path(output_file),
                input_type=input_type,
                spacing=spacing,
                buffer=buffer,
                boundary_type=boundary_type,
                point_style=point_style,
                grid_name=grid_name,
                progress_callback=None
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"GPS grid generation failed: {e}")