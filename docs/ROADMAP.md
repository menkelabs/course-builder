# Course Builder Roadmap (4 Phases)

Four phases, ordered by priority. **Phases 1 & 2** get you a course; **Phase 3** makes it look better; **Phase 4** gets to a solid course-builder level.

---

## Phase 1: Splining from sat image and lidar

**Goal:** Terrain and feature splines (fairways, greens, bunkers, water, etc.) from satellite imagery and lidar.

**Current work (mapped here):**
- **phase1_1**: SegFormer-B3 trained on Danish Golf Courses → semantic segmentation → masks → polygons → SVG.
- **phase1a**: Interactive tracing (SegFormer pre-segment + SAM refinement), hole assignment, SVG export.

**Deliverables:**
- Semantic segmentation over ortho imagery (SegFormer).
- Vector splines / polygons (per-hole, per-feature) and SVG suitable for terrain + overlay.
- Lidar integrated where available (e.g. elevation, refinement).

**Success:** Reliable splining from sat (+ lidar) → editable vector output.

---

## Phase 2: Tree / foliage planting

**Goal:** Tree and foliage placement from a combination of satellite imagery, course location, and lidar.

**Deliverables:**
- Detection of tree canopy / vegetation from sat (and lidar where applicable).
- Placement rules or maps (e.g. density, species proxies) using course location.
- Export of tree/foliage layout for the course (e.g. for Unity/Blender).

**Success:** Plausible tree and foliage cover; **Phases 1 + 2** together yield a **playable course**.

---

## Phase 3: Texture colors from example course pictures

**Goal:** Derive texture and color palettes from reference course photos to improve appearance.

**Deliverables:**
- Use example course images (e.g. fairway, rough, green) to extract color/texture cues.
- Map those to surface types (fairway, rough, bunker, etc.) and apply in-engine.

**Success:** **Better-looking** course via data-driven texture/color from real examples.

---

## Phase 4: Bunker shaping from an example bunker pic

**Goal:** Shape bunkers using a reference bunker image (and optionally lidar / sat).

**Deliverables:**
- Use an example bunker photo to guide form, edges, and appearance.
- Combine with Phase 1 bunker outlines and terrain to produce shaped bunker geometry.

**Success:** **Decent course-builder level** — bunkers that match a desired style.

---

## Priority summary

| Phase | Focus | Outcome |
|-------|--------|---------|
| **1** | Splining (sat + lidar) | Vector terrain + features (SVG, etc.) |
| **2** | Tree/foliage planting | Playable course (1 + 2) |
| **3** | Texture colors from examples | Better-looking course |
| **4** | Bunker shaping from example | Solid course-builder quality |

Active implementation is **Phase 1** (phase1_1 + phase1a). Phases 2–4 are planned; scope may shift as we learn.

---

## Archived

- Old QGIS/terrain Phase 1, Grounding DINO (`archive/GROUNDING-DINO.md`), broader MCP roadmap → `archive/` (see `archive/ROADMAP.md`, `archive/README.md`).
