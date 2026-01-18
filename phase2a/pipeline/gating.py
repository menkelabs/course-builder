"""
Confidence Gating Module

Routes classified masks based on confidence thresholds.
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Tuple
import logging

from .classify import Classification, FeatureClass

logger = logging.getLogger(__name__)


class GateDecision(str, Enum):
    """Gating decisions for classified masks."""
    ACCEPT = "accept"
    REVIEW = "review"
    DISCARD = "discard"


@dataclass
class GatedMask:
    """A classification with its gating decision."""
    classification: Classification
    decision: GateDecision
    
    def to_dict(self) -> dict:
        """Export to dictionary."""
        return {
            "mask_id": self.classification.mask_id,
            "class": self.classification.feature_class.value,
            "confidence": self.classification.confidence,
            "decision": self.decision.value,
        }


class ConfidenceGate:
    """
    Route masks based on classification confidence.
    
    Rules:
    - Auto-accept: confidence >= high_threshold
    - Review queue: low_threshold <= confidence < high_threshold
    - Discard: confidence < low_threshold
    
    Review does not block pipeline execution.
    """
    
    def __init__(
        self,
        high_threshold: float = 0.85,
        low_threshold: float = 0.5,
    ):
        """
        Initialize the confidence gate.
        
        Args:
            high_threshold: Minimum confidence for auto-accept
            low_threshold: Minimum confidence to avoid discard
        """
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
    
    def gate(self, classification: Classification) -> GatedMask:
        """
        Apply gating to a single classification.
        
        Args:
            classification: Classification result
            
        Returns:
            GatedMask with decision
        """
        # Ignored masks are always discarded
        if classification.feature_class == FeatureClass.IGNORE:
            decision = GateDecision.DISCARD
        elif classification.confidence >= self.high_threshold:
            decision = GateDecision.ACCEPT
        elif classification.confidence >= self.low_threshold:
            decision = GateDecision.REVIEW
        else:
            decision = GateDecision.DISCARD
        
        return GatedMask(classification=classification, decision=decision)
    
    def gate_all(
        self,
        classifications: List[Classification],
    ) -> Tuple[List[GatedMask], List[GatedMask], List[GatedMask]]:
        """
        Apply gating to all classifications.
        
        Args:
            classifications: List of Classification results
            
        Returns:
            Tuple of (accepted, review, discarded) lists
        """
        accepted = []
        review = []
        discarded = []
        
        for classification in classifications:
            gated = self.gate(classification)
            
            if gated.decision == GateDecision.ACCEPT:
                accepted.append(gated)
            elif gated.decision == GateDecision.REVIEW:
                review.append(gated)
            else:
                discarded.append(gated)
        
        logger.info(
            f"Gating results: {len(accepted)} accepted, "
            f"{len(review)} review, {len(discarded)} discarded"
        )
        
        return accepted, review, discarded
    
    def save_gating_results(
        self,
        accepted: List[GatedMask],
        review: List[GatedMask],
        discarded: List[GatedMask],
        output_dir: Path,
    ) -> None:
        """
        Save gating results to files.
        
        Args:
            accepted: List of accepted masks
            review: List of masks for review
            discarded: List of discarded masks
            output_dir: Directory to save results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save accepted
        accepted_data = [g.to_dict() for g in accepted]
        with open(output_dir / "accepted.json", "w") as f:
            json.dump(accepted_data, f, indent=2)
        
        # Save review queue
        review_data = [g.to_dict() for g in review]
        with open(output_dir / "review_queue.json", "w") as f:
            json.dump(review_data, f, indent=2)
        
        # Save discarded
        discarded_data = [g.to_dict() for g in discarded]
        with open(output_dir / "discarded.json", "w") as f:
            json.dump(discarded_data, f, indent=2)
        
        logger.info(f"Saved gating results to {output_dir}")
    
    @staticmethod
    def load_accepted(output_dir: Path) -> List[GatedMask]:
        """Load accepted masks from saved results."""
        from .classify import Classification, FeatureClass
        
        with open(output_dir / "accepted.json") as f:
            data = json.load(f)
        
        accepted = []
        for item in data:
            classification = Classification(
                mask_id=item["mask_id"],
                feature_class=FeatureClass(item["class"]),
                confidence=item["confidence"],
                scores={},
            )
            gated = GatedMask(
                classification=classification,
                decision=GateDecision(item["decision"]),
            )
            accepted.append(gated)
        
        return accepted
