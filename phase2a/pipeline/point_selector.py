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
            return None
        
        # Calculate center for logging
        xs = [p[0] for p in outline_points]
        ys = [p[1] for p in outline_points]
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
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
            return None
        
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
