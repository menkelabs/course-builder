"""
Phase 2A Command Line Interface

Standalone CLI for running the Phase 2A pipeline.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import click
import numpy as np
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .client import Phase2AClient
from .config import Phase2AConfig

if TYPE_CHECKING:
    from .pipeline.interactive import InteractiveSelector, FeatureType

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
    "--device",
    type=click.Choice(["cuda", "cpu"]),
    default="cuda",
    help="Device to run SAM on (cuda or cpu)",
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
    device: str,
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
    
    cfg.sam.device = device
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


@cli.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path("phase2a_output"),
    help="Output directory",
)
@click.option(
    "--checkpoint",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="SAM model checkpoint path",
)
@click.option(
    "--selections",
    type=click.Path(path_type=Path),
    help="Load existing selections JSON file",
)
@click.option(
    "--model-type",
    type=click.Choice(["vit_h", "vit_l", "vit_b"]),
    default="vit_h",
    help="SAM model variant",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def select(
    image: Path,
    output: Path,
    checkpoint: Path,
    selections: Optional[Path],
    model_type: str,
    verbose: bool,
):
    """
    Interactive hole-by-hole feature selection workflow.
    
    Workflow:
    1. For each hole (1-18):
       a. Prompt: "Click on the green for hole N"
       b. User clicks on image - tool generates mask around that point
       c. Prompt: "Click on the tee for hole N"
       d. User clicks on image - tool generates mask around that point
       e. Prompt: "Click on fairway items for hole N"
       f. User clicks on image - tool generates mask around that point
       g. Prompt: "Click on bunkers for hole N"
       h. User clicks on image - tool generates mask around that point
    
    The tool uses SAM to automatically find the area around each click point
    and assigns it to the appropriate feature type for Inkscape export.
    
    IMAGE: Path to satellite image (PNG/JPG)
    """
    setup_logging(verbose)
    
    from PIL import Image
    from .pipeline.masks import MaskGenerator
    from .pipeline.interactive import InteractiveSelector, FeatureType
    
    console.print("\n[bold blue]Interactive Feature Selection[/bold blue]")
    console.print(f"Input:  {image}")
    console.print(f"Output: {output}\n")
    
    try:
        # Load image
        image_array = np.array(Image.open(image).convert("RGB"))
        
        # Initialize mask generator for point-based selection
        console.print("[cyan]Initializing SAM model for point-based mask generation...[/cyan]")
        generator = MaskGenerator(
            model_type=model_type,
            checkpoint_path=str(checkpoint),
            device="cuda",  # Use CUDA if available
        )
        
        # Initialize point-based selector
        from .pipeline.point_selector import PointBasedSelector
        selector = PointBasedSelector(image_array, generator)
        
        console.print("[green]✓ Ready for interactive selection[/green]")
        console.print("[dim]Click on the image to mark feature locations. SAM will find the area around each click.[/dim]\n")
        
        # Interactive selection workflow with matplotlib (point-based)
        try:
            from .pipeline.visualize import InteractiveMaskSelector
        except ImportError:
            console.print("[red]matplotlib is required for interactive selection[/red]")
            sys.exit(1)
        else:
            _interactive_point_mode(console, selector, image_array)
        
        # Save selections and generated masks
        output.mkdir(parents=True, exist_ok=True)
        metadata_dir = output / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Save selections
        selections_path = metadata_dir / "interactive_selections.json"
        selections_data = {
            "selections": {
                str(hole): selection.to_dict()
                for hole, selection in selector.get_all_selections().items()
            }
        }
        with open(selections_path, "w") as f:
            json.dump(selections_data, f, indent=2)
        console.print(f"\n[green]✓ Saved selections to {selections_path}[/green]")
        
        # Save generated masks
        if selector.generated_masks:
            masks_dir = output / "masks"
            masks_dir.mkdir(parents=True, exist_ok=True)
            from .pipeline.masks import MaskGenerator
            # Create a temporary generator just for saving
            temp_gen = MaskGenerator(checkpoint_path=str(checkpoint))
            temp_gen.save_masks(list(selector.generated_masks.values()), masks_dir)
            console.print(f"[green]✓ Saved {len(selector.generated_masks)} generated masks to {masks_dir}[/green]")
        
        # Extract and save green centers from selected green masks
        green_centers = selector.extract_green_centers()
        if green_centers:
            green_centers_path = metadata_dir / "green_centers.json"
            with open(green_centers_path, "w") as f:
                json.dump(green_centers, f, indent=2)
            console.print(f"[green]✓ Extracted and saved green centers to {green_centers_path}[/green]")
            console.print(f"[dim]   Found green centers for {len(green_centers)} holes[/dim]")
        else:
            console.print("[yellow]⚠ No green centers extracted (no green selections found)[/yellow]")
        
        console.print("\n[bold green]Selection complete![/bold green]")
        console.print(f"[dim]Next: Use these selections with the pipeline[/dim]")
        if green_centers:
            console.print(f"[dim]   Green centers saved to: {green_centers_path}[/dim]")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


def _interactive_point_mode(console, selector, image_array):
    """Interactive point-based selection using matplotlib clicking."""
    from .pipeline.visualize import InteractiveMaskSelector
    from .pipeline.interactive import FeatureType
    
    console.print("[cyan]Interactive Point Selection Mode[/cyan]")
    console.print("[dim]Click anywhere on the image to mark feature locations.[/dim]")
    console.print("[dim]SAM will automatically find the area around each click.[/dim]")
    console.print("[dim]Press Enter/Space or click 'Done' when finished with each feature.[/dim]\n")
    
    holes_to_process = list(range(1, 19))  # Holes 1-18
    
    for hole in holes_to_process:
        console.print(f"\n[bold yellow]Hole {hole}[/bold yellow]")
        
        feature_types = [
            (FeatureType.GREEN, "green(s)"),
            (FeatureType.TEE, "tee(s)"),
            (FeatureType.FAIRWAY, "fairway items"),
            (FeatureType.BUNKER, "bunker(s)"),
        ]
        
        for feature_type, feature_name in feature_types:
            console.print(f"\n[cyan]Click on {feature_name} for hole {hole}[/cyan]")
            console.print("[dim]Click on the image where you see the {feature_name}. You can click multiple times.[/dim]")
            console.print("[dim]Press Enter/Space or click 'Done' when finished[/dim]")
            
            # Create interactive selector
            interactive = InteractiveMaskSelector(
                selector,
                title=f"Hole {hole} - Click on {feature_name} (SAM will find the area)",
            )
            
            # Set current hole and feature type for point-based generation
            interactive._current_hole = hole
            interactive._current_feature_type = feature_type
            
            # Show current selections for this feature type
            hole_selection = selector.get_selection_for_hole(hole)
            if hole_selection:
                if feature_type == FeatureType.GREEN:
                    existing = hole_selection.greens
                elif feature_type == FeatureType.TEE:
                    existing = hole_selection.tees
                elif feature_type == FeatureType.FAIRWAY:
                    existing = hole_selection.fairways
                elif feature_type == FeatureType.BUNKER:
                    existing = hole_selection.bunkers
                else:
                    existing = []
                interactive.selected_mask_ids = existing.copy()
            
            # Show interactive window (blocks until Done is pressed)
            interactive.show(block=True)
            
            # Get selected masks (already assigned via click_to_mask)
            selected_ids = interactive.get_selected_mask_ids()
            
            if selected_ids:
                console.print(f"[green]✓ Marked {len(selected_ids)} {feature_name} location(s)[/green]")
            else:
                console.print(f"[dim]No {feature_name} marked[/dim]")


def _interactive_click_mode(console, selector):
    """Interactive selection using matplotlib clicking with buttons/keyboard."""
    from .pipeline.visualize import InteractiveMaskSelector
    from .pipeline.interactive import FeatureType
    
    console.print("[cyan]Interactive Click Mode[/cyan]")
    console.print("[dim]Click on masks in the image window to select them.[/dim]")
    console.print("[dim]Press Enter/Space or click 'Done' button when finished with each feature.[/dim]\n")
    
    holes_to_process = list(range(1, 19))  # Holes 1-18
    
    for hole in holes_to_process:
        console.print(f"\n[bold yellow]Hole {hole}[/bold yellow]")
        
        feature_types = [
            (FeatureType.GREEN, "green(s)"),
            (FeatureType.TEE, "tee(s)"),
            (FeatureType.FAIRWAY, "fairway items"),
            (FeatureType.BUNKER, "bunker(s)"),
        ]
        
        for feature_type, feature_name in feature_types:
            console.print(f"\n[cyan]Select {feature_name} for hole {hole}[/cyan]")
            console.print("[dim]Window will open - click masks to select, press Enter/Space or click 'Done' when finished[/dim]")
            
            # Create interactive selector
            interactive = InteractiveMaskSelector(
                selector,
                title=f"Hole {hole} - Select {feature_name} (Click masks, then Enter/Space/Done)",
            )
            
            # Show current selections for this feature type
            hole_selection = selector.get_selection_for_hole(hole)
            if hole_selection:
                if feature_type == FeatureType.GREEN:
                    existing = hole_selection.greens
                elif feature_type == FeatureType.TEE:
                    existing = hole_selection.tees
                elif feature_type == FeatureType.FAIRWAY:
                    existing = hole_selection.fairways
                elif feature_type == FeatureType.BUNKER:
                    existing = hole_selection.bunkers
                else:
                    existing = []
                interactive.selected_mask_ids = existing.copy()
            
            # Show interactive window (blocks until Done is pressed)
            interactive.show(block=True)
            
            # Get selected masks
            selected_ids = interactive.get_selected_mask_ids()
            
            if selected_ids:
                selector.select_for_hole(hole, feature_type, selected_ids)
                console.print(f"[green]✓ Selected {len(selected_ids)} {feature_name}[/green]")
            else:
                console.print(f"[dim]No {feature_name} selected[/dim]")
        
        # Optional: water and rough
        console.print(f"\n[dim]Add water/rough for hole {hole}? (y/N):[/dim]")
        if click.prompt("", default="n", show_default=False).lower() == 'y':
            for feature_type, feature_name in [
                (FeatureType.WATER, "water"),
                (FeatureType.ROUGH, "rough"),
            ]:
                console.print(f"\n[cyan]Select {feature_name} for hole {hole}[/cyan]")
                interactive = InteractiveMaskSelector(
                    selector,
                    title=f"Hole {hole} - Select {feature_name} (Enter/Space/Done when done)",
                )
                interactive.show(block=True)
                selected_ids = interactive.get_selected_mask_ids()
                if selected_ids:
                    selector.select_for_hole(hole, feature_type, selected_ids)
                    console.print(f"[green]✓ Selected {len(selected_ids)} {feature_name}[/green]")


def _interactive_text_mode(console, selector):
    """Fallback text-based selection mode."""
    from .pipeline.interactive import FeatureType
    
    console.print("[cyan]Interactive Selection Mode (Text Input)[/cyan]")
    console.print("[dim]For each hole, you'll be prompted to select features.[/dim]")
    console.print("[dim]You can type mask IDs or use coordinates (format: x,y)[/dim]\n")
    
    holes_to_process = list(range(1, 19))  # Holes 1-18
    
    for hole in holes_to_process:
        console.print(f"\n[bold yellow]Hole {hole}[/bold yellow]")
        
        # Green selection
        _prompt_feature_selection(
            console, selector, hole, FeatureType.GREEN, "green(s)"
        )
        
        # Tee selection
        _prompt_feature_selection(
            console, selector, hole, FeatureType.TEE, "tee(s)"
        )
        
        # Fairway selection
        _prompt_feature_selection(
            console, selector, hole, FeatureType.FAIRWAY, "fairway items"
        )
        
        # Bunker selection
        _prompt_feature_selection(
            console, selector, hole, FeatureType.BUNKER, "bunker(s)"
        )
        
        # Optional: water and rough
        console.print(f"\n[dim]Press Enter to skip water/rough for hole {hole}, or type 'y' to add:[/dim]")
        if click.prompt("", default="", show_default=False).lower() == 'y':
            _prompt_feature_selection(
                console, selector, hole, FeatureType.WATER, "water"
            )
            _prompt_feature_selection(
                console, selector, hole, FeatureType.ROUGH, "rough"
            )


def _prompt_feature_selection(
    console,
    selector: "InteractiveSelector",
    hole: int,
    feature_type: "FeatureType",
    prompt_text: str,
):
    """Helper to prompt for feature selection."""
    console.print(f"[cyan]Select {prompt_text} for hole {hole}:[/cyan]")
    console.print("[dim]Enter mask IDs (comma-separated) or coordinates (x,y format)[/dim]")
    console.print("[dim]Press Enter to skip[/dim]")
    
    response = click.prompt("", default="", show_default=False).strip()
    
    if not response:
        return
    
    # Parse input - could be mask IDs or coordinates
    mask_ids = []
    
    for item in response.split(','):
        item = item.strip()
        if not item:
            continue
        
        # Check if it's coordinates (x,y format)
        if ',' in item:
            try:
                parts = item.split(',')
                if len(parts) == 2:
                    x, y = int(parts[0].strip()), int(parts[1].strip())
                    mask_id = selector.get_mask_at_point(x, y)
                    if mask_id:
                        mask_ids.append(mask_id)
                    else:
                        console.print(f"[yellow]No mask found at ({x}, {y})[/yellow]")
            except ValueError:
                console.print(f"[yellow]Invalid coordinate format: {item}[/yellow]")
        else:
            # Assume it's a mask ID
            mask_id = f"mask_{int(item):04d}" if item.isdigit() else item
            if mask_id in selector.masks:
                mask_ids.append(mask_id)
            else:
                console.print(f"[yellow]Mask ID not found: {mask_id}[/yellow]")
    
    if mask_ids:
        selector.select_for_hole(hole, feature_type, mask_ids)
        console.print(f"[green]✓ Selected {len(mask_ids)} mask(s)[/green]")
    else:
        console.print("[dim]No masks selected[/dim]")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
