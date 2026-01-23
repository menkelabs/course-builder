# Golf Course Builder - Embabel Agent Implementation

A Spring Boot application demonstrating the **Matryoshka Tool Pattern** for building GSPro golf courses through the "None to Done" workflow.

> **Note**: This is the agent orchestration component of the course builder pipeline. See the [main README](../README.md) for an overview of all components and [plan.md](../plan.md) for the full automation specification.

## Overview

This project implements the course builder workflow from [plan.md](../plan.md) using **Goal-Oriented Action Planning (GOAP)** combined with the nested tools pattern (Matryoshka tools) from [embabel-agent PR #1289](https://github.com/embabel/embabel-agent/pull/1289).

### Why GOAP + Nested Tools?

The combination creates an intelligent, autonomous agent that can:

- **Plan Dynamically**: Automatically determine action sequences to achieve goals (e.g., "build complete course") based on current world state
- **Handle Complexity**: 50+ tools organized hierarchically, revealed progressively as GOAP selects relevant action groups
- **Adapt and Replan**: If an action fails or produces unexpected results, the agent can replan rather than following a rigid script
- **Track Progress**: Workflow gates map directly to GOAP world state, enabling goal-driven progress monitoring

### The "None to Done" Workflow

```
LIDAR → Unity (Terrain) → Phase2a (SAM SVG) → Unity (PNG) → Blender (Mesh) → Unity (Final)
```

**6 Phases:**
1. **Terrain Creation** (LIDAR) - Generate heightmap, set up Unity terrain
2. **Course Tracing** (Phase2a) - SAM-based automated satellite tracing
3. **Terrain Refinement** (Unity) - Apply overlay, adjust contours, export OBJ
4. **SVG Conversion** - GSProSVGConvert.exe processing
5. **Blender Processing** - Mesh import, conversion, peripherals, FBX export
6. **Unity Assembly** - Import, materials, vegetation, asset bundle

## Matryoshka Tool Pattern

The pattern prevents LLM context pollution by organizing 50+ tools hierarchically:

```
golf_course_builder (top-level)
├── lidar_mcp
│   ├── lidar_to_heightmap
│   └── unity_setup_terrain
├── phase2a_mcp
│   ├── phase2a_run
│   ├── phase2a_generate_masks
│   ├── phase2a_classify
│   ├── phase2a_interactive_select
│   ├── phase2a_generate_svg
│   └── phase2a_validate
├── unity_terrain_mcp
│   ├── unity_apply_terrain_overlay
│   ├── unity_adjust_terrain_contours
│   └── unity_export_terrain
├── svg_convert_mcp
│   └── svg_convert
├── blender_mcp
│   ├── blender_open_course_template
│   ├── blender_import_svg
│   ├── blender_import_terrain
│   ├── blender_convert_and_cut
│   ├── blender_convert_meshes
│   ├── blender_fix_donut
│   ├── blender_add_curbs
│   ├── blender_add_bulkhead
│   ├── blender_add_water_plane
│   └── blender_export_fbx
└── unity_assembly_mcp
    ├── unity_import_fbx
    ├── unity_add_colliders
    ├── unity_apply_materials
    ├── unity_place_vegetation
    └── unity_build_asset_bundle
```

## Project Structure

```
course-builder/
├── src/main/java/com/coursebuilder/
│   ├── agent/                    # AI Agents
│   │   ├── Agent.java           # Agent interface
│   │   ├── AgentRouter.java     # Routes tasks to appropriate agent
│   │   ├── GolfCourseWorkflowAgent.java  # Main workflow orchestrator
│   │   ├── Phase2aAgent.java    # SAM-based tracing specialist
│   │   └── BlenderAgent.java    # Mesh operations specialist
│   ├── tool/                    # Matryoshka Tools
│   │   ├── Tool.java            # Tool interface
│   │   ├── MatryoshkaTool.java  # Nested tool base class
│   │   ├── ToolRegistry.java    # Tool discovery and navigation
│   │   └── golfcourse/          # Golf course specific tools
│   │       ├── GolfCourseBuilderMatryoshkaTool.java
│   │       ├── LidarMcpTool.java
│   │       ├── Phase2aMcpTool.java
│   │       ├── UnityTerrainMcpTool.java
│   │       ├── SvgConvertMcpTool.java
│   │       ├── BlenderMcpTool.java
│   │       └── UnityAssemblyMcpTool.java
│   ├── model/                   # Domain models
│   │   ├── GolfCourse.java      # Course with workflow state
│   │   └── Hole.java            # Hole with features (including 98/99)
│   ├── service/                 # Business logic
│   │   ├── GolfCourseService.java
│   │   └── ChatService.java
│   └── controller/              # REST API
│       └── ChatController.java
├── src/test/java/com/coursebuilder/
│   └── harness/
│       └── GolfCourseTestHarness.java  # Comprehensive workflow tests
├── frontend/                    # React chat interface
│   └── src/
│       └── App.jsx
└── pom.xml
```

## Running the Application

### Backend (Spring Boot)

```bash
cd course-builder
./mvnw spring-boot:run
```

The API will be available at `http://localhost:8080`

### Frontend (React)

```bash
cd course-builder/frontend
npm install
npm run dev
```

The chat interface will be available at `http://localhost:3000`

## Running Tests

```bash
cd course-builder
./mvnw test
```

The test harness demonstrates:
- Matryoshka tool hierarchy navigation
- Agent routing based on task description
- Complete workflow execution through all 6 phases
- Gate completion tracking
- Special holes (98/99) handling

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/message` | POST | Send a message, get agent response |
| `/api/chat/agents` | GET | List available agents |
| `/api/chat/tools` | GET | Get tools by category |
| `/api/chat/tools/hierarchy` | GET | Get full tool hierarchy |
| `/api/chat/workflow/{courseId}` | GET | Get workflow progress |
| `/api/chat/courses` | GET | List all courses |
| `/api/chat/session` | POST | Create new chat session |

## Chat Interface Features

- **Workflow Progress**: Visual sidebar showing current phase (1-6)
- **Quick Actions**: Pre-built prompts for common operations
- **Tool Invocations**: See which tools were executed
- **Gate Tracking**: Monitor workflow gate completions
- **Markdown Support**: Rich text responses

## Key Concepts

### GOAP Architecture

This implementation uses **Goal-Oriented Action Planning (GOAP)**, an AI architecture developed by Jeff Orkin for the game F.E.A.R. GOAP enables agents to dynamically plan action sequences to achieve goals based on world state.

**GOAP Components in Course Builder:**

| Component | Implementation |
|-----------|----------------|
| **Goals** | Course completion states (e.g., `terrain_ready`, `course_complete`) |
| **World State** | `GolfCourse.workflowState` - tracks gate completions and file outputs |
| **Actions** | Matryoshka tools with preconditions and effects |
| **Planner** | `AgentRouter` + individual agents determine optimal action sequences |

**Example GOAP Planning:**
```
Goal: course_complete
Current State: {terrain_ready: true, svg_complete: false, ...}

Planner evaluates:
  1. Check preconditions for each available action
  2. Find actions whose effects advance toward goal
  3. Chain actions: phase2a_run → svg_convert → blender_export → unity_build
  4. Execute plan, update world state after each action
  5. Replan if action fails or state changes unexpectedly
```

### Agents
High-level AI coordinators that implement GOAP planning to understand user intent and orchestrate tool execution:
- **GolfCourseWorkflowAgent**: Main GOAP planner for the complete workflow, manages goals and world state
- **Phase2aAgent**: Specialist planner for SAM-based tracing sub-goals
- **BlenderAgent**: Specialist planner for mesh operation sub-goals

### Matryoshka Tools
Nested tool hierarchies (like Russian dolls) that reveal tools progressively, designed to work with GOAP:
- LLM sees only top-level `golf_course_builder` tool initially
- GOAP planner selects phase tools based on current goal and state
- Each phase tool reveals specific operations as actions become relevant
- **Preconditions** on nested tools ensure valid action sequencing
- **Effects** update world state to drive planning forward

### Workflow Gates
Checkpoints that must be completed before proceeding:
- `terrain_ready` (Phase 1)
- `svg_complete` (Phase 2)
- `terrain_exported` (Phase 3)
- `svg_converted` (Phase 4)
- `fbx_exported` (Phase 5)
- `course_complete` (Phase 6)

### Special Holes
- **Hole 98**: Cart paths (features that cut through other objects)
- **Hole 99**: Outer mesh (deep rough spanning multiple holes)

## Integration with Phase2a

This project integrates with the existing Phase2a Python pipeline for SAM-based course tracing. The `Phase2aMcpTool` wraps the Python CLI:

```bash
phase2a run satellite.png --checkpoint models/sam_vit_h_4b8939.pth -o output/
phase2a select satellite.png --checkpoint ... -o output/  # Interactive mode
```

## References

- [Embabel Agent - Matryoshka Tools PR](https://github.com/embabel/embabel-agent/pull/1289)
- [Course Builder Documentation](https://docs.google.com/document/d/1InsfFuOrAH4l2S6RnTy17_O8FPXwt_EA_jKLvW4Ky80)
- [None to Done Video Series](https://docs.google.com/document/d/1bwNRByfPQNbUOWfKymXvdoWq9QP9-1R0U1GaJf5z9fU)
