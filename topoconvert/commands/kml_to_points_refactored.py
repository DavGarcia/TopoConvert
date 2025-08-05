"""Extract point data from KML files - Refactored version.

This demonstrates how CLI commands would use the refactored core modules
that return structured results instead of printing directly.
"""
import click
from pathlib import Path
from topoconvert.core.points_refactored import extract_points_refactored
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the kml-to-points command with the CLI."""
    @cli.command('kml-to-points-v2')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path(), required=False)
    @click.option('--format', '-f', type=click.Choice(['dxf', 'csv', 'json', 'txt']),
                  default='csv', help='Output format (default: csv)')
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML (default: meters)')
    @click.option('--translate/--no-translate', default=True,
                  help='Translate coordinates to origin (DXF only, default: translate)')
    @click.option('--use-reference-point', is_flag=True,
                  help='Use first point as reference for translation (DXF only)')
    @click.option('--layer-name', default='GPS_POINTS',
                  help='Layer name for DXF output (default: GPS_POINTS)')
    @click.option('--point-color', type=int, default=7,
                  help='AutoCAD color index for DXF points (default: 7)')
    @click.option('--target-epsg', type=int, default=None,
                  help='Target EPSG code for projection (DXF only, default: auto-detect UTM)')
    @click.option('--wgs84', is_flag=True,
                  help='Keep coordinates in WGS84 (DXF only, no projection)')
    def kml_to_points_v2(input_file, output_file, format, elevation_units, translate,
                        use_reference_point, layer_name, point_color, target_epsg, wgs84):
        """Extract point data from KML files (refactored version).
        
        This version demonstrates how CLI commands use refactored core modules
        that return structured results.
        """
        try:
            input_path = Path(input_file)
            
            # Generate default output filename if not provided
            if output_file is None:
                extension_map = {
                    'dxf': '.dxf',
                    'csv': '.csv',
                    'json': '.json',
                    'txt': '.txt'
                }
                output_path = input_path.with_suffix(extension_map[format])
            else:
                output_path = Path(output_file)
            
            # Validate projection options for DXF format
            if format == 'dxf' and target_epsg and wgs84:
                raise click.ClickException("Cannot use both --target-epsg and --wgs84")
            
            # Call the refactored core function
            result = extract_points_refactored(
                input_file=input_path,
                output_file=output_path,
                output_format=format,
                elevation_units=elevation_units,
                translate_to_origin=translate,
                use_reference_point=use_reference_point,
                layer_name=layer_name,
                point_color=point_color,
                target_epsg=target_epsg if format == 'dxf' else None,
                wgs84=wgs84 if format == 'dxf' else False,
                progress_callback=None
            )
            
            # Display the results to the user
            if result.success:
                click.echo(f"Found {result.point_count} points in KML")
                click.echo(f"\nCreated {result.format.upper()} file: {result.output_file}")
                click.echo(f"- {result.point_count} points")
                click.echo(f"- Elevation units: {result.elevation_units}")
                
                # Display coordinate system info
                if result.coordinate_system:
                    click.echo(f"- Coordinate system: {result.coordinate_system}")
                
                # Display translation info for DXF
                if result.translated_to_origin and result.reference_point:
                    ref_x, ref_y, ref_z = result.reference_point
                    if result.coordinate_system == "WGS84 (degrees)":
                        click.echo(f"- Translated to origin (reference: {ref_x:.6f}, {ref_y:.6f}, {ref_z:.2f})")
                    else:
                        click.echo(f"- Translated to origin (reference: {ref_x:.2f}, {ref_y:.2f}, {ref_z:.2f} ft)")
                
                # Display coordinate ranges
                if result.coordinate_ranges:
                    for coord, (min_val, max_val) in result.coordinate_ranges.items():
                        if coord in ['longitude', 'latitude']:
                            click.echo(f"- {coord.capitalize()} range: {min_val:.6f} to {max_val:.6f}")
                        else:
                            click.echo(f"- {coord.capitalize()} range: {min_val:.2f} to {max_val:.2f}")
                
                # Display any warnings
                for warning in result.warnings:
                    click.echo(f"Warning: {warning}")
            else:
                click.echo(f"Error: {result.message}", err=True)
                raise click.ClickException(result.message)
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Point extraction failed: {e}")