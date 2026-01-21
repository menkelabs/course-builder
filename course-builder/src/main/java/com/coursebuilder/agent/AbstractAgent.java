package com.coursebuilder.agent;

import com.coursebuilder.tool.Tool;
import com.coursebuilder.tool.ToolRegistry;
import com.coursebuilder.tool.ToolResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.regex.Pattern;

/**
 * Abstract base class for agents providing common functionality.
 */
public abstract class AbstractAgent implements Agent {
    
    protected final Logger log = LoggerFactory.getLogger(getClass());
    protected final ToolRegistry toolRegistry;
    protected final List<Tool> tools;
    protected final List<String> capabilities;
    protected final List<Pattern> capabilityPatterns;
    
    protected AbstractAgent(ToolRegistry toolRegistry, List<Tool> tools, List<String> capabilities) {
        this.toolRegistry = toolRegistry;
        this.tools = tools;
        this.capabilities = capabilities;
        this.capabilityPatterns = capabilities.stream()
            .map(c -> Pattern.compile(c, Pattern.CASE_INSENSITIVE))
            .toList();
    }
    
    @Override
    public List<Tool> getTools() {
        return tools;
    }
    
    @Override
    public List<String> getCapabilities() {
        return capabilities;
    }
    
    @Override
    public double evaluateFit(String taskDescription) {
        // Simple keyword-based matching for demonstration
        String lowerTask = taskDescription.toLowerCase();
        
        long matches = capabilityPatterns.stream()
            .filter(p -> p.matcher(lowerTask).find())
            .count();
        
        return (double) matches / capabilities.size();
    }
    
    /**
     * Execute a tool by name with given parameters.
     */
    protected ToolResult executeTool(String toolName, Map<String, Object> params, AgentContext context) {
        log.debug("Executing tool: {} with params: {}", toolName, params);
        
        long startTime = System.currentTimeMillis();
        ToolResult result = toolRegistry.execute(toolName, params);
        long duration = System.currentTimeMillis() - startTime;
        
        context.recordToolExecution(new AgentContext.ToolExecution(
            toolName, params, result.data(), result.success(), duration, null
        ));
        
        return result;
    }
    
    /**
     * Select the best tool for a given task description.
     */
    protected Optional<Tool> selectTool(String taskDescription) {
        return tools.stream()
            .max(Comparator.comparingDouble(t -> scoreTool(t, taskDescription)));
    }
    
    private double scoreTool(Tool tool, String taskDescription) {
        String lowerTask = taskDescription.toLowerCase();
        String lowerDesc = tool.getDescription().toLowerCase();
        String lowerName = tool.getName().toLowerCase().replace("_", " ");
        
        double score = 0.0;
        
        // Check for keyword matches
        String[] taskWords = lowerTask.split("\\s+");
        for (String word : taskWords) {
            if (word.length() > 3) {
                if (lowerDesc.contains(word)) score += 0.1;
                if (lowerName.contains(word)) score += 0.2;
            }
        }
        
        return score;
    }
    
    /**
     * Build the system prompt for this agent.
     */
    protected String buildSystemPrompt() {
        StringBuilder sb = new StringBuilder();
        sb.append("You are ").append(getName()).append(". ").append(getDescription()).append("\n\n");
        sb.append("You have access to the following tools:\n\n");
        
        for (Tool tool : tools) {
            sb.append("- **").append(tool.getName()).append("**: ").append(tool.getDescription());
            if (tool.isMatryoshka()) {
                sb.append(" (contains nested tools - use 'list' operation to see them)");
            }
            sb.append("\n");
        }
        
        return sb.toString();
    }
}
