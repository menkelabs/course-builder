"""
Interactive Selection Module

Provides interactive hole-by-hole feature selection workflow.
Users click on masks to assign them to features for each hole.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
import logging

import numpy as np

from .masks import MaskData
from .classify import FeatureClass

logger = logging.getLogger(__name__)


class FeatureType(str, Enum):
    """Interactive feature types for selection."""
    GREEN = "green"
    TEE = "tee"
    FAIRWAY = "fairway"
    BUNKER = "bunker"
    WATER = "water"
    ROUGH = "rough"


@dataclass
class SelectedMask:
    """A mask selected for a specific feature type and hole."""
    mask_id: str
    hole: int
    feature_type: FeatureType
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    
    def to_dict(self) -> dict:
        """Export to dictionary."""
        return {
            "mask_id": self.mask_id,
            "hole": self.hole,
            "feature_type": self.feature_type.value,
            "bbox": list(self.bbox),
        }


@dataclass
class HoleSelection:
    """Selected features for a single hole."""
    hole: int
    greens: List[str] = field(default_factory=list)  # mask_ids
    tees: List[str] = field(default_factory=list)
    fairways: List[str] = field(default_factory=list)
    bunkers: List[str] = field(default_factory=list)
    water: List[str] = field(default_factory=list)
    rough: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Export to dictionary."""
        return {
            "hole": self.hole,
            "greens": self.greens,
            "tees": self.tees,
            "fairways": self.fairways,
            "bunkers": self.bunkers,
            "water": self.water,
            "rough": self.rough,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "HoleSelection":
        """Load from dictionary."""
        return cls(
            hole=data["hole"],
            greens=data.get("greens", []),
            tees=data.get("tees", []),
            fairways=data.get("fairways", []),
            bunkers=data.get("bunkers", []),
            water=data.get("water", []),
            rough=data.get("rough", []),
        )


class InteractiveSelector:
    """
    Interactive selector for hole-by-hole feature assignment.
    
    Workflow:
    1. Prepare: Generate all candidate masks
    2. For each hole (1-18):
       a. Prompt: "Click on the green for hole N"
       b. User clicks on mask(s)
       c. Prompt: "Click on the tee for hole N"
       d. User clicks on mask(s)
       e. Prompt: "Click on fairway items for hole N"
       f. User clicks on mask(s)
       g. Prompt: "Click on bunkers for hole N"
       h. User clicks on mask(s)
    3. Save selections
    """
    
    def __init__(
        self,
        masks: List[MaskData],
        image: np.ndarray,
    ):
        """
        Initialize the interactive selector.
        
        Args:
            masks: List of all candidate masks
            image: Source image for visualization
        """
        self.masks = {mask.id: mask for mask in masks}
        self.image = image
        self.selections: Dict[int, HoleSelection] = {}
        self._mask_id_to_index = {mask.id: i for i, mask in enumerate(masks)}
    
    def get_mask_at_point(self, x: int, y: int) -> Optional[str]:
        """
        Find mask ID at a given point.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Mask ID if found, None otherwise
        """
        for mask_id, mask_data in self.masks.items():
            mask = mask_data.mask
            if y < mask.shape[0] and x < mask.shape[1] and mask[y, x]:
                return mask_id
        return None
    
    def get_masks_in_region(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
    ) -> List[str]:
        """
        Find all mask IDs in a rectangular region.
        
        Args:
            x1, y1: Top-left corner
            x2, y2: Bottom-right corner
            
        Returns:
            List of mask IDs in the region
        """
        mask_ids = []
        for mask_id, mask_data in self.masks.items():
            mask = mask_data.mask
            # Check if mask overlaps with region
            y_coords, x_coords = np.where(mask)
            if len(y_coords) > 0:
                mask_min_x, mask_max_x = x_coords.min(), x_coords.max()
                mask_min_y, mask_max_y = y_coords.min(), y_coords.max()
                
                # Check overlap
                if not (mask_max_x < x1 or mask_min_x > x2 or
                       mask_max_y < y1 or mask_min_y > y2):
                    mask_ids.append(mask_id)
        
        return mask_ids
    
    def select_for_hole(
        self,
        hole: int,
        feature_type: FeatureType,
        mask_ids: List[str],
    ) -> None:
        """
        Select masks for a specific feature type on a hole.
        
        Args:
            hole: Hole number (1-18, 98, 99)
            feature_type: Type of feature
            mask_ids: List of mask IDs to select
        """
        if hole not in self.selections:
            self.selections[hole] = HoleSelection(hole=hole)
        
        selection = self.selections[hole]
        
        # Validate mask IDs
        valid_mask_ids = [mid for mid in mask_ids if mid in self.masks]
        
        if feature_type == FeatureType.GREEN:
            selection.greens.extend(valid_mask_ids)
        elif feature_type == FeatureType.TEE:
            selection.tees.extend(valid_mask_ids)
        elif feature_type == FeatureType.FAIRWAY:
            selection.fairways.extend(valid_mask_ids)
        elif feature_type == FeatureType.BUNKER:
            selection.bunkers.extend(valid_mask_ids)
        elif feature_type == FeatureType.WATER:
            selection.water.extend(valid_mask_ids)
        elif feature_type == FeatureType.ROUGH:
            selection.rough.extend(valid_mask_ids)
        
        # Remove duplicates
        selection.greens = list(set(selection.greens))
        selection.tees = list(set(selection.tees))
        selection.fairways = list(set(selection.fairways))
        selection.bunkers = list(set(selection.bunkers))
        selection.water = list(set(selection.water))
        selection.rough = list(set(selection.rough))
    
    def get_selection_for_hole(self, hole: int) -> Optional[HoleSelection]:
        """Get current selection for a hole."""
        return self.selections.get(hole)
    
    def get_all_selections(self) -> Dict[int, HoleSelection]:
        """Get all hole selections."""
        return self.selections.copy()
    
    def extract_green_centers(self) -> List[Dict]:
        """
        Extract green center coordinates from selected green masks.
        
        For each hole with green selections, calculates the centroid
        of all selected green masks to determine the green center.
        
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
                if mask_id not in self.masks:
                    continue
                
                mask_data = self.masks[mask_id]
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
    
    def save_selections(self, output_path: Path) -> None:
        """Save selections to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "selections": {
                str(hole): selection.to_dict()
                for hole, selection in self.selections.items()
            }
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved selections to {output_path}")
    
    @classmethod
    def load_selections(cls, selections_path: Path) -> Dict[int, HoleSelection]:
        """Load selections from JSON file."""
        with open(selections_path) as f:
            data = json.load(f)
        
        selections = {}
        for hole_str, hole_data in data.get("selections", {}).items():
            hole = int(hole_str)
            selections[hole] = HoleSelection.from_dict(hole_data)
        
        return selections
    
    def get_mask_summary(self) -> Dict[str, dict]:
        """
        Get summary of all masks with their locations.
        
        Returns:
            Dictionary mapping mask_id to metadata
        """
        summary = {}
        for mask_id, mask_data in self.masks.items():
            y_coords, x_coords = np.where(mask_data.mask)
            if len(y_coords) > 0:
                centroid_x = int(x_coords.mean())
                centroid_y = int(y_coords.mean())
                
                summary[mask_id] = {
                    "area": mask_data.area,
                    "bbox": mask_data.bbox,
                    "centroid": (centroid_x, centroid_y),
                    "predicted_iou": mask_data.predicted_iou,
                    "stability_score": mask_data.stability_score,
                }
        
        return summary
