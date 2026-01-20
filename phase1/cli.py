"""
Phase 1 Command Line Interface

CLI for running the Phase 1 QGIS/GDAL terrain preparation pipeline.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from .client import Phase1Client
from .config import Phase1Config

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False, show_path=False)],
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="phase1")
def cli():
    """
    Phase 1 - QGIS/GDAL Terrain Preparation
    
    Process DEM/DTM data to create heightmaps and overlays for Unity.
    """
    pass


@cli.command()
@click.option(
    "-c", "--config",
    type=click.Path(exists=True, path_type=Path),
    help="YAML or JSON configuration file",
)
@click.option(
    "--course-name",
    type=str,
    help="Course name",
)
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    help="Workspace output directory",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def run(
    config: Optional[Path],
    course_name: Optional[str],
    output: Optional[Path],
    verbose: bool,
):
    """
    Run the complete Phase 1 pipeline.
    """
    setup_logging(verbose)
    
    # Load or create config
    if config:
        if config.suffix in (".yml", ".yaml"):
            cfg = Phase1Config.from_yaml(config)
        else:
            cfg = Phase1Config.from_json(config)
    else:
        cfg = Phase1Config()
    
    # Override with CLI options
    if course_name:
        cfg.course_name = course_name
    if output:
        cfg.workspace.workspace_path = output
    cfg.verbose = verbose
    
    console.print("\n[bold blue]Phase 1 Pipeline[/bold blue]")
    console.print(f"Course: {cfg.course_name}")
    console.print(f"Workspace: {cfg.workspace.workspace_path}\n")
    
    try:
        client = Phase1Client(cfg)
        state = client.run()
        
        console.print("\n[green]✓ Pipeline completed![/green]")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("phase1_config.yaml"),
    help="Output config file path",
)
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Config file format",
)
def init_config(output: Path, format: str):
    """
    Generate a default configuration file.
    """
    config = Phase1Config()
    
    if format == "yaml":
        config.to_yaml(output)
    else:
        config.to_json(output)
    
    console.print(f"[green]✓ Created config file: {output}[/green]")


@cli.command()
@click.argument("workspace_dir", type=click.Path(exists=True, path_type=Path))
def validate(workspace_dir: Path):
    """
    Validate Phase 1 pipeline output.
    
    WORKSPACE_DIR: Path to Phase 1 workspace directory
    """
    console.print("\n[bold blue]Validating Output[/bold blue]")
    console.print(f"Directory: {workspace_dir}\n")
    
    # TODO: Implement validation checks
    console.print("[yellow]Validation not yet implemented[/yellow]")


@cli.command()
def info():
    """
    Display Phase 1 pipeline information.
    """
    console.print("\n[bold blue]Phase 1 - QGIS/GDAL Terrain Preparation[/bold blue]\n")
    
    console.print("[bold]Pipeline Stages:[/bold]")
    stages = [
        ("Stage 2: Project Setup", "Initialize QGIS project and workspace"),
        ("Stage 3: DEM Merging", "Merge DEM tiles into single TIF"),
        ("Stage 4: Heightmaps", "Create inner and outer heightmaps"),
        ("Stage 5: Unity Conversion", "Convert to Unity RAW format"),
        ("Validation", "Verify output files and formats"),
    ]
    
    for stage, desc in stages:
        console.print(f"  {stage}: {desc}")
    
    console.print("\n[bold]Usage:[/bold]")
    console.print("  phase1 run --course-name MyCourse -o workspace/")
    console.print("  phase1 init-config -o config.yaml")
    console.print("  phase1 validate ./workspace")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
