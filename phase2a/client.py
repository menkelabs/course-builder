"""
Phase 2A Pipeline Client

Main client class that orchestrates the complete Phase 2A pipeline.
Can be used as a library or via CLI.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum

import numpy as np
from PIL import Image

from .config import Phase2AConfig
from .pipeline import (
    MaskGenerator,
    FeatureExtractor,
    MaskClassifier,
    ConfidenceGate,
    PolygonGenerator,
    HoleAssigner,
    SVGGenerator,
    SVGCleaner,
    PNGExporter,
)
from .pipeline.masks import MaskData
from .pipeline.features import MaskFeatures
from .pipeline.classify import Classification
from .pipeline.gating import GatedMask
from .pipeline.polygons import PolygonFeature
from .pipeline.holes import HoleAssignment

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Pipeline execution stages."""
    MASKS = "masks"
    FEATURES = "features"
    CLASSIFY = "classify"
    GATE = "gate"
    POLYGONS = "polygons"
    HOLES = "holes"
    SVG = "svg"
    CLEANUP = "cleanup"
    EXPORT = "export"


@dataclass
class PipelineState:
    """Current state of the pipeline execution."""
    image: Optional[np.ndarray] = None
    images: List[np.ndarray] = field(default_factory=list)  # Multiple images for feature extraction
    masks: List[MaskData] = field(default_factory=list)
    features: List[MaskFeatures] = field(default_factory=list)
    classifications: List[Classification] = field(default_factory=list)
    accepted: List[GatedMask] = field(default_factory=list)
    review: List[GatedMask] = field(default_factory=list)
    discarded: List[GatedMask] = field(default_factory=list)
    polygons: List[PolygonFeature] = field(default_factory=list)
    assignments_by_hole: Dict[int, List[HoleAssignment]] = field(default_factory=dict)
    svg_content: Optional[str] = None
    
    completed_stages: List[PipelineStage] = field(default_factory=list)


