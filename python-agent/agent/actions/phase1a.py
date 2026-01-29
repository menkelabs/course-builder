"""
Phase 1A Actions for the Python Agent.

Exposes Phase 1A pipeline functionality as remote actions that can
participate in Embabel's GOAP planning and execution.

Actions:
- phase1a_run: Run complete pipeline
- phase1a_generate_masks: Generate SAM masks
- phase1a_classify: Classify masks as features
- phase1a_generate_svg: Generate SVG output
- phase1a_export_png: Export SVG to PNG
- phase1a_validate: Validate pipeline output
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ..registry import get_registry
from ..models import Io, DynamicType, PropertyDef

logger = logging.getLogger(__name__)

# Get the global registry
registry = get_registry()


# =============================================================================
# Type Definitions
# =============================================================================

# Define domain types for Phase 1A inputs/outputs

Phase1AConfig = DynamicType(
    name="Phase1AConfig",
    description="Configuration for Phase 1A pipeline execution",
    own_properties=[
        PropertyDef("satellite_image", "string", "Path to satellite image (PNG/JPG)"),
        PropertyDef("checkpoint", "string", "Path to SAM checkpoint file"),
        PropertyDef("output_dir", "string", "Output directory for pipeline artifacts"),
        PropertyDef("device", "string", "Device to run SAM on (cuda or cpu)"),
        PropertyDef("high_threshold", "number", "High confidence threshold for auto-accept"),
        PropertyDef("low_threshold", "number", "Low confidence threshold (below = discard)"),
        PropertyDef("green_centers_file", "string", "Optional path to green_centers.json"),
        PropertyDef("verbose", "boolean", "Enable verbose output"),
    ],
)

Phase1AResult = DynamicType(
    name="Phase1AResult",
    description="Result from Phase 1A pipeline execution",
    own_properties=[
        PropertyDef("svg_file", "string", "Path to generated SVG file"),
        PropertyDef("png_file", "string", "Path to exported PNG overlay"),
        PropertyDef("output_dir", "string", "Output directory with all artifacts"),
        PropertyDef("masks_generated", "number", "Number of masks generated"),
        PropertyDef("features_classified", "object", "Classification counts by type"),
        PropertyDef("holes_assigned", "number", "Number of holes with assigned features"),
        PropertyDef("valid", "boolean", "Whether validation passed"),
    ],
)

MaskGenerationResult = DynamicType(
    name="MaskGenerationResult",
    description="Result from SAM mask generation",
    own_properties=[
        PropertyDef("masks_dir", "string", "Directory containing generated masks"),
        PropertyDef("mask_count", "number", "Number of masks generated"),
        PropertyDef("image_size", "object", "Image dimensions {width, height}"),
    ],
)

ClassificationResult = DynamicType(
    name="ClassificationResult",
    description="Result from mask classification",
    own_properties=[
        PropertyDef("classifications_file", "string", "Path to classifications JSON"),
        PropertyDef("counts", "object", "Classification counts by type"),
        PropertyDef("requires_review", "number", "Number of masks requiring review"),
    ],
)

SVGGenerationResult = DynamicType(
    name="SVGGenerationResult",
    description="Result from SVG generation",
    own_properties=[
        PropertyDef("svg_file", "string", "Path to generated SVG file"),
        PropertyDef("hole_layers", "number", "Number of hole layers in SVG"),
        PropertyDef("width", "number", "SVG width"),
        PropertyDef("height", "number", "SVG height"),
    ],
)

ValidationResult = DynamicType(
    name="ValidationResult",
    description="Result from output validation (svg_complete gate)",
    own_properties=[
        PropertyDef("valid", "boolean", "Whether all checks passed"),
        PropertyDef("checks", "object", "Individual check results"),
        PropertyDef("errors", "array", "List of validation errors"),
    ],
)

# Register all types
for dtype in [Phase1AConfig, Phase1AResult, MaskGenerationResult, 
              ClassificationResult, SVGGenerationResult, ValidationResult]:
    registry.register_type(dtype)


# =============================================================================
# Helper Functions
# =============================================================================

def _get_phase1a_client(params: Dict[str, Any]):
    """Create a Phase 1A client with given parameters."""
    try:
        # Add phase1a to path if needed
        phase1a_path = Path(__file__).parent.parent.parent.parent / "phase1a"
        if str(phase1a_path) not in sys.path:
            sys.path.insert(0, str(phase1a_path.parent))
        
        from phase1a.client import Phase1AClient
        from phase1a.config import Phase1AConfig as Phase1AConfigClass
        
        config = Phase1AConfigClass()
        
        if "satellite_image" in params:
            config.input_image = Path(params["satellite_image"])
        if "output_dir" in params:
            config.output_dir = Path(params["output_dir"])
        if "checkpoint" in params:
            config.sam.checkpoint_path = params["checkpoint"]
        if "device" in params:
            config.sam.device = params["device"]
        if "high_threshold" in params:
            config.thresholds.high = params["high_threshold"]
        if "low_threshold" in params:
            config.thresholds.low = params["low_threshold"]
        if "green_centers_file" in params:
            config.green_centers_file = Path(params["green_centers_file"])
        if "verbose" in params:
            config.verbose = params["verbose"]
        
        return Phase1AClient(config)
    except ImportError as e:
        logger.warning(f"Phase 1A not available: {e}")
        return None


# =============================================================================
# Action Handlers
# =============================================================================

@registry.action(
    name="phase1a_run",
    description="Run the complete Phase1A pipeline: satellite image → SAM masks → "
                "classification → SVG. Automatically extracts and classifies course features.",
    inputs=[Io("config", "Phase1AConfig")],
    outputs=[Io("result", "Phase1AResult")],
    pre=["satellite_image_exists"],
    post=["svg_complete"],
    cost=0.8,
    value=0.9,
    can_rerun=True,
)
async def phase1a_run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run complete Phase1A pipeline."""
    config = params.get("config", params)  # Allow direct params or nested config
    
    client = _get_phase1a_client(config)
    
    if client is None:
        # Return mock result for testing/development
        output_dir = config.get("output_dir", "/output/phase1a/")
        return {
            "svg_file": f"{output_dir}/course.svg",
            "png_file": f"{output_dir}/exports/overlay.png",
            "output_dir": output_dir,
            "masks_generated": 150,
            "features_classified": {
                "green": 18,
                "fairway": 18,
                "bunker": 45,
                "water": 5,
                "tee": 18,
                "rough": 30,
            },
            "holes_assigned": 18,
            "valid": True,
            "_mock": True,
        }
    
    # Run actual pipeline
    try:
        png_path = client.run()
        
        return {
            "svg_file": str(client.output_dir / "course.svg"),
            "png_file": str(png_path),
            "output_dir": str(client.output_dir),
            "masks_generated": len(client.state.masks),
            "features_classified": _count_classifications(client.state.classifications),
            "holes_assigned": len(client.state.assignments_by_hole),
            "valid": client.validate(),
        }
    except Exception as e:
        logger.exception(f"Phase1A pipeline error: {e}")
        raise


