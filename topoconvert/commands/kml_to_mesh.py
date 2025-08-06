"""Generate triangulated mesh from KML point data."""

import click
from pathlib import Path
from topoconvert.core.mesh import generate_mesh
from topoconvert.core.exceptions import TopoConvertError


def register(cli) -> None:
    """Register the kml-to-dxf-mesh command with the CLI."""

    @cli.command("kml-to-dxf-mesh")
    @click.argument("input_file", type=click.Path(exists=True))
    @click.argument("output_file", type=click.Path(), required=False)
    @click.option(
        "--elevation-units",
        type=click.Choice(["meters", "feet"]),
        default="meters",
        help="Units of elevation in KML (default: meters)",
    )
    @click.option(
        "--translate/--no-translate",
        default=True,
        help="Translate coordinates to origin (default: translate)",
    )
    @click.option(
        "--use-reference-point",
        is_flag=True,
        help="Use first point as reference for translation",
    )
    @click.option(
        "--layer-name",
        default="TIN_MESH",
        help="Layer name for mesh faces (default: TIN_MESH)",
    )
    @click.option(
        "--mesh-color",
        type=int,
        default=8,
        help="AutoCAD color index for mesh faces (default: 8)",
    )
    @click.option(
        "--no-wireframe",
        is_flag=True,
        help="Skip wireframe edges (default: include wireframe)",
    )
    @click.option(
        "--wireframe-color",
        type=int,
        default=7,
        help="AutoCAD color index for wireframe (default: 7)",
    )
    @click.option(
        "--target-epsg",
        type=int,
        default=None,
        help="Target EPSG code for projection (default: auto-detect UTM)",
    )
    def kml_to_mesh(
        input_file,
        output_file,
        elevation_units,
        translate,
        use_reference_point,
        layer_name,
        mesh_color,
        no_wireframe,
        wireframe_color,
        target_epsg,
    ) -> None:
        """Generate 3D TIN mesh from KML points.

        Creates a Delaunay triangulated irregular network (TIN) mesh from KML point data
        and saves it as a DXF file with 3D faces. Includes wireframe edges by default
        for better visualization.

        INPUT_FILE: Path to input KML file
        OUTPUT_FILE: Path to output DXF file (optional, defaults to input name with .dxf)
        """

        try:
            input_path = Path(input_file)

            # Use provided output file or create default name
            if output_file is None:
                output_path = input_path.with_suffix(".dxf")
            else:
                output_path = Path(output_file)

            # Generate mesh
            result = generate_mesh(
                input_file=input_path,
                output_file=output_path,
                elevation_units=elevation_units,
                translate_to_origin=translate,
                use_reference_point=use_reference_point,
                layer_name=layer_name,
                mesh_color=mesh_color,
                add_wireframe=not no_wireframe,  # Invert the flag since wireframe is now default
                wireframe_color=wireframe_color,
                target_epsg=target_epsg,
                wgs84=False,  # Mesh generation requires projected coordinates
            )

            # Display results
            click.echo(f"\nCreated 3D TIN mesh DXF: {result.output_file}")
            click.echo(f"- {result.face_count} triangular faces")
            click.echo(f"- {result.vertex_count} vertices")
            click.echo(f"- Layer: {result.layer_name}")

            if result.has_wireframe:
                wireframe_layer = result.details.get(
                    "wireframe_layer", f"{result.layer_name}_WIREFRAME"
                )
                click.echo(f"- {result.edge_count} wireframe edges")
                click.echo(f"- Wireframe layer: {wireframe_layer}")

            if result.translated_to_origin and result.reference_point:
                ref_x, ref_y, ref_z = result.reference_point
                if use_reference_point:
                    click.echo(
                        f"- Reference point (excluded): ({ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)"
                    )
                    click.echo("- First point translated to origin")
                else:
                    click.echo(
                        f"- Translated to origin (reference: {ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)"
                    )

            # Output coordinate system info
            click.echo(f"- Coordinates in {result.coordinate_system}")

            # Print coordinate ranges
            if (
                "coordinate_ranges" in result.details
                and result.details["coordinate_ranges"]
            ):
                ranges = result.details["coordinate_ranges"]
                units = ranges.get("units", "ft")
                click.echo(
                    f"- X range: {ranges['x'][0]:.1f} to {ranges['x'][1]:.1f} {units}"
                )
                click.echo(
                    f"- Y range: {ranges['y'][0]:.1f} to {ranges['y'][1]:.1f} {units}"
                )
                click.echo(
                    f"- Z range: {ranges['z'][0]:.1f} to {ranges['z'][1]:.1f} {units}"
                )

        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Mesh generation failed: {e}")