class Phase2AClient:
    """
    Main client for the Phase 2A pipeline.
    
    The pipeline consists of these stages:
    1. Mask Generation (SAM)
    2. Feature Extraction
    3. Classification
    4. Confidence Gating
    5. Polygon Generation
    6. Hole Assignment
    7. SVG Generation
    8. SVG Cleanup
    9. PNG Export
    
    Usage:
        # Full pipeline
        client = Phase2AClient(config)
        client.run()
        
        # Step-by-step
        client = Phase2AClient(config)
        client.generate_masks()
        client.extract_features()
        client.classify_masks()
        client.gate_masks()
        client.generate_polygons()
        client.assign_holes()
        client.generate_svg()
        client.cleanup_svg()
        client.export_png()
    """
    
    def __init__(self, config: Optional[Phase2AConfig] = None):
        """
        Initialize the Phase 2A client.
        
        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or Phase2AConfig()
        self.state = PipelineState()
        
        # Initialize components
        self._mask_generator: Optional[MaskGenerator] = None
        self._feature_extractor: Optional[FeatureExtractor] = None
        self._classifier: Optional[MaskClassifier] = None
        self._gate: Optional[ConfidenceGate] = None
        self._polygon_generator: Optional[PolygonGenerator] = None
        self._hole_assigner: Optional[HoleAssigner] = None
        self._svg_generator: Optional[SVGGenerator] = None
        self._svg_cleaner: Optional[SVGCleaner] = None
        self._png_exporter: Optional[PNGExporter] = None
        
        # Setup logging
        if self.config.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
    
    @property
    def output_dir(self) -> Path:
        """Get output directory, creating if needed."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        return self.config.output_dir
    
    def _load_image(self) -> np.ndarray:
        """Load the primary input satellite image (for mask generation)."""
        if self.state.image is not None:
            return self.state.image
        
        # Use first image from input_images if available, otherwise input_image
        image_path = None
        if self.config.input_images:
            image_path = self.config.input_images[0]
        elif self.config.input_image:
            image_path = self.config.input_image
        else:
            raise ValueError("No input image specified")
        
        logger.info(f"Loading primary image from {image_path}")
        self.state.image = np.array(
            Image.open(image_path).convert("RGB")
        )
        return self.state.image
    
    def _load_images(self) -> List[np.ndarray]:
        """Load all input satellite images (for multi-image feature extraction)."""
        if self.state.images:
            return self.state.images
        
        # Determine which images to load
        image_paths = []
        if self.config.input_images:
            image_paths = self.config.input_images
        elif self.config.input_image:
            image_paths = [self.config.input_image]
        else:
            raise ValueError("No input images specified")
        
        logger.info(f"Loading {len(image_paths)} image(s) for feature extraction")
        self.state.images = [
            np.array(Image.open(path).convert("RGB"))
            for path in image_paths
        ]
        
        # Also set primary image if not set
        if self.state.image is None:
            self.state.image = self.state.images[0]
        
        return self.state.images
    
    def _load_green_centers(self) -> Optional[List[Dict]]:
        """Load green centers if available."""
        if self.config.green_centers_file is None:
            return None
        
        if not self.config.green_centers_file.exists():
            logger.warning(
                f"Green centers file not found: {self.config.green_centers_file}"
            )
            return None
        
        with open(self.config.green_centers_file) as f:
            return json.load(f)
    
    # =========================================================================
    # Pipeline Stages
    # =========================================================================
    
    def generate_masks(self) -> List[MaskData]:
        """
        Stage 1: Generate masks using SAM.
        
        Returns:
            List of MaskData objects
        """
        logger.info("Stage 1: Generating masks...")
        
        if self._mask_generator is None:
            self._mask_generator = MaskGenerator(
                model_type=self.config.sam.model_type,
                checkpoint_path=self.config.sam.checkpoint_path,
                points_per_side=self.config.sam.points_per_side,
                pred_iou_thresh=self.config.sam.pred_iou_thresh,
                stability_score_thresh=self.config.sam.stability_score_thresh,
                min_mask_region_area=self.config.sam.min_mask_region_area,
            )
        
        image = self._load_image()
        self.state.masks = self._mask_generator.generate(image)
        
        # Save if configured
        if self.config.export_intermediates:
            masks_dir = self.output_dir / "masks"
            self._mask_generator.save_masks(self.state.masks, masks_dir)
        
        self.state.completed_stages.append(PipelineStage.MASKS)
        logger.info(f"Generated {len(self.state.masks)} masks")
        
        return self.state.masks
    
    def extract_features(self) -> List[MaskFeatures]:
        """
        Stage 2: Extract features from masks.
        
        Returns:
            List of MaskFeatures objects
        """
        logger.info("Stage 2: Extracting features...")
        
        if not self.state.masks:
            raise ValueError("No masks available. Run generate_masks() first.")
        
        green_centers = self._load_green_centers()
        
        if self._feature_extractor is None:
            self._feature_extractor = FeatureExtractor(
                green_centers=green_centers,
            )
        
        # Use multi-image extraction if multiple images available
        images = self._load_images()
        if len(images) > 1:
            logger.info(f"Using multi-image feature extraction from {len(images)} images")
            self.state.features = self._feature_extractor.extract_all_multi_image(
                self.state.masks, images
            )
        else:
            image = images[0]
            self.state.features = self._feature_extractor.extract_all(
                self.state.masks, image
            )
        
        # Save if configured
        if self.config.export_intermediates:
            features_path = self.output_dir / "metadata" / "mask_features.json"
            self._feature_extractor.save_features(self.state.features, features_path)
        
        self.state.completed_stages.append(PipelineStage.FEATURES)
        logger.info(f"Extracted features for {len(self.state.features)} masks")
        
        return self.state.features
    
    def classify_masks(self) -> List[Classification]:
        """
        Stage 3: Classify masks into feature types.
        
        Returns:
            List of Classification objects
        """
        logger.info("Stage 3: Classifying masks...")
        
        if not self.state.features:
            raise ValueError("No features available. Run extract_features() first.")
        
        if self._classifier is None:
            self._classifier = MaskClassifier(
                min_area=self.config.sam.min_mask_region_area,
            )
        
        self.state.classifications = self._classifier.classify_all(self.state.features)
        
        # Save if configured
        if self.config.export_intermediates:
            classifications_path = self.output_dir / "metadata" / "classifications.json"
            self._classifier.save_classifications(
                self.state.classifications, classifications_path
            )
        
        self.state.completed_stages.append(PipelineStage.CLASSIFY)
        
        return self.state.classifications
    
    def gate_masks(self) -> tuple:
        """
        Stage 4: Apply confidence gating.
        
        Returns:
            Tuple of (accepted, review, discarded) lists
        """
        logger.info("Stage 4: Applying confidence gating...")
        
        if not self.state.classifications:
            raise ValueError("No classifications available. Run classify_masks() first.")
        
        if self._gate is None:
            self._gate = ConfidenceGate(
                high_threshold=self.config.thresholds.high,
                low_threshold=self.config.thresholds.low,
            )
        
        self.state.accepted, self.state.review, self.state.discarded = \
            self._gate.gate_all(self.state.classifications)
        
        # Save if configured
        if self.config.export_intermediates:
            reviews_dir = self.output_dir / "reviews"
            self._gate.save_gating_results(
                self.state.accepted,
                self.state.review,
                self.state.discarded,
                reviews_dir,
            )
        
        self.state.completed_stages.append(PipelineStage.GATE)
        
        return self.state.accepted, self.state.review, self.state.discarded
    
    def generate_polygons(self) -> List[PolygonFeature]:
        """
        Stage 5: Generate polygons from accepted masks.
        
        Returns:
            List of PolygonFeature objects
        """
        logger.info("Stage 5: Generating polygons...")
        
        if not self.state.accepted:
            raise ValueError("No accepted masks. Run gate_masks() first.")
        
        if self._polygon_generator is None:
            self._polygon_generator = PolygonGenerator(
                simplify_tolerance=self.config.polygon.simplify_tolerance,
                min_area=self.config.polygon.min_area,
                buffer_distance=self.config.polygon.buffer_distance,
            )
        
        self.state.polygons = self._polygon_generator.generate_all(
            self.state.masks,
            self.state.accepted,
        )
        
        # Save if configured
        if self.config.export_intermediates:
            polygons_dir = self.output_dir / "polygons"
            self._polygon_generator.save_polygons(self.state.polygons, polygons_dir)
        
        self.state.completed_stages.append(PipelineStage.POLYGONS)
        
        return self.state.polygons
    
    def assign_holes(self) -> Dict[int, List[HoleAssignment]]:
        """
        Stage 6: Assign polygons to holes.
        
        Returns:
            Dictionary mapping hole numbers to assignments
        """
        logger.info("Stage 6: Assigning polygons to holes...")
        
        if not self.state.polygons:
            raise ValueError("No polygons available. Run generate_polygons() first.")
        
        green_centers = self._load_green_centers()
        
        if self._hole_assigner is None:
            self._hole_assigner = HoleAssigner(green_centers=green_centers)
        
        self.state.assignments_by_hole = self._hole_assigner.assign_all(
            self.state.polygons
        )
        
        # Save if configured
        if self.config.export_intermediates:
            assignments_path = self.output_dir / "metadata" / "hole_assignments.json"
            self._hole_assigner.save_assignments(
                self.state.assignments_by_hole, assignments_path
            )
        
        self.state.completed_stages.append(PipelineStage.HOLES)
        
        return self.state.assignments_by_hole
    
    def generate_svg(self) -> str:
        """
        Stage 7: Generate SVG with per-hole layers.
        
        Returns:
            SVG content as string
        """
        logger.info("Stage 7: Generating SVG...")
        
        if not self.state.assignments_by_hole:
            raise ValueError("No hole assignments. Run assign_holes() first.")
        
        # Determine SVG dimensions from image
        image = self._load_image()
        height, width = image.shape[:2]
        
        if self._svg_generator is None:
            self._svg_generator = SVGGenerator(
                width=width,
                height=height,
                colors=self.config.svg.colors,
                stroke_width=self.config.svg.stroke_width,
            )
        
        self.state.svg_content = self._svg_generator.generate(
            self.state.assignments_by_hole
        )
        
        self.state.completed_stages.append(PipelineStage.SVG)
        
        return self.state.svg_content
    
    def cleanup_svg(self) -> str:
        """
        Stage 8: Clean and optimize SVG geometry.
        
        Returns:
            Updated SVG content
        """
        logger.info("Stage 8: Cleaning SVG geometry...")
        
        if not self.state.assignments_by_hole:
            raise ValueError("No hole assignments. Run assign_holes() first.")
        
        if self._svg_cleaner is None:
            self._svg_cleaner = SVGCleaner(
                simplify_tolerance=self.config.polygon.simplify_tolerance,
            )
        
        # Clean geometry
        cleaned_assignments = self._svg_cleaner.clean(self.state.assignments_by_hole)
        self.state.assignments_by_hole = cleaned_assignments
        
        # Regenerate SVG with cleaned geometry
        self.state.svg_content = self._svg_generator.generate(cleaned_assignments)
        
        # Save SVG
        svg_path = self.output_dir / "course.svg"
        with open(svg_path, "w") as f:
            f.write(self.state.svg_content)
        
        logger.info(f"Saved SVG to {svg_path}")
        
        self.state.completed_stages.append(PipelineStage.CLEANUP)
        
        return self.state.svg_content
    
    def export_png(self) -> Path:
        """
        Stage 9: Export SVG to PNG overlay.
        
        Returns:
            Path to exported PNG
        """
        logger.info("Stage 9: Exporting PNG...")
        
        if self.state.svg_content is None:
            raise ValueError("No SVG content. Run generate_svg() first.")
        
        # Determine dimensions from image
        image = self._load_image()
        height, width = image.shape[:2]
        
        if self._png_exporter is None:
            self._png_exporter = PNGExporter(
                width=width,
                height=height,
            )
        
        # Save SVG first if not already saved
        svg_path = self.output_dir / "course.svg"
        if not svg_path.exists():
            with open(svg_path, "w") as f:
                f.write(self.state.svg_content)
        
        # Export PNG
        exports_dir = self.output_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        png_path = exports_dir / "overlay.png"
        
        self._png_exporter.export(svg_path, png_path)
        
        self.state.completed_stages.append(PipelineStage.EXPORT)
        
        return png_path
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    def run(self) -> Path:
        """
        Run the complete pipeline.
        
        Returns:
            Path to the final PNG overlay
        """
        logger.info("Running complete Phase 2A pipeline...")
        
        self.generate_masks()
        self.extract_features()
        self.classify_masks()
        self.gate_masks()
        self.generate_polygons()
        self.assign_holes()
        self.generate_svg()
        self.cleanup_svg()
        png_path = self.export_png()
        
        logger.info("Pipeline complete!")
        self._print_summary()
        
        return png_path
    
    def _print_summary(self) -> None:
        """Print pipeline execution summary."""
        print("\n" + "=" * 60)
        print("Phase 2A Pipeline Summary")
        print("=" * 60)
        print(f"Masks generated:    {len(self.state.masks)}")
        print(f"Features extracted: {len(self.state.features)}")
        print(f"Classifications:    {len(self.state.classifications)}")
        print(f"  - Accepted:       {len(self.state.accepted)}")
        print(f"  - Review:         {len(self.state.review)}")
        print(f"  - Discarded:      {len(self.state.discarded)}")
        print(f"Polygons:           {len(self.state.polygons)}")
        print(f"Holes with features: {len(self.state.assignments_by_hole)}")
        print(f"Output directory:   {self.output_dir}")
        print("=" * 60 + "\n")
    
    def validate(self) -> bool:
        """
        Validate pipeline completion (svg_complete gate).
        
        Returns:
            True if validation passes
        """
        svg_path = self.output_dir / "course.svg"
        png_path = self.output_dir / "exports" / "overlay.png"
        
        checks = {
            "SVG exists": svg_path.exists(),
            "PNG exists": png_path.exists(),
            "Has hole assignments": len(self.state.assignments_by_hole) > 0,
            "Has polygons": len(self.state.polygons) > 0,
        }
        
        # Check for required feature types
        feature_classes = set()
        for assignments in self.state.assignments_by_hole.values():
            for a in assignments:
                feature_classes.add(a.polygon.feature_class)
        
        checks["Has water"] = "water" in feature_classes
        checks["Has bunkers"] = "bunker" in feature_classes
        checks["Has greens"] = "green" in feature_classes
        
        # Print validation results
        all_passed = True
        print("\nValidation (svg_complete):")
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def load_masks(self, masks_dir: Path) -> List[MaskData]:
        """Load masks from a previous run."""
        self.state.masks = MaskGenerator.load_masks(masks_dir)
        return self.state.masks
    
    def load_features(self, features_path: Path) -> List[MaskFeatures]:
        """Load features from a previous run."""
        self.state.features = FeatureExtractor.load_features(features_path)
        return self.state.features
    
    def load_classifications(self, classifications_path: Path) -> List[Classification]:
        """Load classifications from a previous run."""
        self.state.classifications = MaskClassifier.load_classifications(
            classifications_path
        )
        return self.state.classifications
    
    def load_polygons(self, polygons_dir: Path) -> List[PolygonFeature]:
        """Load polygons from a previous run."""
        self.state.polygons = PolygonGenerator.load_polygons(polygons_dir)
        return self.state.polygons
    
    def reset(self) -> None:
        """Reset pipeline state."""
        self.state = PipelineState()
        logger.info("Pipeline state reset")
