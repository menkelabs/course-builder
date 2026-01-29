# Phase 2A — Automated Satellite Tracing (Starting Work)

## Status
Active

This document defines the initial implementation for Phase 2A: automatic extraction
of golf course features from satellite imagery using SAM proposals and lightweight
mask classification.

This is a single, canonical specification intended for direct use in Cursor.

---

## Objective

Automatically generate a structured SVG representing a golf course with:

- Per-hole layers (1–18, plus 98 and 99)
- Per-feature vector geometry (water, bunker, green, fairway, rough)
- Deterministic outputs suitable for Unity, Blender, and GSPro

Pipeline:

Satellite Image
→ Feature Masks
→ Clean Polygons
→ Hole-Scoped SVG Layers
→ Overlay PNG

Gate: svg_complete

---

## Design Principle

Mask generation is modular and replaceable.
All downstream vectorization and SVG generation steps are deterministic and invariant.

---

## Scope

### In Scope
- Automatic feature extraction from satellite imagery
- SAM-based mask generation
- Mask feature extraction and classification
- Confidence gating
- Polygon generation and cleanup
- SVG generation
- PNG overlay export

### Out of Scope
- Manual Inkscape tracing
- Model training pipelines
- Blender or Unity processing
- Fully trained semantic segmentation

---

## Inputs

Required:
- satellite_normalized.png

Optional:
- green_centers.json

Example:

```json
[
  { "hole": 1, "x": 1234, "y": 567 },
  { "hole": 2, "x": 1320, "y": 610 }
]
```

---

## Pipeline

### 1. Mask Generation — sam_generate_masks

Generate candidate masks using SAM automatic mask generation.

Output:

```
masks/
  mask_<id>.png
  mask_<id>.json
```

---

### 2. Mask Feature Extraction — extract_mask_features

For each mask, compute:

Color:
- HSV mean and variance
- Lab mean and variance

Texture:
- Grayscale variance

Shape:
- Area
- Perimeter
- Compactness
- Elongation

Context:
- Proximity to other masks
- Overlap with water candidates
- Distance to green centers

Output:

```
metadata/mask_features.json
```

---

### 3. Mask Classification — classify_masks

Classify each mask into:

- water
- bunker
- green
- fairway
- rough
- ignore

Each classification includes a confidence score.

---

### 4. Confidence Gating — route_masks

Rules:

- Auto-accept: confidence >= HIGH_THRESHOLD
- Review queue: LOW_THRESHOLD <= confidence < HIGH_THRESHOLD
- Discard: confidence < LOW_THRESHOLD

Review does not block execution.

---

### 5. Polygon Generation — mask_to_polygons

For accepted masks:

- Extract contours
- Convert to polygons
- Simplify geometry
- Remove small artifacts
- Fix invalid topology

Output:

```
polygons/
  feature_<id>.geojson
```

---

### 6. Hole Assignment — assign_polygons_to_holes

Assign polygons to holes using:

- Nearest green center
- Spatial clustering fallback

Each polygon belongs to exactly one hole.

---

### 7. SVG Generation — svg_write_layers

Generate course.svg with:

- Hole01–Hole18 layers
- Hole98_CartPaths
- Hole99_OuterMesh

Classes:
- .green
- .fairway
- .bunker
- .water
- .rough

All geometry written directly as SVG paths.

---

### 8. SVG Cleanup — svg_cleanup

- Union overlapping shapes
- Fix self-intersections
- Simplify nodes
- Optional fringe generation

---

### 9. PNG Export — svg_export_png

Render SVG to PNG overlay.

```
exports/
  overlay.png
```

---

## Artifacts

```
phase1a/
  satellite_normalized.png
  masks/
  polygons/
  reviews/
  metadata/
  course.svg
  exports/
```

All outputs must be reproducible from inputs.

---

## Validation — svg_complete

Phase 1A is complete when:

- course.svg exists and loads
- Layers exist for holes 1–18, 98, 99
- Water, bunkers, and greens are present
- All polygons are valid
- Overlay PNG renders correctly
