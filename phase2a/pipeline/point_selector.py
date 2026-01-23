"""
Point-based Interactive Selection Module

Allows users to click on the image to mark feature locations.
The tool then uses SAM to generate masks around those points.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

from .masks import MaskGenerator, MaskData, merge_masks
from .interactive import InteractiveSelector, HoleSelection, FeatureType

logger = logging.getLogger(__name__)


class PointBasedSelector:
    """
    Point-based selector that generates masks from user clicks.
    
    Workflow:
    1. User clicks on image at a location (e.g., green, fairway, bunker, tee)
    2. Tool uses SAM to generate mask around that point
    3. Mask is assigned to the selected feature type for the current hole
    """
    
    def __init__(
        self,
        image: np.ndarray,
        mask_generator: MaskGenerator,
    ):
        """
        Initialize point-based selector.
        
        Args:
            image: Source image (H, W, 3) in RGB
            mask_generator: MaskGenerator instance for generating masks from points
        """
        self.image = image
        self.mask_generator = mask_generator
        self.selections: Dict[int, HoleSelection] = {}
        self.generated_masks: Dict[str, MaskData] = {}  # Track generated masks
    
    def click_to_mask(
        self,
        x: int,
        y: int,
        hole: int,
        feature_type: FeatureType,
    ) -> Optional[MaskData]:
        """
        Generate a mask from a click point and assign it to a feature type.
        
        Args:
            x: X coordinate of click
            y: Y coordinate of click
            hole: Hole number (1-18)
            feature_type: Type of feature (green, fairway, bunker, tee)
            
        Returns:
            Generated MaskData or None if generation failed
        """
        logger.info(f"Generating mask from point ({x}, {y}) for hole {hole}, {feature_type.value}")
        
        # Generate mask from point using SAM
        mask_data = self.mask_generator.generate_from_point(
            self.image,
            point=(x, y),
            label=1,  # Foreground point
        )
        
        if mask_data is None:
            logger.warning(f"Failed to generate mask from point ({x}, {y})")
            return None
        
        # Create unique ID for this mask
        mask_id = f"{feature_type.value}_{hole}_{len(self.generated_masks):04d}"
        mask_data.id = mask_id
        
        # Store generated mask
        self.generated_masks[mask_id] = mask_data
        
        # Add to selections
        if hole not in self.selections:
            self.selections[hole] = HoleSelection(hole=hole)
        
        selection = self.selections[hole]
        
        # Add to appropriate feature list
        if feature_type == FeatureType.GREEN:
            selection.greens.append(mask_id)
        elif feature_type == FeatureType.TEE:
            selection.tees.append(mask_id)
        elif feature_type == FeatureType.FAIRWAY:
            selection.fairways.append(mask_id)
        elif feature_type == FeatureType.BUNKER:
            selection.bunkers.append(mask_id)
        elif feature_type == FeatureType.WATER:
            selection.water.append(mask_id)
        elif feature_type == FeatureType.ROUGH:
            selection.rough.append(mask_id)
        
        # Remove duplicates
        selection.greens = list(set(selection.greens))
        selection.tees = list(set(selection.tees))
        selection.fairways = list(set(selection.fairways))
        selection.bunkers = list(set(selection.bunkers))
        selection.water = list(set(selection.water))
        selection.rough = list(set(selection.rough))
        
        logger.info(f"Generated mask {mask_id} with area {mask_data.area}")
        return mask_data
    
    def draw_to_mask(
        self,
        outline_points: List[tuple],
        hole: int,
        feature_type: FeatureType,
    ) -> Optional[MaskData]:
        """
        Generate a mask from a drawn outline and assign it to a feature type.
        
        This is the preferred method for accurate mask generation.
        User draws an outline around the feature, and SAM uses it as a hint.
        
        Args:
            outline_points: List of (x, y) coordinates from the drawn outline
            hole: Hole number (1-18)
            feature_type: Type of feature (green, fairway, bunker, tee)
            
        Returns:
            Generated MaskData or None if generation failed
        """
        if len(outline_points) < 3:
            logger.warning("Need at least 3 points to form an outline")
            return None
        
        # Calculate center for logging
        xs = [p[0] for p in outline_points]
        ys = [p[1] for p in outline_points]
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
        logger.info(f"Generating mask from outline ({len(outline_points)} points) "
                   f"for hole {hole}, {feature_type.value}")
        
        # Generate mask from outline using SAM
        mask_data = self.mask_generator.generate_from_outline(
            self.image,
            outline_points=outline_points,
        )
        
        if mask_data is None:
            logger.warning(f"Failed to generate mask from outline")
            return None
        
        # Create unique ID for this mask
        mask_id = f"{feature_type.value}_{hole}_{len(self.generated_masks):04d}"
        mask_data.id = mask_id
        
        # Store generated mask
        self.generated_masks[mask_id] = mask_data
        
        # Add to selections
        if hole not in self.selections:
            self.selections[hole] = HoleSelection(hole=hole)
        
        selection = self.selections[hole]
        
        # Add to appropriate feature list
        if feature_type == FeatureType.GREEN:
            selection.greens.append(mask_id)
        elif feature_type == FeatureType.TEE:
            selection.tees.append(mask_id)
        elif feature_type == FeatureType.FAIRWAY:
            selection.fairways.append(mask_id)
        elif feature_type == FeatureType.BUNKER:
            selection.bunkers.append(mask_id)
        elif feature_type == FeatureType.WATER:
            selection.water.append(mask_id)
        elif feature_type == FeatureType.ROUGH:
            selection.rough.append(mask_id)
        
        # Remove duplicates
        selection.greens = list(set(selection.greens))
        selection.tees = list(set(selection.tees))
        selection.fairways = list(set(selection.fairways))
        selection.bunkers = list(set(selection.bunkers))
        selection.water = list(set(selection.water))
        selection.rough = list(set(selection.rough))
        
        logger.info(f"Generated mask {mask_id} with area {mask_data.area}")
        return mask_data
    
    def fill_polygon_to_mask(
        self,
        outline_points: List[tuple],
        hole: int,
        feature_type: FeatureType,
    ) -> Optional[MaskData]:
        """
        Generate a completely filled mask from a drawn polygon (no SAM processing).
        
        This is useful when SAM's color-based refinement misses parts of an area.
        The user can draw a polygon that will be completely filled.
        
        Args:
            outline_points: List of (x, y) coordinates from the drawn polygon
            hole: Hole number (1-18)
            feature_type: Type of feature (green, fairway, bunker, tee)
            
        Returns:
            Generated MaskData or None if generation failed
        """
        if len(outline_points) < 3:
            logger.warning("Need at least 3 points to form a polygon")
            print(f"[FILL] Need at least 3 points, got {len(outline_points)}")
            return None
        
        # Calculate center and bounds for logging
        xs = [p[0] for p in outline_points]
        ys = [p[1] for p in outline_points]
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
        # Debug info
        print(f"[FILL] Drawing polygon with {len(outline_points)} points")
        print(f"[FILL] Bounds: x=[{min(xs):.0f}, {max(xs):.0f}], y=[{min(ys):.0f}, {max(ys):.0f}]")
        print(f"[FILL] Center: ({center_x}, {center_y})")
        
        logger.info(f"Generating filled polygon ({len(outline_points)} points) "
                   f"for hole {hole}, {feature_type.value}")
        
        # Generate filled polygon mask (no SAM processing)
        mask_data = self.mask_generator.generate_filled_polygon(
            self.image,
            outline_points=outline_points,
            smooth_edges=True,
        )
        
        if mask_data is None:
            logger.warning(f"Failed to generate filled polygon mask")
            print(f"[FILL] Failed to generate mask - check console for details")
            return None
        
        print(f"[FILL] Generated mask with area {mask_data.area} pixels")
        
        # Create unique ID for this mask
        mask_id = f"{feature_type.value}_{hole}_fill_{len(self.generated_masks):04d}"
        mask_data.id = mask_id
        
        # Store generated mask
        self.generated_masks[mask_id] = mask_data
        
        # Add to selections
        if hole not in self.selections:
            self.selections[hole] = HoleSelection(hole=hole)
        
        selection = self.selections[hole]
        
        # Add to appropriate feature list
        if feature_type == FeatureType.GREEN:
            selection.greens.append(mask_id)
        elif feature_type == FeatureType.TEE:
            selection.tees.append(mask_id)
        elif feature_type == FeatureType.FAIRWAY:
            selection.fairways.append(mask_id)
        elif feature_type == FeatureType.BUNKER:
            selection.bunkers.append(mask_id)
        elif feature_type == FeatureType.WATER:
            selection.water.append(mask_id)
        elif feature_type == FeatureType.ROUGH:
            selection.rough.append(mask_id)
        
        logger.info(f"Generated filled polygon mask {mask_id} with area {mask_data.area}")
        return mask_data

    def grow_from_polygon(
        self,
        outline_points: List[tuple],
        hole: int,
        feature_type: FeatureType,
        color_sensitivity: float = 0.6,
        growth_limit: int = 50,
    ) -> Optional[MaskData]:
        """
        Generate a mask by growing outward from a drawn polygon based on color.
        
        The polygon should be drawn INSIDE the feature - the algorithm grows
        outward until hitting a color boundary or the growth limit.
        
        Args:
            outline_points: List of (x, y) coordinates forming the seed polygon
            hole: Hole number (1-18)
            feature_type: Type of feature (green, fairway, bunker, tee)
            color_sensitivity: 0.0 = strict, 1.0 = loose (default 0.6)
            growth_limit: Maximum pixels to grow from polygon (default 50)
            
        Returns:
            Generated MaskData or None if generation failed
        """
        if len(outline_points) < 3:
            logger.warning("Need at least 3 points to form a polygon")
            print(f"[GROW] Need at least 3 points, got {len(outline_points)}")
            return None
        
        # Calculate center for logging
        xs = [p[0] for p in outline_points]
        ys = [p[1] for p in outline_points]
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
        print(f"[GROW] Processing polygon with {len(outline_points)} points")
        print(f"[GROW] Bounds: x=[{min(xs):.0f}, {max(xs):.0f}], y=[{min(ys):.0f}, {max(ys):.0f}]")
        print(f"[GROW] Settings: sensitivity={color_sensitivity:.2f}, limit={growth_limit}px")
        
        logger.info(f"Growing mask from polygon ({len(outline_points)} points) "
                   f"for hole {hole}, {feature_type.value}")
        
        # Generate grown mask
        mask_data = self.mask_generator.generate_from_polygon_grow(
            self.image,
            outline_points=outline_points,
            color_sensitivity=color_sensitivity,
            growth_limit=growth_limit,
            smooth_edges=True,
        )
        
        if mask_data is None:
            logger.warning("Failed to grow mask from polygon")
            print("[GROW] Failed to generate mask")
            return None
        
        print(f"[GROW] Generated mask with area {mask_data.area} pixels")
        
        # Create unique ID for this mask
        mask_id = f"{feature_type.value}_{hole}_grow_{len(self.generated_masks):04d}"
        mask_data.id = mask_id
        
        # Store generated mask
        self.generated_masks[mask_id] = mask_data
        
        # Add to selections
        if hole not in self.selections:
            self.selections[hole] = HoleSelection(hole=hole)
        
        selection = self.selections[hole]
        self._add_to_selection(selection, feature_type, mask_id)
        
        logger.info(f"Generated grown mask {mask_id} with area {mask_data.area}")
        return mask_data

    def fill_and_merge(
        self,
        outline_points: List[tuple],
        existing_mask_id: Optional[str],
        hole: int,
        feature_type: FeatureType,
    ) -> Optional[MaskData]:
        """
        Generate a filled polygon and automatically merge it with an existing mask.
        
        This is the preferred workflow for completing partial SAM masks:
        1. SAM generates a partial mask
        2. User draws fill to cover missing area
        3. Fill automatically merges with the SAM mask
        
        Args:
            outline_points: List of (x, y) coordinates from the drawn polygon
            existing_mask_id: ID of the mask to merge with (or None for standalone)
            hole: Hole number (1-18)
            feature_type: Type of feature (green, fairway, bunker, tee)
            
        Returns:
            Merged MaskData or None if generation failed
        """
        if len(outline_points) < 3:
            logger.warning("Need at least 3 points to form a polygon")
            print(f"[FILL+MERGE] Need at least 3 points, got {len(outline_points)}")
            return None
        
        # Generate the filled polygon mask first
        fill_mask = self.mask_generator.generate_filled_polygon(
            self.image,
            outline_points=outline_points,
            smooth_edges=True,
        )
        
        if fill_mask is None:
            logger.warning("Failed to generate fill polygon")
            print("[FILL+MERGE] Failed to generate fill polygon")
            return None
        
        # If no existing mask to merge with, just use the fill as standalone
        if existing_mask_id is None or existing_mask_id not in self.generated_masks:
            print(f"[FILL+MERGE] No existing mask to merge - creating standalone fill")
            # Create unique ID
            mask_id = f"{feature_type.value}_{hole}_fill_{len(self.generated_masks):04d}"
            fill_mask.id = mask_id
            self.generated_masks[mask_id] = fill_mask
            
            # Add to selections
            if hole not in self.selections:
                self.selections[hole] = HoleSelection(hole=hole)
            self._add_to_selection(self.selections[hole], feature_type, mask_id)
            
            print(f"[FILL+MERGE] Created standalone: {mask_id} ({fill_mask.area} pixels)")
            return fill_mask
        
        # Merge with existing mask
        existing_mask = self.generated_masks[existing_mask_id]
        print(f"[FILL+MERGE] Merging fill ({fill_mask.area} px) with {existing_mask_id} ({existing_mask.area} px)")
        
        # Use merge_masks to combine them
        merged = merge_masks([existing_mask, fill_mask], smooth_edges=True)
        
        if merged is None:
            logger.warning("Failed to merge masks")
            print("[FILL+MERGE] Merge failed")
            return None
        
        # Create new ID for merged mask
        merged_id = f"{feature_type.value}_{hole}_merged_{len(self.generated_masks):04d}"
        merged.id = merged_id
        
        # Store merged mask
        self.generated_masks[merged_id] = merged
        
        # Update selections: remove old mask ID, add merged
        if hole in self.selections:
            selection = self.selections[hole]
            self._remove_from_selection(selection, feature_type, existing_mask_id)
            self._add_to_selection(selection, feature_type, merged_id)
        
        print(f"[FILL+MERGE] Created merged mask: {merged_id} ({merged.area} pixels)")
        logger.info(f"Fill merged into {merged_id}: {existing_mask.area} + {fill_mask.area} -> {merged.area}")
        return merged
    
    def _add_to_selection(self, selection: HoleSelection, feature_type: FeatureType, mask_id: str):
        """Helper to add a mask ID to the appropriate feature list."""
        if feature_type == FeatureType.GREEN:
            if mask_id not in selection.greens:
                selection.greens.append(mask_id)
        elif feature_type == FeatureType.TEE:
            if mask_id not in selection.tees:
                selection.tees.append(mask_id)
        elif feature_type == FeatureType.FAIRWAY:
            if mask_id not in selection.fairways:
                selection.fairways.append(mask_id)
        elif feature_type == FeatureType.BUNKER:
            if mask_id not in selection.bunkers:
                selection.bunkers.append(mask_id)
        elif feature_type == FeatureType.WATER:
            if mask_id not in selection.water:
                selection.water.append(mask_id)
        elif feature_type == FeatureType.ROUGH:
            if mask_id not in selection.rough:
                selection.rough.append(mask_id)
    
    def _remove_from_selection(self, selection: HoleSelection, feature_type: FeatureType, mask_id: str):
        """Helper to remove a mask ID from the appropriate feature list."""
        if feature_type == FeatureType.GREEN and mask_id in selection.greens:
            selection.greens.remove(mask_id)
        elif feature_type == FeatureType.TEE and mask_id in selection.tees:
            selection.tees.remove(mask_id)
        elif feature_type == FeatureType.FAIRWAY and mask_id in selection.fairways:
            selection.fairways.remove(mask_id)
        elif feature_type == FeatureType.BUNKER and mask_id in selection.bunkers:
            selection.bunkers.remove(mask_id)
        elif feature_type == FeatureType.WATER and mask_id in selection.water:
            selection.water.remove(mask_id)
        elif feature_type == FeatureType.ROUGH and mask_id in selection.rough:
            selection.rough.remove(mask_id)

    def merge_selected_masks(
        self,
        mask_ids: List[str],
        hole: int,
        feature_type: FeatureType,
    ) -> Optional[MaskData]:
        """
        Merge multiple masks into one with smooth edges.
        
        Use this to combine a SAM-generated mask with a manually-drawn
        filled polygon to create a complete, smooth mask.
        
        Args:
            mask_ids: List of mask IDs to merge
            hole: Hole number for the merged mask
            feature_type: Feature type for the merged mask
            
        Returns:
            Merged MaskData or None if merging failed
        """
        if len(mask_ids) < 2:
            logger.warning("Need at least 2 masks to merge")
            return None
        
        # Get the mask data objects
        masks_to_merge = []
        for mask_id in mask_ids:
            if mask_id in self.generated_masks:
                masks_to_merge.append(self.generated_masks[mask_id])
            else:
                logger.warning(f"Mask {mask_id} not found, skipping")
        
        if len(masks_to_merge) < 2:
            logger.warning("Need at least 2 valid masks to merge")
            return None
        
        logger.info(f"Merging {len(masks_to_merge)} masks for hole {hole}, {feature_type.value}")
        
        # Create merged mask
        merged_mask = merge_masks(masks_to_merge, smooth_edges=True)
        
        if merged_mask is None:
            logger.warning("Failed to merge masks")
            return None
        
        # Create unique ID for merged mask
        merged_id = f"{feature_type.value}_{hole}_merged_{len(self.generated_masks):04d}"
        merged_mask.id = merged_id
        
        # Store the merged mask
        self.generated_masks[merged_id] = merged_mask
        
        # Update selections: remove old mask IDs, add merged mask ID
        if hole in self.selections:
            selection = self.selections[hole]
            
            # Get the appropriate list based on feature type
            if feature_type == FeatureType.GREEN:
                feature_list = selection.greens
            elif feature_type == FeatureType.TEE:
                feature_list = selection.tees
            elif feature_type == FeatureType.FAIRWAY:
                feature_list = selection.fairways
            elif feature_type == FeatureType.BUNKER:
                feature_list = selection.bunkers
            elif feature_type == FeatureType.WATER:
                feature_list = selection.water
            elif feature_type == FeatureType.ROUGH:
                feature_list = selection.rough
            else:
                feature_list = []
            
            # Remove the old mask IDs that were merged
            for old_id in mask_ids:
                if old_id in feature_list:
                    feature_list.remove(old_id)
            
            # Add the merged mask ID
            feature_list.append(merged_id)
        
        # Optionally: remove old masks from generated_masks
        # (keeping them for now in case user wants to undo)
        
        logger.info(f"Created merged mask {merged_id} with area {merged_mask.area}")
        return merged_mask

    def get_all_masks(self) -> List[MaskData]:
        """Get all generated masks."""
        return list(self.generated_masks.values())
    
    def get_selection_for_hole(self, hole: int) -> Optional[HoleSelection]:
        """Get current selection for a hole."""
        return self.selections.get(hole)
    
    def get_all_selections(self) -> Dict[int, HoleSelection]:
        """Get all hole selections."""
        return self.selections.copy()
    
    def extract_green_centers(self) -> List[Dict]:
        """
        Extract green center coordinates from selected green masks.
        
        Returns:
            List of green center dictionaries [{hole, x, y}, ...]
        """
        green_centers = []
        
        for hole, selection in self.selections.items():
            if not selection.greens:
                continue
            
            # Calculate centroid of all green masks for this hole
            all_x_coords = []
            all_y_coords = []
            
            for mask_id in selection.greens:
                if mask_id not in self.generated_masks:
                    continue
                
                mask_data = self.generated_masks[mask_id]
                mask = mask_data.mask
                
                # Get coordinates of all pixels in the mask
                y_coords, x_coords = np.where(mask)
                if len(y_coords) > 0:
                    all_x_coords.extend(x_coords.tolist())
                    all_y_coords.extend(y_coords.tolist())
            
            if len(all_x_coords) > 0:
                # Calculate centroid
                center_x = float(np.mean(all_x_coords))
                center_y = float(np.mean(all_y_coords))
                
                green_centers.append({
                    "hole": hole,
                    "x": center_x,
                    "y": center_y,
                })
        
        return green_centers
