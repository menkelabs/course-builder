# Embabel Automation Plan for Course Builder

## Overview

This document outlines an automation strategy using **Embabel** as the orchestration layer, with **MCP (Model Context Protocol) tools** designed specifically to facilitate the **"None to Done"** workflow. Every tool exists to move a course project from concept to completion.

---

## Table of Contents

1. [The None to Done Philosophy](#the-none-to-done-philosophy)
2. [Workflow Stages](#workflow-stages)
3. [MCP Tools by Workflow Stage](#mcp-tools-by-workflow-stage)
4. [Tool Implementations](#tool-implementations)
5. [Embabel Orchestration](#embabel-orchestration)
6. [Implementation Roadmap](#implementation-roadmap)

---

## The None to Done Philosophy

### Core Principle

**Every MCP tool exists solely to facilitate moving from "None" (no content) to "Done" (published course).**

Tools are not general-purpose utilities—they are purpose-built to support specific stages of the course creation workflow. If a tool doesn't directly contribute to completing a course, it doesn't belong in the system.

### The Complete Journey

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  NONE   │───▶│ CONCEPT │───▶│  DRAFT  │───▶│  BUILD  │───▶│ REVIEW  │───▶│  DONE   │
│         │    │         │    │         │    │         │    │         │    │         │
│ Empty   │    │ Ideas & │    │ Scripts │    │ Assets  │    │ Testing │    │Published│
│ Project │    │ Outline │    │ & Plans │    │ & Scenes│    │ & Polish│    │ Course  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Workflow Stages

### Stage 1: NONE → CONCEPT

**Goal**: Transform an idea into a structured course outline

| Input | Output |
|-------|--------|
| Course topic/idea | Structured outline with modules, lessons, learning objectives |

### Stage 2: CONCEPT → DRAFT

**Goal**: Expand outline into detailed content plans

| Input | Output |
|-------|--------|
| Course outline | Scripts, storyboards, asset requirements, interaction designs |

### Stage 3: DRAFT → BUILD

**Goal**: Create all assets and assemble the course

| Input | Output |
|-------|--------|
| Content plans | 3D models, scenes, animations, audio, interactive elements |

### Stage 4: BUILD → REVIEW

**Goal**: Test and refine the course

| Input | Output |
|-------|--------|
| Assembled course | Tested, polished, QA-passed course |

### Stage 5: REVIEW → DONE

**Goal**: Package and publish the final course

| Input | Output |
|-------|--------|
| Reviewed course | Published, deployed, documented course |

---

## MCP Tools by Workflow Stage

### Stage 1 Tools: NONE → CONCEPT

These tools help transform raw ideas into structured course plans.

| Tool | Purpose in Workflow |
|------|---------------------|
| `course_outline_from_topic` | Generate initial course structure from a topic description |
| `learning_objectives_generator` | Create measurable learning objectives for each module |
| `module_structure_builder` | Break course into logical modules and lessons |
| `prerequisite_analyzer` | Identify and document required prior knowledge |
| `scope_estimator` | Estimate content volume and complexity |

```yaml
# Example: Starting from nothing
input:
  topic: "Introduction to 3D Modeling for Game Development"
  target_audience: "Beginners"
  duration: "8 hours"

output:
  course_outline:
    modules: 6
    lessons: 24
    learning_objectives: 48
    asset_requirements: preliminary_list
```

### Stage 2 Tools: CONCEPT → DRAFT

These tools expand the outline into actionable content plans.

| Tool | Purpose in Workflow |
|------|---------------------|
| `lesson_script_generator` | Create detailed scripts for each lesson |
| `storyboard_creator` | Generate visual storyboards for scenes |
| `asset_requirements_compiler` | List all 3D models, textures, audio needed |
| `interaction_designer` | Define interactive elements and user flows |
| `quiz_question_generator` | Create assessment questions from objectives |

```yaml
# Example: Expanding a lesson
input:
  lesson: "Understanding Mesh Topology"
  learning_objectives:
    - "Identify vertices, edges, and faces"
    - "Explain why topology matters for animation"

output:
  script: detailed_narration_script
  storyboard: 12_scene_visual_plan
  assets_needed:
    - 3d_models: ["cube_topology_demo", "character_topology_comparison"]
    - textures: ["wireframe_overlay"]
    - audio: ["narration_track"]
  interactions:
    - type: "click_to_highlight"
      targets: ["vertices", "edges", "faces"]
```

### Stage 3 Tools: BUILD (Blender MCP)

These tools create the actual 3D content in Blender.

| Tool | Purpose in Workflow |
|------|---------------------|
| `create_lesson_environment` | Build the 3D scene for a specific lesson |
| `generate_demonstration_model` | Create models that demonstrate concepts |
| `setup_camera_sequence` | Configure camera positions for lesson flow |
| `apply_educational_materials` | Add materials optimized for clarity |
| `export_for_unity` | Export assets in Unity-ready format |

```yaml
# Example: Building lesson assets
input:
  lesson_id: "topology_basics"
  storyboard: storyboard_reference
  asset_list: ["cube_topology_demo", "character_topology_comparison"]

output:
  blender_files:
    - "topology_basics_scene.blend"
  exported_assets:
    - "cube_topology_demo.fbx"
    - "character_topology_comparison.fbx"
  textures:
    - "wireframe_overlay.png"
```

### Stage 3 Tools: BUILD (Unity MCP)

These tools assemble the course in Unity.

| Tool | Purpose in Workflow |
|------|---------------------|
| `create_lesson_scene` | Set up Unity scene from storyboard |
| `import_lesson_assets` | Bring in Blender exports with correct settings |
| `setup_lesson_progression` | Configure lesson flow and navigation |
| `add_interactive_elements` | Implement click/hover/drag interactions |
| `integrate_audio_narration` | Sync audio with scene progression |
| `configure_assessment` | Set up quizzes and knowledge checks |

```yaml
# Example: Assembling in Unity
input:
  lesson_id: "topology_basics"
  assets: [exported_blender_assets]
  script: narration_script
  interactions: interaction_definitions

output:
  unity_scene: "Lesson_TopologyBasics.unity"
  prefabs_created: 5
  interactions_configured: 3
  audio_synced: true
```

### Stage 3 Tools: BUILD (Supporting Tools)

| Tool | Purpose in Workflow |
|------|---------------------|
| `generate_narration_audio` | Create voiceover from scripts (TTS or guide for recording) |
| `create_ui_graphics` | Generate UI elements for the lesson |
| `optimize_textures` | Prepare textures at correct resolutions |
| `generate_thumbnails` | Create preview images for lessons |

### Stage 4 Tools: BUILD → REVIEW

These tools test and validate the course.

| Tool | Purpose in Workflow |
|------|---------------------|
| `run_playthrough_test` | Automated walkthrough of all lessons |
| `check_learning_objective_coverage` | Verify all objectives are addressed |
| `validate_interactions` | Test all interactive elements work |
| `accessibility_check` | Verify accessibility requirements |
| `performance_profile` | Check performance on target platforms |

```yaml
# Example: Review process
input:
  course_build: complete_course

output:
  test_report:
    lessons_tested: 24
    interactions_validated: 156
    objectives_covered: 48/48
    accessibility_score: 94%
    performance_rating: "Good"
  issues_found:
    - lesson_12: "Audio desync at 2:34"
    - lesson_18: "Interaction not responding on mobile"
```

### Stage 5 Tools: REVIEW → DONE

These tools finalize and publish the course.

| Tool | Purpose in Workflow |
|------|---------------------|
| `build_for_platform` | Create builds for target platforms |
| `package_scorm` | Create LMS-compatible package |
| `generate_documentation` | Create instructor guides, syllabi |
| `create_marketing_assets` | Generate promotional materials |
| `deploy_to_staging` | Push to staging environment |
| `publish_release` | Final deployment to production |

```yaml
# Example: Publishing
input:
  reviewed_course: qa_passed_build
  target_platforms: ["web", "mobile", "desktop"]

output:
  builds:
    - web_build: "course_v1.0_web.zip"
    - mobile_build: "course_v1.0.apk"
    - desktop_build: "course_v1.0_win.exe"
  scorm_package: "course_v1.0_scorm.zip"
  documentation:
    - instructor_guide.pdf
    - learner_syllabus.pdf
  status: DONE
```

---

## Tool Implementations

### Blender MCP Server

The Blender MCP server focuses exclusively on course asset creation.

```python
class BlenderCourseMCP:
    """
    Blender MCP tools exist only to create assets 
    that move lessons from draft to built.
    """
    
    # Stage 3 Tools - Asset Creation
    
    def create_lesson_environment(self, lesson_spec: dict):
        """Create complete 3D environment for a lesson."""
        # Reads storyboard, creates scene, exports for Unity
        pass
    
    def generate_demonstration_model(self, concept: str, style: str):
        """Create a model that demonstrates a specific concept."""
        # Purpose-built for educational clarity
        pass
    
    def setup_camera_sequence(self, storyboard: dict):
        """Configure cameras to match storyboard shots."""
        # Each camera position serves the lesson narrative
        pass
    
    def export_for_unity(self, scene: str):
        """Export all assets Unity-ready."""
        # Optimized for the course runtime
        pass
```

### Unity MCP Server

The Unity MCP server focuses exclusively on course assembly and delivery.

```csharp
// Unity MCP tools exist only to assemble and deliver courses

public class UnityCourseMCP
{
    // Stage 3 Tools - Assembly
    
    public void CreateLessonScene(LessonSpec spec)
    {
        // Build scene from storyboard specification
    }
    
    public void SetupLessonProgression(ProgressionConfig config)
    {
        // Configure how learner moves through content
    }
    
    public void AddInteractiveElement(InteractionDef def)
    {
        // Add interaction that supports learning objective
    }
    
    // Stage 4 Tools - Testing
    
    public TestReport RunPlaythroughTest(Course course)
    {
        // Automated testing of complete course
    }
    
    // Stage 5 Tools - Publishing
    
    public Build BuildForPlatform(Platform target)
    {
        // Create deployable build
    }
}
```

---

## Embabel Orchestration

Embabel drives the entire None to Done workflow, invoking the right MCP tools at each stage.

### Workflow Definition

```yaml
workflow: none_to_done
name: "Complete Course Creation"

stages:
  - stage: concept
    tools:
      - course_outline_from_topic
      - learning_objectives_generator
      - module_structure_builder
    gate: outline_approved
    
  - stage: draft
    tools:
      - lesson_script_generator
      - storyboard_creator
      - asset_requirements_compiler
      - interaction_designer
    gate: content_plan_complete
    
  - stage: build
    parallel:
      - tools: [blender_create_lesson_environment, blender_generate_demonstration_model]
        for_each: lesson
      - tools: [generate_narration_audio]
        for_each: script
    then:
      - tools: [unity_create_lesson_scene, unity_import_lesson_assets]
        for_each: lesson
      - tools: [unity_setup_lesson_progression, unity_add_interactive_elements]
    gate: all_lessons_assembled
    
  - stage: review
    tools:
      - run_playthrough_test
      - check_learning_objective_coverage
      - validate_interactions
      - accessibility_check
    gate: qa_passed
    
  - stage: done
    tools:
      - build_for_platform
      - package_scorm
      - generate_documentation
      - publish_release
    gate: published
```

### Embabel Commands

```
User: "Create a course on Introduction to 3D Modeling"

Embabel:
1. Invokes course_outline_from_topic("Introduction to 3D Modeling")
2. Generates learning objectives for each module
3. Creates detailed lesson plans
4. For each lesson:
   - Generates storyboard
   - Creates assets in Blender
   - Assembles in Unity
5. Runs full test suite
6. Builds and publishes

Result: Complete, published course
```

---

## Implementation Roadmap

### Phase 1: Core Workflow Tools

- [ ] `course_outline_from_topic` - Concept stage entry point
- [ ] `lesson_script_generator` - Draft stage core tool
- [ ] `asset_requirements_compiler` - Draft to Build bridge

### Phase 2: Blender MCP (Build Stage)

- [ ] `create_lesson_environment` - Scene creation
- [ ] `generate_demonstration_model` - Asset creation
- [ ] `export_for_unity` - Build pipeline

### Phase 3: Unity MCP (Build Stage)

- [ ] `create_lesson_scene` - Scene assembly
- [ ] `import_lesson_assets` - Asset integration
- [ ] `setup_lesson_progression` - Flow configuration
- [ ] `add_interactive_elements` - Interaction layer

### Phase 4: Review & Publish Tools

- [ ] `run_playthrough_test` - Automated QA
- [ ] `validate_interactions` - Interaction testing
- [ ] `build_for_platform` - Build generation
- [ ] `publish_release` - Final deployment

### Phase 5: Embabel Integration

- [ ] Workflow orchestration engine
- [ ] Stage gate management
- [ ] Progress tracking
- [ ] Error recovery

---

## Summary

The MCP tools in this system are **not** general-purpose automation utilities. Each tool exists to:

1. **Move content forward** through the None to Done pipeline
2. **Bridge specific stages** in the workflow
3. **Eliminate manual bottlenecks** that slow course creation
4. **Maintain quality** while enabling speed

By keeping this focus, we ensure that every tool we build directly contributes to the goal: **taking a course from nothing to published**.

---

## References

- **OPCD Wiki**: [Open Project Community Designers Wiki](https://open-project-community-designers.github.io/OPCD-Wiki/)
- **MCP Specification**: Model Context Protocol documentation
- **Embabel**: AI-driven workflow orchestration framework
