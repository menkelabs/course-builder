"""
Tests for confidence gating module.
"""

import json
from pathlib import Path

import pytest

from phase1a.pipeline.gating import ConfidenceGate, GateDecision, GatedMask
from phase1a.pipeline.classify import Classification, FeatureClass


class TestGateDecision:
    """Tests for GateDecision enum."""
    
    def test_all_decisions_exist(self):
        assert GateDecision.ACCEPT == "accept"
        assert GateDecision.REVIEW == "review"
        assert GateDecision.DISCARD == "discard"


class TestGatedMask:
    """Tests for GatedMask dataclass."""
    
    def test_to_dict(self):
        classification = Classification(
            mask_id="mask_001",
            feature_class=FeatureClass.GREEN,
            confidence=0.9,
            scores={},
        )
        gated = GatedMask(
            classification=classification,
            decision=GateDecision.ACCEPT,
        )
        
        data = gated.to_dict()
        
        assert data["mask_id"] == "mask_001"
        assert data["class"] == "green"
        assert data["confidence"] == 0.9
        assert data["decision"] == "accept"


class TestConfidenceGate:
    """Tests for ConfidenceGate class."""
    
    def test_init_default(self):
        gate = ConfidenceGate()
        assert gate.high_threshold == 0.85
        assert gate.low_threshold == 0.5
    
    def test_init_custom(self):
        gate = ConfidenceGate(high_threshold=0.9, low_threshold=0.3)
        assert gate.high_threshold == 0.9
        assert gate.low_threshold == 0.3
    
    def test_gate_accept_high_confidence(self):
        """High confidence should be accepted."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classification = Classification(
            mask_id="high",
            feature_class=FeatureClass.GREEN,
            confidence=0.9,
            scores={},
        )
        
        result = gate.gate(classification)
        
        assert result.decision == GateDecision.ACCEPT
    
    def test_gate_review_medium_confidence(self):
        """Medium confidence should go to review."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classification = Classification(
            mask_id="medium",
            feature_class=FeatureClass.GREEN,
            confidence=0.6,
            scores={},
        )
        
        result = gate.gate(classification)
        
        assert result.decision == GateDecision.REVIEW
    
    def test_gate_discard_low_confidence(self):
        """Low confidence should be discarded."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classification = Classification(
            mask_id="low",
            feature_class=FeatureClass.GREEN,
            confidence=0.2,
            scores={},
        )
        
        result = gate.gate(classification)
        
        assert result.decision == GateDecision.DISCARD
    
    def test_gate_ignore_always_discarded(self):
        """IGNORE class should always be discarded."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classification = Classification(
            mask_id="ignore",
            feature_class=FeatureClass.IGNORE,
            confidence=1.0,  # Even with high confidence
            scores={},
        )
        
        result = gate.gate(classification)
        
        assert result.decision == GateDecision.DISCARD
    
    def test_gate_boundary_high(self):
        """Exactly at high threshold should be accepted."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classification = Classification(
            mask_id="boundary",
            feature_class=FeatureClass.GREEN,
            confidence=0.8,
            scores={},
        )
        
        result = gate.gate(classification)
        
        assert result.decision == GateDecision.ACCEPT
    
    def test_gate_boundary_low(self):
        """Exactly at low threshold should go to review."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classification = Classification(
            mask_id="boundary",
            feature_class=FeatureClass.GREEN,
            confidence=0.4,
            scores={},
        )
        
        result = gate.gate(classification)
        
        assert result.decision == GateDecision.REVIEW
    
    def test_gate_all(self):
        """Test batch gating."""
        gate = ConfidenceGate(high_threshold=0.8, low_threshold=0.4)
        classifications = [
            Classification("high", FeatureClass.GREEN, 0.9, {}),
            Classification("medium", FeatureClass.BUNKER, 0.6, {}),
            Classification("low", FeatureClass.WATER, 0.2, {}),
            Classification("ignore", FeatureClass.IGNORE, 1.0, {}),
        ]
        
        accepted, review, discarded = gate.gate_all(classifications)
        
        assert len(accepted) == 1
        assert len(review) == 1
        assert len(discarded) == 2
        
        assert accepted[0].classification.mask_id == "high"
        assert review[0].classification.mask_id == "medium"
    
    def test_save_gating_results(self, temp_dir):
        """Test saving gating results."""
        gate = ConfidenceGate()
        
        accepted = [
            GatedMask(
                Classification("a1", FeatureClass.GREEN, 0.9, {}),
                GateDecision.ACCEPT,
            ),
        ]
        review = [
            GatedMask(
                Classification("r1", FeatureClass.BUNKER, 0.6, {}),
                GateDecision.REVIEW,
            ),
        ]
        discarded = [
            GatedMask(
                Classification("d1", FeatureClass.IGNORE, 0.1, {}),
                GateDecision.DISCARD,
            ),
        ]
        
        gate.save_gating_results(accepted, review, discarded, temp_dir)
        
        assert (temp_dir / "accepted.json").exists()
        assert (temp_dir / "review_queue.json").exists()
        assert (temp_dir / "discarded.json").exists()
        
        # Verify content
        with open(temp_dir / "accepted.json") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["mask_id"] == "a1"
    
    def test_load_accepted(self, temp_dir):
        """Test loading accepted masks."""
        # Create test file
        data = [
            {"mask_id": "a1", "class": "green", "confidence": 0.9, "decision": "accept"},
            {"mask_id": "a2", "class": "bunker", "confidence": 0.85, "decision": "accept"},
        ]
        with open(temp_dir / "accepted.json", "w") as f:
            json.dump(data, f)
        
        loaded = ConfidenceGate.load_accepted(temp_dir)
        
        assert len(loaded) == 2
        assert loaded[0].classification.mask_id == "a1"
        assert loaded[0].decision == GateDecision.ACCEPT


class TestGatingEdgeCases:
    """Edge case tests for confidence gating."""
    
    def test_empty_classifications(self):
        """Empty input should return empty outputs."""
        gate = ConfidenceGate()
        accepted, review, discarded = gate.gate_all([])
        
        assert len(accepted) == 0
        assert len(review) == 0
        assert len(discarded) == 0
    
    def test_all_accepted(self):
        """All high confidence should all be accepted."""
        gate = ConfidenceGate(high_threshold=0.5, low_threshold=0.2)
        classifications = [
            Classification(f"m{i}", FeatureClass.GREEN, 0.9, {})
            for i in range(5)
        ]
        
        accepted, review, discarded = gate.gate_all(classifications)
        
        assert len(accepted) == 5
        assert len(review) == 0
        assert len(discarded) == 0
    
    def test_all_discarded(self):
        """All low confidence should all be discarded."""
        gate = ConfidenceGate(high_threshold=0.9, low_threshold=0.8)
        classifications = [
            Classification(f"m{i}", FeatureClass.GREEN, 0.5, {})
            for i in range(5)
        ]
        
        accepted, review, discarded = gate.gate_all(classifications)
        
        assert len(accepted) == 0
        assert len(review) == 0
        assert len(discarded) == 5
