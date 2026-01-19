# Test Walkthrough: Processing a Complete Hole

This document provides a step-by-step walkthrough for processing a complete golf course hole from satellite imagery to final SVG export with proper Inkscape annotations.

## Prerequisites

- Python 3.10+ with virtual environment activated
- SAM checkpoint file (`sam_vit_h_4b8939.pth`) in `checkpoints/` directory
- Satellite image of golf course (e.g., `phase2a/resources/Pictatinny_B.jpg`)
- Optional: Green centers JSON file for hole assignment

## Overview

The complete pipeline processes a golf course through these stages:

1. **Mask Generation** - Generate candidate masks using SAM
2. **Feature Extraction** - Extract color, texture, shape, and context features
3. **Classification** - Classify masks as water, bunker, green, fairway, rough, or ignore
4. **Confidence Gating** - Route masks based on classification confidence
5. **Polygon Generation** - Convert masks to vector polygons
6. **Hole Assignment** - Assign polygons to holes (1-18, 98, 99)
7. **SVG Generation** - Create SVG with per-hole layers and OPCD classes
8. **SVG Cleanup** - Union, simplify, and fix topology
9. **PNG Export** - Render final overlay image

## Step-by-Step Walkthrough

### Step 1: Prepare Input Files

Create a green centers file (optional but recommended for accurate hole assignment):

```bash
# Create green_centers.json
cat > green_centers.json << EOF
[
  {"hole": 1, "x": 2000, "y": 1500},
  {"hole": 2, "x": 3500, "y": 1800},
  {"hole": 3, "x": 5000, "y": 2200}
]
EOF
```

### Step 2: Run Complete Pipeline

Run the full automated pipeline:

```bash
cd phase2a
phase2a run ../phase2a/resources/Pictatinny_B.jpg \
  --checkpoint ../checkpoints/sam_vit_h_4b8939.pth \
  --green-centers green_centers.json \
  --device cuda \
  --high-threshold 0.85 \
  --low-threshold 0.5 \
  -o test_output \
  -v
```

**Expected Output:**
```
Phase 2A Pipeline
Input:  phase2a/resources/Pictatinny_B.jpg
Output: test_output

Stage 1: Generating masks...
Stage 2: Extracting features...
Stage 3: Classifying masks...
Stage 4: Gating masks...
Stage 5: Generating polygons...
Stage 6: Assigning holes...
Stage 7: Generating SVG...
Stage 8: Cleaning SVG geometry...
Stage 9: Exporting PNG...

✓ Pipeline completed successfully!
  SVG: test_output/course.svg
  PNG: test_output/exports/overlay.png
```

### Step 3: Verify Output Structure

Check the output directory structure:

```bash
tree test_output/
```

**Expected Structure:**
```
test_output/
├── satellite_normalized.png
├── masks/
│   ├── mask_0000.png
│   ├── mask_0000.json
│   └── ...
├── polygons/
│   └── polygons.json
├── reviews/
│   └── review_masks.json
├── metadata/
│   ├── mask_features.json
│   ├── classifications.json
│   └── hole_assignments.json
├── course.svg
└── exports/
    └── overlay.png
```

### Step 4: Inspect SVG Structure

