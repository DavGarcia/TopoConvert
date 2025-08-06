"""TopoConvert CLI entry point."""

import click
import sys

from topoconvert import __version__
from topoconvert.commands import (
    kml_to_contours,
    csv_to_kml,
    kml_to_points,
    kml_to_mesh,
    multi_csv_to_dxf,
    multi_csv_to_kml,
    slope_heatmap,
    kml_contours_to_dxf,
    gps_grid,
)


@click.group()
@click.version_option(version=__version__, prog_name="topoconvert")
@click.help_option("-h", "--help")
def cli() -> None:
    """TopoConvert - A unified geospatial conversion toolkit.

    Convert and process survey data between various formats including
    KML, CSV, and DXF with specialized topographical operations.
    """
    pass


# Register all commands
kml_to_contours.register(cli)
csv_to_kml.register(cli)
kml_to_points.register(cli)
kml_to_mesh.register(cli)
multi_csv_to_dxf.register(cli)
multi_csv_to_kml.register(cli)
slope_heatmap.register(cli)
kml_contours_to_dxf.register(cli)
gps_grid.register(cli)


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
