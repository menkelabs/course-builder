# Using Trained SegFormer in Phase2A Workflow

## Current Phase2A Workflow

**Matplotlib app**: User draws an outline (circle/polygon) → SAM generates a mask → user assigns to feature type (green, fairway, bunker, etc.)

## SegFormer Model Capabilities

**SegFormer-B3** does **semantic segmentation**: classifies every pixel into one of 6 classes:
- `background`, `fairway`, `green`, `tee`, `bunker`, `water`

**Key difference**: SegFormer is **not interactive** like SAM. It processes the whole image at once and gives you a class prediction for every pixel.

## Integration Options

### Option 1: Pre-segment + User Refinement (Recommended)

**Workflow:**
1. **Pre-process**: Run SegFormer on the full satellite image → get semantic mask
2. **Extract regions**: Convert semantic mask to per-class connected components (regions)
3. **Matplotlib app**: Show these regions as candidate masks
4. **User interaction**: User can:
   - Click to select/assign regions to holes
   - Draw new outlines (SAM mode) to refine/add missing features
   - Use existing SAM workflow for edge cases

**Implementation:**
```python
# In phase1a/pipeline/masks.py or new phase1_1 integration
from phase1_1.pipeline.inference import SemanticSegmenter
from phase1_1.pipeline.masks import semantic_mask_to_regions, resolve_overlaps
from phase1_1.config import InferenceConfig

# Load trained model
config = InferenceConfig(
    mode="self_hosted",
    model_path="phase1_1_output/segformer_b3_danish_best.pt",
    device="cuda"
)
segmenter = SemanticSegmenter(config)

# Run on full image
semantic_mask, class_map = segmenter.predict(satellite_image)

# Extract regions per class
regions_by_class = semantic_mask_to_regions(semantic_mask, class_map)
regions_by_class = resolve_overlaps(regions_by_class, priority_order, h, w)

# Convert to MaskData format for phase1a
candidate_masks = []
for class_name, regions in regions_by_class.items():
    for region in regions:
        mask_data = MaskData(
            id=f"segformer_{class_name}_{len(candidate_masks)}",
            mask=region.mask,
            area=int(region.mask.sum()),
            bbox=region.bbox,
            predicted_iou=0.9,  # High confidence from trained model
            stability_score=0.9,
        )
        candidate_masks.append(mask_data)

# Feed to InteractiveSelector
selector = InteractiveSelector(candidate_masks, satellite_image)
```

**Pros:**
- Fast: One inference pass on full image
- High accuracy: Trained on Danish golf courses
- User can still refine with SAM if needed
- Reduces manual work: Most features pre-detected

**Cons:**
- Requires full image inference (slower than SAM on small regions)
- May miss features not in training data

---

### Option 2: SegFormer + SAM 2 Edge Refinement (Blueprint)

**Workflow:**
1. User draws outline in matplotlib (as now)
2. **SegFormer**: Run on that region → get class prediction (e.g., "this is a green")
3. **SAM 2**: Use outline as prompt → get crisp edge mask
4. **Combine**: Use SegFormer class + SAM 2 geometry

**Implementation:**
```python
# When user draws outline
outline_points = [...]  # from matplotlib

# 1. Get bounding box of outline
bbox = get_bbox(outline_points)
crop = image[bbox.y:bbox.y+bbox.h, bbox.x:bbox.x+bbox.w]

# 2. SegFormer: what class is this?
semantic_mask, _ = segmenter.predict(crop)
predicted_class = semantic_mask[bbox.center].argmax()  # most common class in region

# 3. SAM 2: crisp edge
from phase1_1.pipeline.sam2_refine import SAM2Refiner
refiner = SAM2Refiner(checkpoint="sam2_checkpoint.pth")
refined_mask = refiner.refine(crop, outline_points, prompt="box")

# 4. Combine: use refined_mask geometry, predicted_class label
final_mask = refined_mask
feature_class = class_map[predicted_class]
```

**Pros:**
- Best of both: SegFormer accuracy + SAM 2 crisp edges
- Interactive: Works with existing draw workflow
- Precise: User controls what to segment

**Cons:**
- Requires SAM 2 (not yet implemented)
- Slower: Two model inferences per region

---

### Option 3: Hybrid - SegFormer Pre-fill + SAM Refinement

**Workflow:**
1. **Pre-segment**: Run SegFormer on full image → show candidate masks
2. **User selects**: Click to assign to holes (most features)
3. **SAM for gaps**: Draw outlines for missing/incorrect features (SAM mode)

**Implementation:** Same as Option 1, but keep existing SAM workflow as fallback.

---

## Answer: Can it segment a hole you circle?

**Yes, but not directly like SAM.**

**SegFormer approach:**
1. Run SegFormer on the **whole image** first (one-time cost)
2. When you circle a region, **extract** the SegFormer prediction for that region
3. The circled region will have class predictions (e.g., "mostly green" or "green + fairway")
4. You can then:
   - Use the SegFormer mask directly (if accurate)
   - Refine with SAM 2 edge refinement (if implemented)
   - Fall back to SAM outline mode (current workflow)

**Example:**
```python
# User circles region at (x1, y1) to (x2, y2)
region_mask = np.zeros_like(semantic_mask)
region_mask[y1:y2, x1:x2] = 1

# Extract SegFormer predictions in that region
region_classes = semantic_mask[region_mask > 0]
most_common = np.bincount(region_classes).argmax()  # e.g., "green"
class_name = class_map[most_common]

# Get connected component for that class in the region
class_mask = (semantic_mask == most_common) & (region_mask > 0)
# This gives you the green pixels within the circled area
```

---

## Recommended Integration Path

**Phase 1 (Quick win):**
- Add `phase1_1` inference to phase1a CLI
- Pre-segment full image with SegFormer
- Convert to MaskData format
- Feed to existing InteractiveSelector
- User can still use SAM mode for refinement

**Phase 2 (Better UX):**
- Implement SAM 2 edge refinement
- Use SegFormer for class + SAM 2 for geometry
- Integrate into matplotlib draw workflow

**Phase 3 (Full automation):**
- Auto-assign regions to holes (spatial clustering)
- User only reviews/refines
- Export to SVG

---

## Code Location

- **Inference**: `phase1_1/pipeline/inference.py` - `SemanticSegmenter` class
- **Mask extraction**: `phase1_1/pipeline/masks.py` - `semantic_mask_to_regions()`
- **Integration point**: `phase1a/pipeline/masks.py` or new `phase1a/pipeline/segformer_masks.py`