Open `test_output/course.svg` in a text editor to verify Inkscape annotations:

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="8192"
     height="8192"
     viewBox="0 0 8192 8192">
  <defs>
    <style type="text/css">
      .water { fill: #0066cc; stroke: #000; stroke-width: 1px; }
      .bunker { fill: #f5deb3; stroke: #000; stroke-width: 1px; }
      .green { fill: #228b22; stroke: #000; stroke-width: 1px; }
      .fairway { fill: #90ee90; stroke: #000; stroke-width: 1px; }
      .rough { fill: #556b2f; stroke: #000; stroke-width: 1px; }
      .cart_path { fill: #808080; stroke: #000; stroke-width: 1px; }
      .ignore { fill: #cccccc; stroke: #000; stroke-width: 1px; }
    </style>
  </defs>
  <g id="Hole01" inkscape:groupmode="layer" inkscape:label="Hole01">
    <path class="green" d="M 2000 1500 L 2100 1500 ... Z" data-id="green_01_001" data-confidence="0.950"/>
    <path class="fairway" d="M 1800 1400 L 2200 1400 ... Z" data-id="fairway_01_001" data-confidence="0.920"/>
    <path class="bunker" d="M 1950 1450 L 2050 1450 ... Z" data-id="bunker_01_001" data-confidence="0.880"/>
  </g>
  <g id="Hole02" inkscape:groupmode="layer" inkscape:label="Hole02">
    ...
  </g>
  ...
</svg>
```

**Key Inkscape Annotations:**
- `xmlns:inkscape` - Inkscape namespace declaration
- `inkscape:groupmode="layer"` - Marks groups as Inkscape layers
- `inkscape:label` - Human-readable layer name (e.g., "Hole01")
- Layer IDs follow pattern: `Hole01` through `Hole18`, `Hole98_CartPaths`, `Hole99_OuterMesh`

**OPCD Color Classes:**
- `.water` - #0066cc (blue)
- `.bunker` - #f5deb3 (sandy brown)
- `.green` - #228b22 (forest green)
- `.fairway` - #90ee90 (light green)
- `.rough` - #556b2f (dark olive)
- `.cart_path` - #808080 (gray)
- `.ignore` - #cccccc (light gray)

### Step 5: Verify in Inkscape

Open the SVG in Inkscape to verify layer structure:

```bash
inkscape test_output/course.svg
```

**In Inkscape:**
1. Open Layers panel (Layer → Layers... or Shift+Ctrl+L)
2. Verify layers are present:
   - Hole01, Hole02, ..., Hole18
   - Hole98_CartPaths (if cart paths detected)
   - Hole99_OuterMesh (if outer boundary detected)
3. Check that each layer contains paths with correct OPCD classes
4. Verify colors match OPCD palette
5. Test layer visibility toggles

### Step 6: Inspect Hole Assignments

Check the hole assignments metadata:

```bash
cat test_output/metadata/hole_assignments.json | python3 -m json.tool | head -50
```

**Expected Format:**
```json
[
  {
    "polygon_id": "green_01_001",
    "feature_class": "green",
    "hole": 1,
    "distance_to_green": 0.0
  },
  {
    "polygon_id": "fairway_01_001",
    "feature_class": "fairway",
    "hole": 1,
    "distance_to_green": 150.5
  },
  ...
]
```

### Step 7: Verify Polygon Data

Check polygon features:

```bash
cat test_output/polygons/polygons.json | python3 -m json.tool | head -50
```

**Expected Format:**
```json
[
  {
    "id": "green_01_001",
    "feature_class": "green",
    "confidence": 0.950,
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[2000, 1500], [2100, 1500], ...]]
    },
    "properties": {
      "area": 1250.5,
      "perimeter": 180.2
    }
  },
  ...
]
```

## Interactive Selection Workflow (Alternative)

For manual hole-by-hole selection:

### Step 1: Generate Masks

```bash
phase2a generate-masks phase2a/resources/Pictatinny_B.jpg \
  --checkpoint checkpoints/sam_vit_h_4b8939.pth \
  --device cuda \
  -o test_masks
```

### Step 2: Interactive Selection

```bash
phase2a select phase2a/resources/Pictatinny_B.jpg \
  --checkpoint checkpoints/sam_vit_h_4b8939.pth \
  --device cuda \
  -o test_interactive
```

**Workflow:**
1. GUI opens showing all candidate masks
2. For each hole (1-18):
   - Click on green masks
   - Press Enter/Space to confirm
   - Click on tee masks
   - Press Enter/Space to confirm
   - Click on fairway masks
   - Press Enter/Space to confirm
   - Click on bunker masks
   - Press Enter/Space to confirm
3. Selections saved to `test_interactive/metadata/interactive_selections.json`

### Step 3: Convert Selections to SVG

The interactive selections can be converted to SVG using the pipeline:

```python
from phase2a.client import Phase2AClient
from phase2a.config import Phase2AConfig
from phase2a.pipeline.interactive import InteractiveSelector
from pathlib import Path

# Load selections
selections_path = Path("test_interactive/metadata/interactive_selections.json")
selector = InteractiveSelector.load_selections(selections_path)

# Convert to hole assignments and generate SVG
# (This would require additional code to convert selections to polygons)
```

## Verification Checklist

- [ ] SVG file created with correct dimensions
- [ ] Inkscape namespace declared (`xmlns:inkscape`)
- [ ] Layers use `inkscape:groupmode="layer"`
- [ ] Layer labels follow pattern: `Hole01` through `Hole18`
- [ ] OPCD color classes defined in `<style>` block
- [ ] Paths have correct `class` attributes (water, bunker, green, fairway, rough)
- [ ] Paths include `data-id` and `data-confidence` attributes
- [ ] SVG opens correctly in Inkscape
- [ ] Layers panel shows all hole layers
- [ ] Colors match OPCD palette
- [ ] PNG export generated successfully

## Troubleshooting

### Issue: SVG doesn't open in Inkscape

**Solution:** Verify Inkscape namespace is declared:
```xml
xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
```

### Issue: Layers not showing in Inkscape

**Solution:** Ensure groups have:
- `inkscape:groupmode="layer"`
- `inkscape:label` attribute

### Issue: Colors not matching OPCD palette

**Solution:** Check CSS classes in `<defs><style>` block match OPCD colors.

### Issue: No polygons for a hole

**Possible causes:**
- No masks generated for that region
- All masks classified as "ignore"
- Confidence thresholds too high
- Green center coordinates incorrect

**Solution:** 
- Lower confidence thresholds
- Check green centers file
- Review classification results in `metadata/classifications.json`

## Example: Processing Hole 1

Here's a focused example for processing just Hole 1:

```bash
# 1. Generate masks
phase2a generate-masks image.jpg --checkpoint sam.pth -o masks/

# 2. Run pipeline with focus on Hole 1
# (In practice, you'd filter assignments or use interactive selection)

# 3. Inspect Hole 1 layer in SVG
grep -A 20 'id="Hole01"' test_output/course.svg

# 4. Verify Hole 1 assignments
cat test_output/metadata/hole_assignments.json | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  print(json.dumps([d for d in data if d['hole']==1], indent=2))"
```

## Next Steps

After successful SVG generation:

1. **Open in Inkscape** - Verify layer structure and colors
2. **Manual Refinement** - Edit polygons as needed in Inkscape
3. **Export for Unity/Blender** - Use Inkscape export or pipeline PNG export
4. **Validate for GSPro** - Ensure OPCD classes and structure match requirements

## References

- [Phase 2A Design Specification](../phase2a.md)
- [README](../README.md)
- [Visual Workflow Guide](images/workflow_step1_masks.jpg)
