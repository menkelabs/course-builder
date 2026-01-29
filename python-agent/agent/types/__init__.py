"""
Type definitions for the Python Agent.

Domain types that can be used as inputs/outputs for actions.
These types are registered automatically and returned via /api/v1/types.
"""

from ..models import DynamicType, PropertyDef

# Additional shared types can be defined here

# Course-related types
GolfCourse = DynamicType(
    name="GolfCourse",
    description="A golf course being built",
    own_properties=[
        PropertyDef("course_id", "string", "Unique course identifier"),
        PropertyDef("name", "string", "Course name"),
        PropertyDef("location", "string", "Course location"),
        PropertyDef("holes", "number", "Number of holes (9 or 18)"),
        PropertyDef("workflow_state", "WorkflowState", "Current workflow state"),
    ],
)

WorkflowState = DynamicType(
    name="WorkflowState",
    description="Current state of course building workflow",
    own_properties=[
        PropertyDef("current_phase", "string", "Current phase (phase1a, blender, unity)"),
        PropertyDef("completed_gates", "array", "List of completed workflow gates"),
        PropertyDef("artifacts", "object", "Map of artifact names to paths"),
    ],
)

# Workflow gates as a type
WorkflowGate = DynamicType(
    name="WorkflowGate",
    description="A workflow gate/milestone",
    own_properties=[
        PropertyDef("name", "string", "Gate name (e.g., svg_complete)"),
        PropertyDef("description", "string", "Gate description"),
        PropertyDef("completed", "boolean", "Whether the gate is complete"),
        PropertyDef("completed_at", "string", "ISO timestamp when completed"),
    ],
)

# Export all types
__all__ = ["GolfCourse", "WorkflowState", "WorkflowGate"]


def register_all_types(registry):
    """Register all types with the given registry."""
    for dtype in [GolfCourse, WorkflowState, WorkflowGate]:
        registry.register_type(dtype)
