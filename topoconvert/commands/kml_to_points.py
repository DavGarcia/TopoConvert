"""Extract point data from KML files."""

import click
from pathlib import Path
from topoconvert.core.points import extract_points
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the kml-to-points command with the CLI."""

    @cli.command("kml-to-points")
    @click.argument("input_file", type=click.Path(exists=True))
    @click.argument("output_file", type=click.Path(), required=False)
    @click.option(
        "--format",
        "-f",
        type=click.Choice(["dxf", "csv", "json", "txt"]),
        default="csv",
        help="Output format (default: csv)",
    )
    @click.option(
        "--elevation-units",
        type=click.Choice(["meters", "feet"]),
        default="meters",
        help="Units of elevation in KML (default: meters)",
    )
    @click.option(
        "--translate/--no-translate",
        default=True,
        help="Translate coordinates to origin (DXF only, default: translate)",
    )
    @click.option(
        "--use-reference-point",
        is_flag=True,
        help="Use first point as reference for translation (DXF only)",
    )
    @click.option(
        "--layer-name",
        default="GPS_POINTS",
        help="Layer name for DXF output (default: GPS_POINTS)",
    )
    @click.option(
        "--point-color",
        type=int,
        default=7,
        help="AutoCAD color index for DXF points (default: 7)",
    )
    @click.option(
        "--target-epsg",
        type=int,
        default=None,
        help="Target EPSG code for projection (DXF only, default: auto-detect UTM)",
    )
    @click.option(
        "--wgs84",
        is_flag=True,
        help="Keep coordinates in WGS84 (DXF only, no projection)",
    )
    def kml_to_points(
        input_file,
        output_file,
        format,
        elevation_units,
        translate,
        use_reference_point,
        layer_name,
        point_color,
        target_epsg,
        wgs84,
    ):
        """Extract point data from KML files.

        Extract points from KML and save in various formats including DXF 3D point cloud,
        CSV with lat/lon/elevation, JSON structured data, or plain text format.

        INPUT_FILE: Path to input KML file
        OUTPUT_FILE: Path to output file (optional, defaults to input name with new extension)
        """
        try:
            input_path = Path(input_file)

            # Generate default output filename if not provided
            if output_file is None:
                extension_map = {
                    "dxf": ".dxf",
                    "csv": ".csv",
                    "json": ".json",
                    "txt": ".txt",
                }
                output_path = input_path.with_suffix(extension_map[format])
            else:
                output_path = Path(output_file)

            # Validate projection options for DXF format
            if format == "dxf" and target_epsg and wgs84:
                raise click.ClickException("Cannot use both --target-epsg and --wgs84")

            # Extract points
            result = extract_points(
                input_file=input_path,
                output_file=output_path,
                output_format=format,
                elevation_units=elevation_units,
                translate_to_origin=translate,
                use_reference_point=use_reference_point,
                layer_name=layer_name,
                point_color=point_color,
                target_epsg=target_epsg if format == "dxf" else None,
                wgs84=wgs84 if format == "dxf" else False,
            )

            # Display results
            click.echo(f"\nCreated {result.format} file: {result.output_file}")
            click.echo(f"- {result.point_count} points")

            if result.format == "DXF":
                click.echo(f"- Layer: {result.details.get('layer_name', 'GPS_POINTS')}")

                if result.translated_to_origin and result.reference_point:
                    ref_x, ref_y, ref_z = result.reference_point
                    if result.details.get("use_reference_point"):
                        if result.details.get("wgs84"):
                            click.echo(
                                f"- Reference point (excluded): ({ref_x:.6f}, {ref_y:.6f}, {ref_z:.2f})"
                            )
                        else:
                            click.echo(
                                f"- Reference point (excluded): ({ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)"
                            )
                        click.echo("- First point translated to origin")
                    else:
                        if result.details.get("wgs84"):
                            click.echo(
                                f"- Translated to origin (reference: {ref_x:.6f}, {ref_y:.6f}, {ref_z:.2f})"
                            )
                        else:
                            click.echo(
                                f"- Translated to origin (reference: {ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)"
                            )

                # Output coordinate system info
                click.echo(f"- Coordinates in {result.coordinate_system}")

                # Print coordinate ranges
                if result.coordinate_ranges:
                    ranges = result.coordinate_ranges
                    units = ranges.get("units", "ft")
                    if units == "degrees":
                        click.echo(
                            f"- X range: {ranges['x'][0]:.6f} to {ranges['x'][1]:.6f} {units}"
                        )
                        click.echo(
                            f"- Y range: {ranges['y'][0]:.6f} to {ranges['y'][1]:.6f} {units}"
                        )
                        z_unit = "m" if result.elevation_units == "meters" else "ft"
                        click.echo(
                            f"- Z range: {ranges['z'][0]:.1f} to {ranges['z'][1]:.1f} {z_unit}"
                        )
                    else:
                        click.echo(
                            f"- X range: {ranges['x'][0]:.1f} to {ranges['x'][1]:.1f} {units}"
                        )
                        click.echo(
                            f"- Y range: {ranges['y'][0]:.1f} to {ranges['y'][1]:.1f} {units}"
                        )
                        click.echo(
                            f"- Z range: {ranges['z'][0]:.1f} to {ranges['z'][1]:.1f} {units}"
                        )
            else:
                click.echo(f"- Elevation units: {result.elevation_units}")

        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Point extraction failed: {e}")