@registry.action(
    name="phase1a_generate_masks",
    description="Generate candidate masks from satellite image using SAM (Segment Anything Model).",
    inputs=[
        Io("satellite_image", "string"),
        Io("checkpoint", "string"),
        Io("output_dir", "string"),
    ],
    outputs=[Io("result", "MaskGenerationResult")],
    pre=["satellite_image_exists"],
    post=["masks_generated"],
    cost=0.7,
    value=0.3,
    can_rerun=True,
)
async def phase1a_generate_masks(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate SAM masks from satellite image."""
    satellite_image = params.get("satellite_image")
    checkpoint = params.get("checkpoint")
    output_dir = params.get("output_dir", "/output/masks/")
    
    client = _get_phase1a_client(params)
    
    if client is None:
        # Mock result
        return {
            "masks_dir": output_dir,
            "mask_count": 150,
            "image_size": {"width": 4096, "height": 4096},
            "_mock": True,
        }
    
    try:
        masks = client.generate_masks()
        image = client.state.image
        
        return {
            "masks_dir": str(client.output_dir / "masks"),
            "mask_count": len(masks),
            "image_size": {
                "width": image.shape[1],
                "height": image.shape[0],
            },
        }
    except Exception as e:
        logger.exception(f"Mask generation error: {e}")
        raise


@registry.action(
    name="phase1a_classify",
    description="Classify masks as water, bunker, green, fairway, rough, or ignore "
                "based on color/texture analysis.",
    inputs=[
        Io("masks_dir", "string"),
        Io("satellite_image", "string"),
    ],
    outputs=[Io("result", "ClassificationResult")],
    pre=["masks_generated"],
    post=["masks_classified"],
    cost=0.3,
    value=0.4,
    can_rerun=True,
)
async def phase1a_classify(params: Dict[str, Any]) -> Dict[str, Any]:
    """Classify masks as course features."""
    masks_dir = params.get("masks_dir")
    
    client = _get_phase1a_client(params)
    
    if client is None:
        # Mock result
        return {
            "classifications_file": f"{masks_dir}/../metadata/classifications.json",
            "counts": {
                "green": 18,
                "fairway": 18,
                "bunker": 45,
                "water": 5,
                "rough": 30,
                "tee": 18,
                "ignore": 16,
            },
            "requires_review": 8,
            "_mock": True,
        }
    
    try:
        # Load masks if needed
        if not client.state.masks:
            client.load_masks(Path(masks_dir))
        
        client.extract_features()
        classifications = client.classify_masks()
        
        return {
            "classifications_file": str(client.output_dir / "metadata" / "classifications.json"),
            "counts": _count_classifications(classifications),
            "requires_review": len(client.state.review) if hasattr(client.state, 'review') else 0,
        }
    except Exception as e:
        logger.exception(f"Classification error: {e}")
        raise


@registry.action(
    name="phase1a_generate_svg",
    description="Generate layered SVG from classified features and hole assignments. "
                "Creates course.svg with proper layers for Unity/Blender/GSPro.",
    inputs=[
        Io("output_dir", "string"),
        Io("include_hole_98", "boolean"),
        Io("include_hole_99", "boolean"),
    ],
    outputs=[Io("result", "SVGGenerationResult")],
    pre=["masks_classified", "holes_assigned"],
    post=["svg_generated"],
    cost=0.2,
    value=0.5,
    can_rerun=True,
)
async def phase1a_generate_svg(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate SVG from classified features."""
    output_dir = params.get("output_dir", "/output/phase1a/")
    include_hole_98 = params.get("include_hole_98", True)
    include_hole_99 = params.get("include_hole_99", True)
    
    client = _get_phase1a_client(params)
    
    if client is None:
        # Mock result
        layer_count = 18 + (1 if include_hole_98 else 0) + (1 if include_hole_99 else 0)
        return {
            "svg_file": f"{output_dir}/course.svg",
            "hole_layers": layer_count,
            "width": 4096,
            "height": 4096,
            "_mock": True,
        }
    
    try:
        svg_content = client.generate_svg()
        client.cleanup_svg()
        
        image = client.state.image
        layer_count = len(client.state.assignments_by_hole)
        
        return {
            "svg_file": str(client.output_dir / "course.svg"),
            "hole_layers": layer_count,
            "width": image.shape[1],
            "height": image.shape[0],
        }
    except Exception as e:
        logger.exception(f"SVG generation error: {e}")
        raise


@registry.action(
    name="phase1a_export_png",
    description="Export SVG to PNG overlay for Unity terrain visualization.",
    inputs=[
        Io("svg_file", "string"),
        Io("output_file", "string"),
        Io("resolution", "number"),
    ],
    outputs=[Io("png_file", "string")],
    pre=["svg_generated"],
    post=["png_exported"],
    cost=0.1,
    value=0.3,
    can_rerun=True,
)
async def phase1a_export_png(params: Dict[str, Any]) -> Dict[str, Any]:
    """Export SVG to PNG overlay."""
    svg_file = params.get("svg_file")
    output_file = params.get("output_file")
    resolution = params.get("resolution", 4096)
    
    if output_file is None:
        output_file = str(Path(svg_file).with_suffix(".png"))
    
    try:
        # Add phase1a to path if needed
        phase1a_path = Path(__file__).parent.parent.parent.parent / "phase1a"
        if str(phase1a_path) not in sys.path:
            sys.path.insert(0, str(phase1a_path.parent))
        
        from phase1a.pipeline.export import PNGExporter
        
        exporter = PNGExporter(width=resolution, height=resolution)
        exporter.export(Path(svg_file), Path(output_file))
        
        return {
            "png_file": output_file,
            "resolution": resolution,
        }
    except ImportError:
        # Mock result
        return {
            "png_file": output_file,
            "resolution": resolution,
            "_mock": True,
        }
    except Exception as e:
        logger.exception(f"PNG export error: {e}")
        raise


@registry.action(
    name="phase1a_validate",
    description="Validate Phase 1A output directory - check all required files and "
                "metadata are present (svg_complete gate).",
    inputs=[Io("output_dir", "string")],
    outputs=[Io("result", "ValidationResult")],
    pre=["svg_generated"],
    post=["svg_complete"],
    cost=0.05,
    value=0.2,
    can_rerun=True,
)
async def phase1a_validate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Phase1A output."""
    output_dir = Path(params.get("output_dir", "/output/phase1a/"))
    
    checks = {}
    errors = []
    
    # Check required files
    required_files = [
        ("course.svg", "SVG file exists"),
        ("exports/overlay.png", "PNG overlay exists"),
        ("metadata/classifications.json", "Classifications exist"),
        ("metadata/hole_assignments.json", "Hole assignments exist"),
    ]
    
    for file_path, check_name in required_files:
        full_path = output_dir / file_path
        exists = full_path.exists()
        checks[check_name] = exists
        if not exists:
            errors.append(f"Missing: {file_path}")
    
    # Check SVG content if it exists
    svg_path = output_dir / "course.svg"
    if svg_path.exists():
        try:
            content = svg_path.read_text()
            checks["SVG has content"] = len(content) > 100
            checks["SVG has layers"] = "inkscape:groupmode" in content or "g id=" in content
        except Exception as e:
            checks["SVG readable"] = False
            errors.append(f"SVG read error: {e}")
    
    valid = len(errors) == 0 and all(checks.values())
    
    return {
        "valid": valid,
        "checks": checks,
        "errors": errors,
    }


def _count_classifications(classifications) -> Dict[str, int]:
    """Count classifications by type."""
    counts = {}
    for c in classifications:
        feature_class = c.feature_class if hasattr(c, 'feature_class') else c.get('class', 'unknown')
        counts[feature_class] = counts.get(feature_class, 0) + 1
    return counts
