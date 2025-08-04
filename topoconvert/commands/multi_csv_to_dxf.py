"""Merge multiple CSV files into a single DXF with 3D points."""
import click
from pathlib import Path
from topoconvert.core.combined_dxf import merge_csv_to_dxf
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the multi-csv-to-dxf command with the CLI."""
    @cli.command('multi-csv-to-dxf')
    @click.argument('csv_files', nargs=-1, required=True, 
                    type=click.Path(exists=True))
    @click.option('--output', '-o', type=click.Path(), required=True,
                  help='Output DXF file path')
    @click.option('--target-epsg', type=int, default=None,
                  help='Target EPSG code for projection (default: auto-detect UTM)')
    @click.option('--wgs84', is_flag=True,
                  help='Keep coordinates in WGS84 (no projection)')
    def combined_dxf(csv_files, output, target_epsg, wgs84):
        """Merge CSV files to DXF with separate layers.
        
        Each CSV file is placed on its own layer with a unique color for easy
        identification. By default, points are projected to the auto-detected local UTM zone
        and translated to a common origin for accurate spatial alignment.
        
        CSV_FILES: Paths to input CSV files (multiple files)
        """
        try:
            # Convert to Path objects
            csv_paths = [Path(f) for f in csv_files]
            
            # Validate projection options
            if target_epsg and wgs84:
                raise click.ClickException("Cannot use both --target-epsg and --wgs84")
            
            # Merge CSV files to DXF
            merge_csv_to_dxf(
                csv_files=csv_paths,
                output_file=Path(output),
                target_epsg=target_epsg,
                wgs84=wgs84,
                progress_callback=None
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"CSV merge failed: {e}")