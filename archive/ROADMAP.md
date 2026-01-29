# Course Builder AI Automation Roadmap

## Overview

This roadmap outlines the path from manual course tracing to fully automated AI-assisted course creation. The goal is to progressively reduce human effort while maintaining high-quality output.

## Current State (Phase 2A)

- Manual feature selection with SAM assistance
- User draws outlines, SAM creates precise masks
- Fill mode for completing partial masks
- Human assigns features to holes

## Roadmap

### Phase 1: Training Data Collection (Current)

**Goal:** Every manual session generates training data for future automation.

**Features:**
- Export labeled masks from interactive sessions
- Save image regions + classification labels
- Format compatible with model fine-tuning

**Output:**
```
training_data/
├── images/
│   ├── course_001_region_0001.png
│   ├── course_001_region_0002.png
│   └── ...
├── masks/
│   ├── course_001_region_0001_mask.png
│   └── ...
└── labels.json  # {region: "green"|"fairway"|"bunker"|...}
```

---

### Phase 2: Grounding DINO Integration

**Goal:** Automated feature detection with zero API costs.

**Architecture:**
```
┌─────────────────┐
│ Satellite Image │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ Grounding DINO (Local, Free)                    │
│ Prompts: "golf green", "fairway", "sand bunker" │
└────────┬────────────────────────────────────────┘
         │ Bounding boxes per feature
         ▼
┌─────────────────┐
│ SAM Segmentation│
└────────┬────────┘
         │ Precise masks
         ▼
┌─────────────────────────────────────┐
│ Contextual Validation               │
│ • Green at end of fairway?          │
│ • Bunkers near green?               │
│ • Sizes within normal range?        │
└────────┬────────────────────────────┘
         │
         ▼
    ┌─────────────┐
    │ Confidence  │
    │ Score       │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────────┐
│ Auto-   │ │ Human Review│
│ Accept  │ │ (Low Conf)  │
└────┬────┘ └──────┬──────┘
     │             │
     └──────┬──────┘
            ▼
      ┌──────────┐
      │ SVG Out  │
      └──────────┘
```

**Implementation:** See [GROUNDING-DINO.md](GROUNDING-DINO.md)

**Effort:** 1-2 days

---

### Phase 3: Model Fine-Tuning

**Goal:** Train a golf-specific model on collected data.

**When:** After collecting 100+ labeled courses

**Approach:**
- Fine-tune Grounding DINO or train YOLO on golf features
- Model learns golf-specific patterns (green shapes, fairway textures)
- Higher accuracy than zero-shot detection

**Expected Improvement:**
- Zero-shot Grounding DINO: ~70-80% accuracy
- Fine-tuned model: ~90-95% accuracy

---

### Phase 4: Bidirectional MCP Communication

**Goal:** AI agent can observe and control interactive sessions.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Embabel AI Agent                         │
└─────────────────────────────┬───────────────────────────────┘
                              │ MCP Protocol
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Phase2A       │    │ Blender       │    │ Unity         │
│ (matplotlib)  │    │ Addon         │    │ Plugin        │
└───────────────┘    └───────────────┘    └───────────────┘
```

#### Phase2A MCP Server

**Tools (Agent → Matplotlib):**
| Tool | Description |
|------|-------------|
| `draw_mask(points, hole, feature)` | Draw a mask from coordinates |
| `set_mode(mode)` | Switch SAM/FILL mode |
| `confirm_selection()` | Press Done |
| `undo_last()` | Undo last mask |
| `merge_masks(ids)` | Merge selected masks |
| `zoom_to(x, y, level)` | Zoom to location |

**Resources (Matplotlib → Agent):**
| Resource | Description |
|----------|-------------|
| `phase2a://current_view` | Screenshot of current state |
| `phase2a://selections` | Current selections JSON |
| `phase2a://events` | Stream of user actions |

#### Blender MCP Server

**Tools:**
| Tool | Description |
|------|-------------|
| `import_svg(path)` | Import course SVG |
| `extrude_region(layer, height)` | Extrude greens/bunkers |
| `apply_material(object, material)` | Apply textures |
| `sculpt_terrain(brush, points)` | Terrain modification |
| `render_preview()` | Render current view |
| `export_fbx(path)` | Export for game engines |

#### Unity MCP Server

**Tools:**
| Tool | Description |
|------|-------------|
| `place_hole(hole_num, position)` | Place hole in scene |
| `paint_texture(region, type)` | Paint terrain textures |
| `place_object(prefab, position)` | Place trees, flags, etc. |
| `get_camera_view()` | Screenshot from camera |
| `run_play_test()` | Test the course |
| `export_course(format)` | Export final course |

---

### Phase 5: End-to-End Automation

**Goal:** Satellite image → Playable course with minimal human input.

**Workflow:**
```
1. User provides: Satellite image + Course name
                        │
                        ▼
2. Grounding DINO + SAM: Auto-detect all features
                        │
                        ▼
3. Human review: Approve/correct low-confidence detections
                        │
                        ▼
4. SVG generation: Layered vector output
                        │
                        ▼
5. Blender (automated): Generate 3D terrain
                        │
                        ▼
6. Unity (automated): Assemble playable course
                        │
                        ▼
7. Output: GSPro-ready course package
```

**Human involvement:** ~15 minutes per course (review only)

---

## Technology Stack

| Component | Technology | Cost |
|-----------|------------|------|
| Object Detection | Grounding DINO | Free (local) |
| Segmentation | SAM | Free (local) |
| 3D Generation | Blender | Free |
| Game Assembly | Unity | Free (personal) |
| AI Orchestration | Embabel + MCP | TBD |

## Hardware Requirements

| Stage | Minimum | Recommended |
|-------|---------|-------------|
| Detection (DINO + SAM) | 8GB VRAM | 16GB VRAM |
| Blender rendering | 8GB RAM | 32GB RAM |
| Unity | 8GB RAM | 16GB RAM |

## Timeline Estimates

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Training Data Export | 4-6 hours | None |
| Grounding DINO Integration | 1-2 days | None |
| Model Fine-Tuning | 2-3 days | 100+ labeled courses |
| Phase2A MCP Server | 2-3 days | None |
| Blender MCP Server | 3-5 days | Blender addon experience |
| Unity MCP Server | 3-5 days | Unity plugin experience |
| End-to-End Pipeline | 1-2 weeks | All above |

## Success Metrics

| Metric | Current | Phase 2 | Phase 5 |
|--------|---------|---------|---------|
| Time per course | 2-4 hours | 30-60 min | 15 min |
| Human actions | ~500 clicks | ~50 clicks | ~10 clicks |
| Automation rate | 0% | 70% | 95% |
| Cost per course | $0 (time only) | $0 | $0 |
