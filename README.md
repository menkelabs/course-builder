# Golf Course Builder

An automated pipeline for creating GSPro golf courses from satellite imagery and LIDAR data - the "None to Done" workflow.

## Overview

This project automates the complete workflow of building golf courses for GSPro, from raw terrain data to a finished playable asset bundle. The pipeline consists of multiple phases, each handled by specialized tools and components.

> See [plan.md](plan.md) for the full automation plan with detailed MCP tool specifications.

## Project Components

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **Phase 1** | QGIS/GDAL Terrain Preparation - DEM processing, heightmap generation | [phase1/README.md](phase1/README.md) |
| **Phase 2A** | Automated Satellite Tracing - SAM-based feature extraction to SVG | [phase2a/README.md](phase2a/README.md) |
| **Course Builder** | Spring Boot Agent Orchestration - Matryoshka tool pattern for workflow | [course-builder/README.md](course-builder/README.md) |

## The "None to Done" Workflow

The complete workflow transforms raw data into a playable GSPro course:

```
LIDAR → Unity (Terrain) → Phase2a (SAM SVG) → Unity (PNG) → Blender (Mesh) → Unity (Final)
```

### 6 Phases

1. **Terrain Creation** (Phase 1) - Generate heightmaps from LIDAR/DEM data, set up Unity terrain
2. **Course Tracing** (Phase 2A) - SAM-based automated satellite tracing to create SVG geometry
3. **Terrain Refinement** - Apply overlay, adjust contours, export OBJ
4. **SVG Conversion** - Process SVG for Blender import (GSProSVGConvert.exe)
5. **Blender Processing** - Mesh import, terrain projection, peripherals, FBX export
6. **Unity Assembly** - Import FBX, materials, vegetation, asset bundle build

## Quick Start

### Phase 1: Terrain Preparation

```bash
cd phase1
pip install -e .
phase1 run --course-name MyCourse -o workspace/
```

### Phase 2A: Satellite Tracing

```bash
cd phase2a
pip install -e .
phase2a run satellite.png --checkpoint checkpoints/sam_vit_h_4b8939.pth -o output/
```

### Course Builder Agent

```bash
cd course-builder
./mvnw spring-boot:run
```

## Project Structure

```
.
├── phase1/              # QGIS/GDAL terrain preparation (Python)
├── phase2a/             # SAM-based satellite tracing (Python)
├── course-builder/      # Agent orchestration (Spring Boot)
├── docs/                # Additional documentation
│   ├── TESTING.md
│   └── TEST_WALKTHROUGH.md
├── plan.md              # Full automation plan with MCP tool specs
└── phase2a.md           # Phase 2A design specification
```

## Requirements

### Phase 1
- Python 3.9+
- QGIS with PyQGIS bindings
- GDAL

### Phase 2A
- Python 3.10+
- SAM model checkpoint
- CUDA (recommended) or CPU

### Course Builder
- Java 17+
- Maven

## Documentation

- [Automation Plan](plan.md) - Complete workflow definition with MCP tool specifications
- [Phase 2A Specification](phase2a.md) - Detailed design for satellite tracing pipeline
- [Testing Guide](docs/TESTING.md) - How to run tests
- [Test Walkthrough](docs/TEST_WALKTHROUGH.md) - Step-by-step test execution guide

## References

- [Course Builder Documentation](https://docs.google.com/document/d/1InsfFuOrAH4l2S6RnTy17_O8FPXwt_EA_jKLvW4Ky80)
- [None to Done Video Series](https://docs.google.com/document/d/1bwNRByfPQNbUOWfKymXvdoWq9QP9-1R0U1GaJf5z9fU)
- [Course Builder Discord](https://discord.gg/4ZhJzwx)
- [Zeros and Ones GCD Tutorials](https://zerosandonesgcd.com/)
