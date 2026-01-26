# Python Agent for Course Builder

A Python-based agent that exposes Phase2A and other pipeline tools as remote actions following the [embabel-agent-remote](https://github.com/embabel/embabel-agent/tree/main/embabel-agent-remote) REST API pattern.

This enables Python tools to participate in the Embabel agent platform's GOAP (Goal-Oriented Action Planning) and execution.

## Features

- **Remote Actions**: Exposes Python tools as REST endpoints compatible with Embabel agent platform
- **GOAP Integration**: Actions have preconditions, postconditions, cost, and value for intelligent planning
- **Phase2A Support**: Full integration with Phase2A SAM-based satellite tracing pipeline
- **Phase1 Support**: Integration with Phase1 terrain preparation tools
- **Registration**: Automatic registration with Embabel server

## API Endpoints

The agent implements the embabel-agent-remote REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/actions` | GET | List all available actions |
| `/api/v1/types` | GET | List all domain types |
| `/api/v1/actions/execute` | POST | Execute an action |
| `/api/v1/actions/{name}` | GET | Get action metadata |
| `/health` | GET | Health check |

## Installation

```bash
cd python-agent
pip install -e .

# With Phase2A support
pip install -e ".[phase2a]"

# With development dependencies
pip install -e ".[dev]"
```

## Usage

### Start the Server

```bash
# Basic server
python -m agent serve --port 8000

# With auto-reload for development
python -m agent serve --port 8000 --reload

# Register with Embabel server on startup
python -m agent serve --port 8000 --embabel-url http://localhost:8080
```

### Register with Embabel Server

```bash
python -m agent register \
    --embabel-url http://localhost:8080 \
    --agent-url http://localhost:8000 \
    --name python-agent
```

### List Available Actions

```bash
python -m agent list-actions

# As JSON
python -m agent list-actions --json
```

### Execute an Action Locally

```bash
# Execute phase2a_validate
python -m agent execute phase2a_validate --params output_dir=/output/phase2a

# With JSON parameters
python -m agent execute phase2a_run --json-params '{"satellite_image": "satellite.png", "checkpoint": "sam.pth"}'
```

## Available Actions

### Phase2A Actions

| Action | Description | Pre | Post |
|--------|-------------|-----|------|
| `phase2a_run` | Run complete Phase2A pipeline | satellite_image_exists | svg_complete |
| `phase2a_generate_masks` | Generate SAM masks | satellite_image_exists | masks_generated |
| `phase2a_classify` | Classify masks as features | masks_generated | masks_classified |
| `phase2a_generate_svg` | Generate SVG output | masks_classified, holes_assigned | svg_generated |
| `phase2a_export_png` | Export SVG to PNG | svg_generated | png_exported |
| `phase2a_validate` | Validate output (gate) | svg_generated | svg_complete |

### Phase1 Actions

| Action | Description | Pre | Post |
|--------|-------------|-----|------|
| `phase1_run` | Run complete Phase1 pipeline | course_name_defined | terrain_ready, satellite_image_exists |
| `phase1_geocode` | Geocode location | - | location_geocoded |
| `phase1_download_dem` | Download DEM data | location_geocoded | dem_downloaded |
| `phase1_generate_heightmap` | Generate heightmap | dem_downloaded | heightmap_generated |

## Domain Types

The agent defines several domain types for structured inputs/outputs:

- `Phase2AConfig` - Configuration for Phase2A pipeline
- `Phase2AResult` - Result from Phase2A execution
- `MaskGenerationResult` - Result from SAM mask generation
- `ClassificationResult` - Result from classification
- `SVGGenerationResult` - Result from SVG generation
- `ValidationResult` - Result from validation
- `GolfCourse` - Golf course being built
- `WorkflowState` - Current workflow state

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Embabel Agent Platform                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  GOAP Planner                                         │  │
│  │  Plans: phase2a_run → svg_convert → blender → unity   │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Remote Action Registry                               │  │
│  │  - Java actions (local)                               │  │
│  │  - Python actions (remote) ◄─────────────┐            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                              │
                                              │ HTTP REST
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Python Agent (this server)                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  FastAPI Server                                       │  │
│  │  - GET /api/v1/actions                                │  │
│  │  - GET /api/v1/types                                  │  │
│  │  - POST /api/v1/actions/execute                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Action Registry                                      │  │
│  │  - phase2a_run                                        │  │
│  │  - phase2a_generate_masks                             │  │
│  │  - phase1_run                                         │  │
│  │  - ...                                                │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Phase2A / Phase1 Pipeline                            │  │
│  │  (actual implementation)                              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Registration Flow

1. Python Agent starts and exposes REST endpoints
2. Agent calls Embabel server's `/api/v1/remote/register` endpoint
3. Embabel server fetches `/api/v1/actions` and `/api/v1/types` from Python Agent
4. Remote actions are deployed into the agent platform
5. GOAP planner can now include Python actions in plans
6. When a Python action is selected, Embabel calls `/api/v1/actions/execute`

## Development

### Running Tests

```bash
cd python-agent
pytest tests/ -v
```

### Code Style

```bash
# Format code
black agent tests

# Lint code
ruff check agent tests
```

## Integration with Course Builder

The Python Agent is part of the Course Builder pipeline:

```
LIDAR → Phase1 (Python) → Phase2A (Python) → Unity → Blender → Unity
         ↑                    ↑
         └────────────────────┴─── Python Agent serves these
```

To run the complete pipeline with the Java Course Builder:

1. Start the Python Agent:
   ```bash
   python -m agent serve --port 8000
   ```

2. Start the Course Builder:
   ```bash
   cd course-builder
   ./mvnw spring-boot:run
   ```

3. Register Python Agent with Course Builder:
   ```bash
   python -m agent register --embabel-url http://localhost:8080
   ```

Now the Course Builder can use Python actions in its GOAP planning!

## License

Apache License 2.0
