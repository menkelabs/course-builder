"""
Phase 2A Command Line Interface

Standalone CLI for running the Phase 2A pipeline.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .client import Phase2AClient
from .config import Phase2AConfig

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
@click.version_option(version="0.1.0", prog_name="phase2a")
def cli():
    """
    Phase 2A - Automated Satellite Tracing
    
    Convert satellite imagery of golf courses into structured SVG geometry.
    """
    pass


@cli.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("phase2a_output"),
    help="Output directory",
)
@click.option(
    "-g", "--green-centers",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with green center coordinates",
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True, path_type=Path),
    help="YAML or JSON configuration file",
)
@click.option(
    "--checkpoint",
    type=click.Path(exists=True, path_type=Path),
    help="SAM model checkpoint path",
)
@click.option(
    "--high-threshold",
    type=float,
    default=0.85,
    help="High confidence threshold for auto-accept",
)
@click.option(
    "--low-threshold",
    type=float,
    default=0.5,
    help="Low confidence threshold (below = discard)",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--no-export-intermediates",
    is_flag=True,
    help="Skip saving intermediate outputs",
)
def run(
    image: Path,
    output: Path,
    green_centers: Optional[Path],
    config: Optional[Path],
    checkpoint: Optional[Path],
    high_threshold: float,
    low_threshold: float,
    verbose: bool,
    no_export_intermediates: bool,
):
    """
    Run the complete Phase 2A pipeline.
    
    IMAGE: Path to satellite image (PNG/JPG)
    """
    setup_logging(verbose)
    
    # Load or create config
    if config:
        if config.suffix in (".yml", ".yaml"):
            cfg = Phase2AConfig.from_yaml(config)
        else:
            cfg = Phase2AConfig.from_json(config)
    else:
        cfg = Phase2AConfig()
    
    # Override with CLI options
    cfg.input_image = image
    cfg.output_dir = output
    cfg.verbose = verbose
    cfg.export_intermediates = not no_export_intermediates
    
    if green_centers:
        cfg.green_centers_file = green_centers
    
    if checkpoint:
        cfg.sam.checkpoint_path = str(checkpoint)
    
    cfg.thresholds.high = high_threshold
    cfg.thresholds.low = low_threshold
    
    # Run pipeline
    console.print("\n[bold blue]Phase 2A Pipeline[/bold blue]")
    console.print(f"Input:  {image}")
    console.print(f"Output: {output}\n")
    
    try:
        client = Phase2AClient(cfg)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running pipeline...", total=None)
            
            png_path = client.run()
            
            progress.update(task, description="[green]Complete!")
        
        # Validate
        console.print()
        valid = client.validate()
        
        if valid:
            console.print("\n[green]✓ Pipeline completed successfully![/green]")
            console.print(f"  SVG: {output / 'course.svg'}")
            console.print(f"  PNG: {png_path}")
        else:
            console.print("\n[yellow]⚠ Pipeline completed with warnings[/yellow]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("masks"),
    help="Output directory for masks",
)
@click.option(
    "--checkpoint",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="SAM model checkpoint path",
)
@click.option(
    "--model-type",
    type=click.Choice(["vit_h", "vit_l", "vit_b"]),
    default="vit_h",
    help="SAM model variant",
)
@click.option(
    "--points-per-side",
    type=int,
    default=32,
    help="Points per side for grid sampling",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def generate_masks(
    image: Path,
    output: Path,
    checkpoint: Path,
    model_type: str,
    points_per_side: int,
    verbose: bool,
):
    """
    Generate SAM masks from an image (standalone).
    
    IMAGE: Path to satellite image
    """
    setup_logging(verbose)
    
    from .pipeline.masks import MaskGenerator
    
    console.print("\n[bold blue]Generating Masks[/bold blue]")
    console.print(f"Input:  {image}")
    console.print(f"Output: {output}\n")
    
    try:
        generator = MaskGenerator(
            model_type=model_type,
            checkpoint_path=str(checkpoint),
            points_per_side=points_per_side,
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating masks...", total=None)
            
            masks = generator.generate_from_file(image)
            generator.save_masks(masks, output)
            
            progress.update(task, description="[green]Complete!")
        
        console.print(f"\n[green]✓ Generated {len(masks)} masks[/green]")
        console.print(f"  Output: {output}")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("svg_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    help="Output PNG path (default: same name as SVG)",
)
@click.option(
    "-w", "--width",
    type=int,
    help="Output width (default: from SVG)",
)
@click.option(
    "-h", "--height",
    type=int,
    help="Output height (default: from SVG)",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def export_png(
    svg_path: Path,
    output: Optional[Path],
    width: Optional[int],
    height: Optional[int],
    verbose: bool,
):
    """
    Export SVG to PNG overlay (standalone).
    
    SVG_PATH: Path to input SVG file
    """
    setup_logging(verbose)
    
    from .pipeline.export import PNGExporter
    
    if output is None:
        output = svg_path.with_suffix(".png")
    
    console.print("\n[bold blue]Exporting PNG[/bold blue]")
    console.print(f"Input:  {svg_path}")
    console.print(f"Output: {output}\n")
    
    try:
        exporter = PNGExporter(width=width, height=height)
        exporter.export(svg_path, output)
        
        console.print(f"[green]✓ Exported PNG to {output}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("phase2a_config.yaml"),
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
    config = Phase2AConfig()
    
    if format == "yaml":
        config.to_yaml(output)
    else:
        config.to_json(output)
    
    console.print(f"[green]✓ Created config file: {output}[/green]")


@cli.command()
@click.argument("output_dir", type=click.Path(exists=True, path_type=Path))
def validate(output_dir: Path):
    """
    Validate pipeline output (svg_complete gate).
    
    OUTPUT_DIR: Path to Phase 2A output directory
    """
    console.print("\n[bold blue]Validating Output[/bold blue]")
    console.print(f"Directory: {output_dir}\n")
    
    svg_path = output_dir / "course.svg"
    png_path = output_dir / "exports" / "overlay.png"
    metadata_dir = output_dir / "metadata"
    
    # Run checks
    checks = []
    
    # SVG exists
    if svg_path.exists():
        checks.append(("SVG file exists", True, str(svg_path)))
    else:
        checks.append(("SVG file exists", False, "course.svg not found"))
    
    # PNG exists
    if png_path.exists():
        checks.append(("PNG overlay exists", True, str(png_path)))
    else:
        checks.append(("PNG overlay exists", False, "exports/overlay.png not found"))
    
    # Classifications
    classifications_path = metadata_dir / "classifications.json"
    if classifications_path.exists():
        with open(classifications_path) as f:
            classifications = json.load(f)
        
        classes = set(c["class"] for c in classifications)
        checks.append(("Has classifications", True, f"{len(classifications)} masks"))
        checks.append(("Has water", "water" in classes, ""))
        checks.append(("Has bunkers", "bunker" in classes, ""))
        checks.append(("Has greens", "green" in classes, ""))
    else:
        checks.append(("Has classifications", False, "classifications.json not found"))
    
    # Display results
    table = Table(title="Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")
    
    all_passed = True
    for check, passed, details in checks:
        status = "[green]✓ Pass[/green]" if passed else "[red]✗ Fail[/red]"
        table.add_row(check, status, details)
        if not passed:
            all_passed = False
    
    console.print(table)
    
    if all_passed:
        console.print("\n[green]✓ All validation checks passed![/green]")
    else:
        console.print("\n[red]✗ Some validation checks failed[/red]")
        sys.exit(1)


@cli.command()
def info():
    """
    Display Phase 2A pipeline information.
    """
    console.print("\n[bold blue]Phase 2A - Automated Satellite Tracing[/bold blue]\n")
    
    console.print("[bold]Pipeline Stages:[/bold]")
    stages = [
        ("1. Mask Generation", "SAM automatic mask generation"),
        ("2. Feature Extraction", "Color, texture, shape, context features"),
        ("3. Classification", "water, bunker, green, fairway, rough, ignore"),
        ("4. Confidence Gating", "Accept, review, or discard based on confidence"),
        ("5. Polygon Generation", "Convert masks to clean vector geometry"),
        ("6. Hole Assignment", "Assign features to holes 1-18, 98, 99"),
        ("7. SVG Generation", "Create layered SVG with OPCD classes"),
        ("8. SVG Cleanup", "Union, simplify, fix topology"),
        ("9. PNG Export", "Render final overlay image"),
    ]
    
    for stage, desc in stages:
        console.print(f"  {stage}: {desc}")
    
    console.print("\n[bold]Output Structure:[/bold]")
    console.print("""  phase2a_output/
    satellite_normalized.png
    masks/
    polygons/
    reviews/
    metadata/
      mask_features.json
      classifications.json
      hole_assignments.json
    course.svg
    exports/
      overlay.png
""")
    
    console.print("[bold]Usage:[/bold]")
    console.print("  phase2a run satellite.png --checkpoint sam_vit_h.pth")
    console.print("  phase2a generate-masks image.png --checkpoint sam.pth")
    console.print("  phase2a export-png course.svg -o overlay.png")
    console.print("  phase2a validate ./output")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
