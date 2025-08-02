"""Combine multiple DXF files into a single file."""
import click


def register(cli):
    """Register the combined-dxf command with the CLI."""
    @cli.command('combined-dxf')
    @click.argument('input_files', nargs=-1, required=True, 
                    type=click.Path(exists=True))
    @click.option('--output', '-o', type=click.Path(), required=True,
                  help='Output DXF file path')
    @click.option('--merge-layers/--keep-layers', default=False,
                  help='Merge all entities into a single layer')
    def combined_dxf(input_files, output, merge_layers):
        """Combine multiple DXF files into one.
        
        INPUT_FILES: Paths to input DXF files (multiple files)
        """
        # Implementation will be added later
        click.echo(f"Combining {len(input_files)} DXF files")
        for f in input_files:
            click.echo(f"  - {f}")
        click.echo(f"Output: {output}")
        click.echo(f"Layer handling: {'merge' if merge_layers else 'keep separate'}")
        click.echo("Note: Implementation pending")