package com.coursebuilder.agent;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Context for an agent conversation session.
 * 
 * Maintains:
 * - Conversation history
 * - Tool execution history
 * - Session state
 * - Current working data (e.g., course being built)
 */
public class AgentContext {
    
    private final String sessionId;
    private final List<Message> conversationHistory;
    private final List<ToolExecution> toolExecutionHistory;
    private final Map<String, Object> sessionState;
    private String currentCourseId;
    
    public AgentContext() {
        this.sessionId = UUID.randomUUID().toString();
        this.conversationHistory = new ArrayList<>();
        this.toolExecutionHistory = new ArrayList<>();
        this.sessionState = new HashMap<>();
    }
    
    public String getSessionId() {
        return sessionId;
    }
    
    public void addMessage(Message message) {
        conversationHistory.add(message);
    }
    
    public List<Message> getConversationHistory() {
        return new ArrayList<>(conversationHistory);
    }
    
    public void recordToolExecution(ToolExecution execution) {
        toolExecutionHistory.add(execution);
    }
    
    public List<ToolExecution> getToolExecutionHistory() {
        return new ArrayList<>(toolExecutionHistory);
    }
    
    public void setState(String key, Object value) {
        sessionState.put(key, value);
    }
    
    @SuppressWarnings("unchecked")
    public <T> T getState(String key, Class<T> type) {
        return (T) sessionState.get(key);
    }
    
    public String getCurrentCourseId() {
        return currentCourseId;
    }
    
    public void setCurrentCourseId(String courseId) {
        this.currentCourseId = courseId;
    }
    
    /**
     * Represents a message in the conversation.
     */
    public record Message(
        String role,  // "user", "assistant", "system", "tool"
        String content,
        String toolName,
        Map<String, Object> toolInput,
        Map<String, Object> toolOutput
    ) {
        public static Message user(String content) {
            return new Message("user", content, null, null, null);
        }
        
        public static Message assistant(String content) {
            return new Message("assistant", content, null, null, null);
        }
        
        public static Message system(String content) {
            return new Message("system", content, null, null, null);
        }
        
        public static Message tool(String toolName, Map<String, Object> input, Map<String, Object> output) {
            return new Message("tool", null, toolName, input, output);
        }
    }
    
    /**
     * Record of a tool execution.
     */
    public record ToolExecution(
        String toolName,
        Map<String, Object> input,
        Map<String, Object> output,
        boolean success,
        long durationMs,
        String parentToolName  // If executed as part of a Matryoshka hierarchy
    ) {}
}
