package com.coursebuilder.agent;

import java.util.List;
import java.util.Map;

/**
 * Response from an agent after processing a user message.
 */
public record AgentResponse(
    String message,
    List<ToolInvocation> toolInvocations,
    boolean requiresFollowUp,
    String suggestedNextStep,
    Map<String, Object> metadata
) {
    
    public static AgentResponse simple(String message) {
        return new AgentResponse(message, List.of(), false, null, Map.of());
    }
    
    public static AgentResponse withTools(String message, List<ToolInvocation> tools) {
        return new AgentResponse(message, tools, false, null, Map.of());
    }
    
    public static AgentResponse withFollowUp(String message, String nextStep) {
        return new AgentResponse(message, List.of(), true, nextStep, Map.of());
    }
    
    /**
     * Record of a tool invocation during agent processing.
     */
    public record ToolInvocation(
        String toolName,
        Map<String, Object> input,
        Map<String, Object> output,
        boolean success,
        List<ToolInvocation> nestedInvocations  // For Matryoshka tools
    ) {
        public static ToolInvocation of(String toolName, Map<String, Object> input, Map<String, Object> output) {
            return new ToolInvocation(toolName, input, output, true, List.of());
        }
        
        public static ToolInvocation withNested(String toolName, Map<String, Object> input, 
                                                 Map<String, Object> output, List<ToolInvocation> nested) {
            return new ToolInvocation(toolName, input, output, true, nested);
        }
        
        public static ToolInvocation failed(String toolName, Map<String, Object> input, String error) {
            return new ToolInvocation(toolName, input, Map.of("error", error), false, List.of());
        }
    }
}
