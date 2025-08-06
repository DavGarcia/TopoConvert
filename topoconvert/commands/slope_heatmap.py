"""Generate slope heatmaps from elevation data."""

import click
from pathlib import Path
from topoconvert.core.slope_heatmap import generate_slope_heatmap
from topoconvert.core.exceptions import TopoConvertError


def register(cli) -> None:
    """Register the slope-heatmap command with the CLI."""

    @cli.command("slope-heatmap")
    @click.argument("input_file", type=click.Path(exists=True))
    @click.argument("output_file", type=click.Path(), required=False)
    @click.option(
        "--elevation-units",
        type=click.Choice(["meters", "feet"]),
        default="meters",
        help="Units of elevation in KML (default: meters)",
    )
    @click.option(
        "--grid-resolution",
        type=int,
        default=200,
        help="Grid density for interpolation (200 = 200x200 grid, higher = smoother heatmap, default: 200)",
    )
    @click.option(
        "--slope-units",
        type=click.Choice(["degrees", "percent", "rise-run"]),
        default="degrees",
        help="Units for slope display (default: degrees)",
    )
    @click.option(
        "--run-length",
        type=float,
        default=10.0,
        help="Run length for rise:run display (default: 10.0)",
    )
    @click.option(
        "--max-slope",
        type=float,
        default=None,
        help="Maximum slope for color scale (auto if not set)",
    )
    @click.option(
        "--colormap",
        default="RdYlGn_r",
        help="Matplotlib colormap (default: RdYlGn_r, color-blind friendly: viridis, cividis)",
    )
    @click.option(
        "--dpi", type=int, default=150, help="Output image DPI (default: 150)"
    )
    @click.option(
        "--smooth",
        type=float,
        default=1.0,
        help="Gaussian smoothing sigma (0 = no smoothing, default: 1.0)",
    )
    @click.option(
        "--no-contours",
        is_flag=True,
        help="Disable elevation contours overlay (default: show contours)",
    )
    @click.option(
        "--contour-interval",
        type=float,
        default=5.0,
        help="Contour interval in feet (default: 5.0)",
    )
    @click.option(
        "--target-slope",
        type=float,
        default=None,
        help="Target slope for middle color in scale (values above=red, below=green)",
    )
    def slope_heatmap(
        input_file,
        output_file,
        elevation_units,
        grid_resolution,
        slope_units,
        run_length,
        max_slope,
        colormap,
        dpi,
        smooth,
        no_contours,
        contour_interval,
        target_slope,
    ) -> None:
        """Generate slope heatmap from elevation data.

        Calculates terrain slope and saves as PNG with color-coded visualization.
        Green indicates low slope, red indicates high slope.

        INPUT_FILE: KML file with elevation points
        OUTPUT_FILE: Output PNG file (optional, defaults to input name with .png)
        """
        try:
            input_path = Path(input_file)

            # Use provided output file or create default name
            if output_file is None:
                output_path = input_path.with_suffix(".png")
            else:
                output_path = Path(output_file)

            # Generate slope heatmap
            result = generate_slope_heatmap(
                input_file=input_path,
                output_file=output_path,
                elevation_units=elevation_units,
                grid_resolution=grid_resolution,
                slope_units=slope_units,
                run_length=run_length,
                max_slope=max_slope,
                colormap=colormap,
                dpi=dpi,
                smooth=smooth,
                show_contours=not no_contours,  # Invert flag since contours are default
                contour_interval=contour_interval,
                target_slope=target_slope,
            )

            # Display results
            click.echo(f"\nCreated slope heatmap: {result.output_file}")
            click.echo(
                f"- Grid resolution: {result.grid_resolution[0]}x{result.grid_resolution[1]}"
            )
            click.echo(f"- Slope units: {result.slope_units}")
            if result.smoothing_applied is not None:
                click.echo(f"- Smoothing applied: sigma={result.smoothing_applied}")
            click.echo(f"- Output resolution: {result.output_dpi} DPI")

        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Slope heatmap generation failed: {e}")
