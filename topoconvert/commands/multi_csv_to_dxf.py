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
    def combined_dxf(csv_files, output):
        """Merge CSV files to DXF with separate layers.
        
        Each CSV file is placed on its own layer with a unique color for easy
        identification. Points are projected to NAD83/UTM Zone 14N and translated
        to a common origin for accurate spatial alignment.
        
        CSV_FILES: Paths to input CSV files (multiple files)
        """
        try:
            # Convert to Path objects
            csv_paths = [Path(f) for f in csv_files]
            
            # Merge CSV files to DXF
            merge_csv_to_dxf(
                csv_files=csv_paths,
                output_file=Path(output),
                progress_callback=None
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"CSV merge failed: {e}")