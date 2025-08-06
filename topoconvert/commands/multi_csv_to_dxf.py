"""Merge multiple CSV files into a single DXF with 3D points."""

import click
from pathlib import Path
from topoconvert.core.combined_dxf import merge_csv_to_dxf
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the multi-csv-to-dxf command with the CLI."""

    @cli.command("multi-csv-to-dxf")
    @click.argument("csv_files", nargs=-1, required=True, type=click.Path(exists=True))
    @click.option(
        "--output", "-o", type=click.Path(), required=True, help="Output DXF file path"
    )
    @click.option(
        "--target-epsg",
        type=int,
        default=None,
        help="Target EPSG code for projection (default: auto-detect UTM)",
    )
    @click.option(
        "--wgs84", is_flag=True, help="Keep coordinates in WGS84 (no projection)"
    )
    def combined_dxf(csv_files, output, target_epsg, wgs84):
        """Merge CSV files to DXF with separate layers.

        Each CSV file is placed on its own layer with a unique color for easy
        identification. By default, points are projected to the auto-detected local UTM zone
        and translated to a common origin for accurate spatial alignment.

        CSV files must have Latitude and Longitude columns. If an Elevation column
        is present, it will be used; otherwise points will be placed at elevation 0.0.

        CSV_FILES: Paths to input CSV files (multiple files)
        """
        try:
            # Convert to Path objects
            csv_paths = [Path(f) for f in csv_files]

            # Validate projection options
            if target_epsg and wgs84:
                raise click.ClickException("Cannot use both --target-epsg and --wgs84")

            # Merge CSV files to DXF
            result = merge_csv_to_dxf(
                csv_files=csv_paths,
                output_file=Path(output),
                target_epsg=target_epsg,
                wgs84=wgs84,
            )

            # Display results
            click.echo(f"\nCreated merged DXF: {result.output_file}")
            click.echo(f"- {result.input_file_count} input files")
            click.echo(f"- {result.total_points} total points")

            # Show reference point
            ref_x, ref_y, ref_z = result.reference_point
            if "WGS84" in result.coordinate_system:
                click.echo(
                    f"- Global reference point: ({ref_x:.6f}, {ref_y:.6f}, {ref_z:.2f})"
                )
            else:
                click.echo(
                    f"- Global reference point: ({ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)"
                )

            # Show coordinate system
            click.echo(f"- Coordinates in {result.coordinate_system}")

            # Show dataset details
            if "datasets" in result.details:
                for name, count, msg in result.details["datasets"]:
                    click.echo(f"Processed {name}: {count} points{msg}")

            # Show coordinate ranges
            if (
                "coordinate_ranges" in result.details
                and result.details["coordinate_ranges"]
            ):
                ranges = result.details["coordinate_ranges"]
                units = ranges.get("units", {})
                for axis in ["x", "y", "z"]:
                    if axis in ranges and axis in units:
                        min_val, max_val = ranges[axis]
                        unit = units[axis]
                        if unit == "degrees":
                            click.echo(
                                f"- {axis.upper()} range: {min_val:.6f} to {max_val:.6f} {unit}"
                            )
                        else:
                            click.echo(
                                f"- {axis.upper()} range: {min_val:.1f} to {max_val:.1f} {unit}"
                            )

            # Show layers created
            for i, layer in enumerate(result.layers_created):
                color_idx = [1, 2, 3, 4, 5, 6, 7, 140, 141, 42, 43, 180, 210][i % 13]
                click.echo(f"Added layer {layer}: (color {color_idx})")

        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"CSV merge failed: {e}")
