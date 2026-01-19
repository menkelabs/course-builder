"""
Point-based Interactive Selection Module

Allows users to click on the image to mark feature locations.
The tool then uses SAM to generate masks around those points.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

from .masks import MaskGenerator, MaskData
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
