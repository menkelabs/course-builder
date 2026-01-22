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
@click.option(
    "-c", "--config",
    type=click.Path(exists=True, path_type=Path),
    help="YAML or JSON configuration file (for default location)",
)
@click.option(
    "--course-name",
    type=str,
    required=True,
    help="Course name",
)
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("workspace"),
    help="Workspace output directory",
)
@click.option(
    "--template",
    type=click.Path(exists=True, path_type=Path),
    help="Path to QGIS template project (.qgz)",
)
@click.option(
    "--timeout",
    type=int,
    default=1800,
    help="Timeout in seconds for user selection (default: 1800 = 30 minutes)",
)
@click.option(
    "--zip-code",
    type=str,
    help="Zip code or postal code to center map (e.g., '90210' or '90210, US')",
)
@click.option(
    "--address",
    type=str,
    help="Address to center map (e.g., 'Pebble Beach Golf Course, CA')",
)
@click.option(
    "--center-lat",
    type=float,
    help="Initial map center latitude (WGS84) - overrides zip-code/address",
)
@click.option(
    "--center-lon",
    type=float,
    help="Initial map center longitude (WGS84) - overrides zip-code/address",
)
@click.option(
    "--zoom-level",
    type=int,
    default=15,
    help="Initial zoom level (1-19, default: 15). Recommended: 15-16 for viewing full course",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def interactive_select(
    config: Optional[Path],
    course_name: str,
    output: Path,
    template: Optional[Path],
    timeout: int,
    zip_code: Optional[str],
    address: Optional[str],
    center_lat: Optional[float],
    center_lon: Optional[float],
    zoom_level: int,
    verbose: bool,
):
    """
    Launch QGIS for interactive course boundary selection.
    
    This opens QGIS with a template project. Draw a polygon around
    the golf course, then save it. The script will continue automatically.
    
    You can optionally provide initial map center coordinates to position
    the map near your golf course location.
    """
    setup_logging(verbose)
    
    # Load config if provided
    cfg = Phase1Config()
    if config:
        if config.suffix in (".yml", ".yaml"):
            cfg = Phase1Config.from_yaml(config)
        else:
            cfg = Phase1Config.from_json(config)
    
    # Override config with CLI options
    cfg.course_name = course_name
    cfg.workspace.workspace_path = output
    cfg.interactive.selection_timeout = timeout
    if template:
        cfg.interactive.template_qgz = template
    cfg.verbose = verbose
    
    console.print("\n[bold blue]Interactive Course Selection[/bold blue]")
    console.print(f"Course: {course_name}")
    console.print(f"Workspace: {output}")
    
    # Determine initial location
    # Priority: CLI args > config location > None
    initial_location = None
    
    # Use CLI args if provided, otherwise fall back to config
    use_address = address or (cfg.location.address if not address and cfg.location.address else None)
    use_zip = zip_code or (cfg.location.zip_code if not zip_code and cfg.location.zip_code else None)
    use_lat = center_lat if center_lat is not None else (cfg.location.center_lat if cfg.location.center_lat else None)
    use_lon = center_lon if center_lon is not None else (cfg.location.center_lon if cfg.location.center_lon else None)
    use_zoom = zoom_level if zoom_level != 15 else (cfg.location.zoom_level if cfg.location.zoom_level != 15 else 15)
    
    # Priority: explicit coordinates > zip code > address
    if use_lat and use_lon:
        initial_location = {
            'lat': use_lat,
            'lon': use_lon,
            'zoom': use_zoom
        }
        console.print(f"Initial location: {use_lat:.6f}, {use_lon:.6f} (zoom: {use_zoom})")
    elif use_zip:
        console.print(f"Geocoding zip code: {use_zip}")
        from .pipeline.geocoding import geocode_zip_code
        location = geocode_zip_code(use_zip)
        if location:
            location['zoom'] = use_zoom
            initial_location = location
            console.print(f"  → Location: {location['lat']:.6f}, {location['lon']:.6f} (zoom: {use_zoom})")
        else:
            console.print(f"  [yellow]⚠ Could not geocode zip code. Map will open at default location.[/yellow]")
    elif use_address:
        console.print(f"Geocoding address: {use_address}")
        from .pipeline.geocoding import geocode_address
        location = geocode_address(use_address)
        if location:
            location['zoom'] = use_zoom
            initial_location = location
            console.print(f"  → Location: {location['lat']:.6f}, {location['lon']:.6f} (zoom: {use_zoom})")
        else:
            console.print(f"  [yellow]⚠ Could not geocode address. Map will open at default location.[/yellow]")
    
    console.print(f"Timeout: {timeout} seconds ({timeout // 60} minutes)\n")
    
    try:
        cfg.interactive.enable_interactive = True
        client = Phase1Client(cfg)
        bounds = client.interactive_course_selection(initial_location=initial_location)
        
        console.print("\n[green]✓ Course boundary selected![/green]")
        console.print(f"\nBounds:")
        console.print(f"  North: {bounds['northLat']:.6f}")
        console.print(f"  South: {bounds['southLat']:.6f}")
        console.print(f"  East:  {bounds['eastLon']:.6f}")
        console.print(f"  West:  {bounds['westLon']:.6f}")
        console.print(f"  Area:  {bounds['area_km2']:.2f} km²")
        
        # Save bounds JSON path
        bounds_json = output / "course_bounds.json"
        console.print(f"\nBounds saved to: {bounds_json}")
        console.print("\nYou can now run the full pipeline:")
        console.print(f"  python -m phase1.cli run --course-name {course_name} -o {output}")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


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
    console.print("  # Activate root .venv first:")
    console.print("  source .venv/bin/activate  # (from project root)")
    console.print("")
    console.print("  # Then run commands:")
    console.print("  python -m phase1.cli run --course-name MyCourse -o workspace/")
    console.print("  python -m phase1.cli interactive-select --course-name MyCourse -o workspace/")
    console.print("  python -m phase1.cli init-config -o config.yaml")
    console.print("  python -m phase1.cli validate ./workspace")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
