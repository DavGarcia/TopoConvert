"""Generate triangulated mesh from KML point data."""
import click
from pathlib import Path
from topoconvert.core.mesh import generate_mesh
from topoconvert.core.exceptions import TopoConvertError


def register(cli):
    """Register the kml-to-mesh command with the CLI."""
    @cli.command('kml-to-mesh')
    @click.argument('input_file', type=click.Path(exists=True))
    @click.argument('output_file', type=click.Path())
    @click.option('--elevation-units', type=click.Choice(['meters', 'feet']),
                  default='meters',
                  help='Units of elevation in KML')
    @click.option('--translate/--no-translate', default=True,
                  help='Translate coordinates to origin')
    @click.option('--use-reference-point', is_flag=True,
                  help='Use first point as reference for translation')
    @click.option('--layer-name', default='TIN_MESH',
                  help='Layer name for mesh faces')
    @click.option('--mesh-color', type=int, default=8,
                  help='AutoCAD color index for mesh faces')
    @click.option('--add-wireframe', is_flag=True,
                  help='Add wireframe edges to the mesh')
    @click.option('--wireframe-color', type=int, default=7,
                  help='AutoCAD color index for wireframe')
    def kml_to_mesh(input_file, output_file, elevation_units, translate,
                   use_reference_point, layer_name, mesh_color, 
                   add_wireframe, wireframe_color):
        """Generate 3D TIN mesh from KML points.
        
        Creates a Delaunay triangulated irregular network (TIN) mesh from KML point data
        and saves it as a DXF file with 3D faces. Optionally includes wireframe edges.
        
        INPUT_FILE: Path to input KML file
        OUTPUT_FILE: Path to output DXF file
        """
        try:
            # Generate mesh
            generate_mesh(
                input_file=Path(input_file),
                output_file=Path(output_file),
                elevation_units=elevation_units,
                translate_to_origin=translate,
                use_reference_point=use_reference_point,
                layer_name=layer_name,
                mesh_color=mesh_color,
                add_wireframe=add_wireframe,
                wireframe_color=wireframe_color,
                progress_callback=None
            )
                
        except TopoConvertError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.ClickException(str(e))
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            raise click.ClickException(f"Mesh generation failed: {e}")