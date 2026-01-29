# Golf Course Builder

Build golf course geometry and assets from satellite imagery and lidar. Active work is **Phase 1** of the [4-phase roadmap](docs/ROADMAP.md): **splining from sat + lidar** (SegFormer → masks → polygons → SVG).

## Scope

- **phase1_1**: Train SegFormer-B3 on Danish Golf Courses, run inference, masks → polygons → SVG.
- **phase1a**: Interactive tracing (SegFormer pre-segment + SAM refinement), hole assignment, SVG export.
- **python-agent**: Exposes Phase 1A as remote actions (REST API) for the [Embabel](https://github.com/embabel/embabel-agent) agent platform (GOAP planning, tool execution).
- **course-builder**: Spring Boot GOAP + Matryoshka tools for the full workflow. Phase1a operations live under `phase1a_mcp`. When `coursebuilder.python-agent.url` is set, those tools delegate to the **python-agent** instead of mocks (single Phase 1A implementation, Java orchestration).

Legacy QGIS/terrain work and the older roadmap are **archived** in `archive/`. See [docs/ROADMAP.md](docs/ROADMAP.md) for Phases 1–4.

## Quick Start

### 1. Train SegFormer (phase1_1)

```bash
.venv/bin/python -m phase1_1 train \
  --archive phase1a/resources/archive.zip \
  -o phase1_1_output \
  --epochs 50 --batch-size 8 --device cuda
```

Requires `phase1a/resources/archive.zip` (Danish Golf Courses). See [phase1_1/README.md](phase1_1/README.md).

### 2. Run phase1a (interactive selection)

```bash
.venv/bin/pip install -e "phase1a[gui]"
.venv/bin/phase1a select satellite.png --checkpoint checkpoints/sam_vit_h_4b8939.pth -o phase1a_output
```

Draw outlines → SAM masks → assign to holes → SVG. SegFormer integration (pre-segment → phase1a) is in progress; see [phase1_1/WORKFLOW_INTEGRATION.md](phase1_1/WORKFLOW_INTEGRATION.md).

### 3. Python agent (optional)

```bash
.venv/bin/pip install -e "python-agent[phase1a]"
.venv/bin/python -m agent serve --port 8000
```

Exposes Phase 1A actions as REST endpoints for the [Embabel](https://github.com/embabel/embabel-agent) agent platform. See [python-agent/README.md](python-agent/README.md).

## Project Layout

```
├── phase1_1/          # SegFormer training & inference
├── phase1a/            # Interactive tracing, SVG export
├── python-agent/       # Phase 1A remote actions (Embabel REST API)
├── archive/            # Phase 1, old ROADMAP, workspace (inactive)
├── docs/               # ROADMAP, testing, etc.
├── course-builder/     # Spring Boot GOAP + Matryoshka; Phase1a → python-agent when configured
└── .venv/              # Shared Python venv (project root)
```

## Requirements

- Python 3.10+
- PyTorch + CUDA (recommended) for SegFormer and SAM
- SAM checkpoint for phase1a (`sam_vit_h_4b8939.pth`)

## Documentation

- [4-phase roadmap](docs/ROADMAP.md) (Phase 1 = splining; 2 = trees; 3 = textures; 4 = bunker shaping)
- [Phase 1.1 training & workflow](phase1_1/README.md)
- [Phase 1.1 ↔ phase1a integration](phase1_1/WORKFLOW_INTEGRATION.md)
- [Phase 1A CLI & GUI](phase1a/README.md)
- [Python agent](python-agent/README.md) (Phase 1A remote actions, Embabel integration)
- [Testing](docs/TESTING.md)
