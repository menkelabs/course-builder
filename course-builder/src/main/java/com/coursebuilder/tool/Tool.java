package com.coursebuilder.tool;

import java.util.Map;

/**
 * Base interface for all tools in the Course Builder system.
 * 
 * Tools are callable units that perform specific operations.
 * They can be simple (leaf tools) or compound (Matryoshka tools
 * that contain nested tools).
 */
public interface Tool {
    
    /**
     * @return Unique identifier for this tool
     */
    String getName();
    
    /**
     * @return Human-readable description of what this tool does
     */
    String getDescription();
    
    /**
     * @return JSON Schema describing the tool's input parameters
     */
    Map<String, Object> getInputSchema();
    
    /**
     * Execute the tool with the given input parameters.
     * 
     * @param input Map of parameter names to values
     * @return Result of the tool execution
     */
    ToolResult execute(Map<String, Object> input);
    
    /**
     * @return true if this tool contains nested tools (is a Matryoshka tool)
     */
    default boolean isMatryoshka() {
        return false;
    }
    
    /**
     * @return Category/group this tool belongs to for organization
     */
    default String getCategory() {
        return "general";
    }
}
