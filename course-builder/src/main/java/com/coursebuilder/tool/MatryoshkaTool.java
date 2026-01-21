package com.coursebuilder.tool;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Matryoshka Tool - A tool that contains nested tools.
 * 
 * Named after Russian nesting dolls, this pattern allows tools to be
 * organized hierarchically. When an LLM needs to perform a complex task,
 * it first sees only the top-level tool. Upon selecting it, the nested
 * tools are revealed, preventing context window pollution.
 * 
 * Example hierarchy for Course Builder:
 * 
 * CourseBuilderTool (top-level)
 * ├── ContentCreationTool
 * │   ├── LessonCreatorTool
 * │   ├── QuizCreatorTool
 * │   └── AssessmentCreatorTool
 * ├── CurriculumDesignTool
 * │   ├── OutlineGeneratorTool
 * │   ├── LearningObjectivesTool
 * │   └── SequencingTool
 * └── MediaTool
 *     ├── ImageGeneratorTool
 *     ├── VideoScriptTool
 *     └── InteractiveElementTool
 */
public abstract class MatryoshkaTool implements Tool {
    
    private final String name;
    private final String description;
    private final String category;
    private final List<Tool> nestedTools;
    
    protected MatryoshkaTool(String name, String description, String category, List<Tool> nestedTools) {
        this.name = name;
        this.description = description;
        this.category = category;
        this.nestedTools = nestedTools;
    }
    
    @Override
    public String getName() {
        return name;
    }
    
    @Override
    public String getDescription() {
        return description;
    }
    
    @Override
    public String getCategory() {
        return category;
    }
    
    @Override
    public boolean isMatryoshka() {
        return true;
    }
    
    /**
     * @return List of tools nested within this Matryoshka tool
     */
    public List<Tool> getNestedTools() {
        return nestedTools;
    }
    
    /**
     * Find a nested tool by name.
     */
    public Optional<Tool> findNestedTool(String toolName) {
        return nestedTools.stream()
            .filter(t -> t.getName().equals(toolName))
            .findFirst();
    }
    
    /**
     * Get all tools in the hierarchy (flattened).
     */
    public List<Tool> getAllToolsRecursive() {
        return nestedTools.stream()
            .flatMap(tool -> {
                if (tool instanceof MatryoshkaTool mt) {
                    return java.util.stream.Stream.concat(
                        java.util.stream.Stream.of(tool),
                        mt.getAllToolsRecursive().stream()
                    );
                }
                return java.util.stream.Stream.of(tool);
            })
            .toList();
    }
    
    @Override
    public Map<String, Object> getInputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "operation", Map.of(
                    "type", "string",
                    "description", "The specific operation to perform. Use 'list' to see available nested tools.",
                    "enum", buildOperationEnum()
                ),
                "parameters", Map.of(
                    "type", "object",
                    "description", "Parameters for the selected operation"
                )
            ),
            "required", List.of("operation")
        );
    }
    
    private List<String> buildOperationEnum() {
        var ops = new java.util.ArrayList<>(List.of("list", "help"));
        nestedTools.forEach(t -> ops.add(t.getName()));
        return ops;
    }
    
    @Override
    public ToolResult execute(Map<String, Object> input) {
        String operation = (String) input.get("operation");
        
        if (operation == null || "list".equals(operation)) {
            return ToolResult.withNestedTools(
                "Available tools in " + name + ":",
                nestedTools
            );
        }
        
        if ("help".equals(operation)) {
            return ToolResult.success(buildHelpMessage());
        }
        
        // Delegate to nested tool
        return findNestedTool(operation)
            .map(tool -> {
                @SuppressWarnings("unchecked")
                Map<String, Object> params = (Map<String, Object>) input.getOrDefault("parameters", Map.of());
                return tool.execute(params);
            })
            .orElse(ToolResult.error("Unknown operation: " + operation + ". Use 'list' to see available tools."));
    }
    
    private String buildHelpMessage() {
        StringBuilder sb = new StringBuilder();
        sb.append("# ").append(name).append("\n\n");
        sb.append(description).append("\n\n");
        sb.append("## Available Operations:\n\n");
        for (Tool tool : nestedTools) {
            sb.append("- **").append(tool.getName()).append("**: ").append(tool.getDescription()).append("\n");
        }
        return sb.toString();
    }
}
