"""Convert KML elevation data to relative elevations with customizable reference methods."""

import click
from pathlib import Path
from topoconvert.core.relative_elevation import convert_to_relative_elevation
from topoconvert.core.exceptions import TopoConvertError


def register(cli) -> None:
    """Register the kml-relative-elevation command with the CLI."""

    @cli.command("kml-relative-elevation")
    @click.argument("input_file", type=click.Path(exists=True))
    @click.argument("output_file", type=click.Path(), required=False)
    @click.option(
        "--elevation-units",
        type=click.Choice(["meters", "feet"]),
        default="meters",
        help="Input elevation units (default: meters)",
    )
    @click.option(
        "--output-units",
        type=click.Choice(["meters", "feet"]),
        default="feet",
        help="Output elevation units (default: feet)",
    )
    @click.option(
        "--reference-method",
        type=click.Choice(["min", "max", "mean"]),
        default="min",
        help="Reference calculation method (default: min)",
    )
    @click.option(
        "--label-format",
        default="{value:.1f} {unit}",
        help="Label format string with {value} and {unit} placeholders (default: {value:.1f} {unit})",
    )
    @click.option(
        "--apply-style/--no-style",
        default=True,
        help="Apply KML styling for elevation labels (default: apply styling)",
    )
    def kml_relative_elevation(
        input_file,
        output_file,
        elevation_units,
        output_units,
        reference_method,
        label_format,
        apply_style,
    ) -> None:
        """Convert KML elevations to relative values.
        
        This command processes KML files containing elevation data and converts
        the elevations to relative values based on a reference point (minimum,
        maximum, or mean elevation). The output KML file will have updated
        point labels showing the relative elevation differences.

        INPUT_FILE: Path to input KML file with elevation data
        OUTPUT_FILE: Path to output KML file (optional, auto-generated if not provided)
        """
        try:
            # Generate output filename if not provided
            if output_file is None:
                input_path = Path(input_file)
                output_file = input_path.parent / f"{input_path.stem}_relative{input_path.suffix}"
                click.echo(f"Auto-generating output file: {output_file}")

            # Convert KML elevations to relative values
            result = convert_to_relative_elevation(
                input_file=Path(input_file),
                output_file=Path(output_file),
                elevation_units=elevation_units,
                output_units=output_units,
                reference_method=reference_method,
                label_format=label_format,
                apply_style=apply_style,
            )

            # Display results
            click.echo(f"\nCreated relative elevation KML file: {result.output_file}")
            click.echo(f"- {result.point_count} elevation points processed")
            click.echo(f"- Input units: {result.input_elevation_units}")
            click.echo(f"- Output units: {result.output_elevation_units}")
            click.echo(f"- Reference method: {result.reference_method}")
            
            # Display unit abbreviation for output
            unit_display = "ft" if result.output_elevation_units == "feet" else "m"
            click.echo(f"- Reference value: {result.reference_value:.1f} {unit_display}")
            
            # Display elevation ranges
            orig_min, orig_max = result.elevation_range
            click.echo(f"- Original elevation range: {orig_min:.1f} to {orig_max:.1f} {unit_display}")
            
            rel_min, rel_max = result.relative_range
            click.echo(f"- Relative elevation range: {rel_min:.1f} to {rel_max:.1f} {unit_display}")
            
            # Display styling info
            if result.style_applied:
                click.echo("- KML styling applied for elevation labels")
            else:
                click.echo("- No KML styling applied")
                
            # Display label format
            click.echo(f"- Label format: {result.label_format}")

            # Display warnings if any
            if result.warnings:
                for warning in result.warnings:
                    click.echo(f"Warning: {warning}", err=True)

        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"KML relative elevation conversion failed: {e}")