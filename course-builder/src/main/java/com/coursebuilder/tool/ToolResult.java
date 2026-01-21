package com.coursebuilder.tool;

import java.util.List;
import java.util.Map;

/**
 * Result of a tool execution.
 * 
 * Can contain:
 * - Simple result data
 * - Nested tool suggestions (for Matryoshka tools)
 * - Error information
 */
public record ToolResult(
    boolean success,
    String message,
    Map<String, Object> data,
    List<Tool> suggestedTools,
    String errorMessage
) {
    
    public static ToolResult success(String message, Map<String, Object> data) {
        return new ToolResult(true, message, data, List.of(), null);
    }
    
    public static ToolResult success(String message) {
        return new ToolResult(true, message, Map.of(), List.of(), null);
    }
    
    public static ToolResult withNestedTools(String message, List<Tool> nestedTools) {
        return new ToolResult(true, message, Map.of(), nestedTools, null);
    }
    
    public static ToolResult error(String errorMessage) {
        return new ToolResult(false, null, Map.of(), List.of(), errorMessage);
    }
    
    public boolean hasNestedTools() {
        return suggestedTools != null && !suggestedTools.isEmpty();
    }
}
