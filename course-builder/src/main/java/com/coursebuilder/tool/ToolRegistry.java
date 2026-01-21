package com.coursebuilder.tool;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Registry for all available tools in the system.
 * 
 * Provides:
 * - Tool discovery and registration
 * - Matryoshka hierarchy navigation
 * - Tool lookup by name or category
 */
@Component
public class ToolRegistry {
    
    private static final Logger log = LoggerFactory.getLogger(ToolRegistry.class);
    
    private final Map<String, Tool> tools = new HashMap<>();
    private final Map<String, List<Tool>> toolsByCategory = new HashMap<>();
    
    public ToolRegistry(List<Tool> toolBeans) {
        toolBeans.forEach(this::register);
        log.info("ToolRegistry initialized with {} tools", tools.size());
    }
    
    /**
     * Register a tool in the registry.
     */
    public void register(Tool tool) {
        tools.put(tool.getName(), tool);
        toolsByCategory
            .computeIfAbsent(tool.getCategory(), k -> new ArrayList<>())
            .add(tool);
        
        log.debug("Registered tool: {} (category: {}, matryoshka: {})", 
            tool.getName(), tool.getCategory(), tool.isMatryoshka());
        
        // Also register nested tools for direct access
        if (tool instanceof MatryoshkaTool mt) {
            for (Tool nested : mt.getNestedTools()) {
                tools.put(tool.getName() + "." + nested.getName(), nested);
            }
        }
    }
    
    /**
     * Get a tool by name.
     */
    public Optional<Tool> getTool(String name) {
        return Optional.ofNullable(tools.get(name));
    }
    
    /**
     * Get all top-level tools (excludes nested tools from Matryoshka).
     */
    public List<Tool> getTopLevelTools() {
        return toolsByCategory.values().stream()
            .flatMap(List::stream)
            .filter(t -> !isNestedTool(t))
            .toList();
    }
    
    /**
     * Get tools by category.
     */
    public List<Tool> getToolsByCategory(String category) {
        return toolsByCategory.getOrDefault(category, List.of());
    }
    
    /**
     * Get all available categories.
     */
    public Set<String> getCategories() {
        return toolsByCategory.keySet();
    }
    
    /**
     * Navigate to a nested tool using dot notation.
     * Example: "content_creation.create_lesson"
     */
    public Optional<Tool> navigateTo(String path) {
        String[] parts = path.split("\\.");
        if (parts.length == 0) {
            return Optional.empty();
        }
        
        Tool current = tools.get(parts[0]);
        for (int i = 1; i < parts.length && current != null; i++) {
            if (current instanceof MatryoshkaTool mt) {
                current = mt.findNestedTool(parts[i]).orElse(null);
            } else {
                return Optional.empty();
            }
        }
        
        return Optional.ofNullable(current);
    }
    
    /**
     * Execute a tool by name with the given input.
     */
    public ToolResult execute(String toolName, Map<String, Object> input) {
        return getTool(toolName)
            .map(tool -> tool.execute(input))
            .orElse(ToolResult.error("Tool not found: " + toolName));
    }
    
    /**
     * Get tool descriptions suitable for LLM context.
     */
    public String getToolDescriptions() {
        return getTopLevelTools().stream()
            .map(t -> String.format("- %s: %s%s", 
                t.getName(), 
                t.getDescription(),
                t.isMatryoshka() ? " (contains nested tools)" : ""))
            .collect(Collectors.joining("\n"));
    }
    
    private boolean isNestedTool(Tool tool) {
        // A tool is nested if it appears inside a Matryoshka tool
        return tools.values().stream()
            .filter(t -> t instanceof MatryoshkaTool)
            .map(t -> (MatryoshkaTool) t)
            .anyMatch(mt -> mt.getNestedTools().contains(tool));
    }
}
