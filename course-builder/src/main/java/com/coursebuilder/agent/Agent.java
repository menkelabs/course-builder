package com.coursebuilder.agent;

import com.coursebuilder.tool.Tool;
import java.util.List;

/**
 * An Agent is a high-level AI coordinator that understands user intent
 * and orchestrates tool execution to accomplish tasks.
 * 
 * Agents differ from tools in that:
 * - Agents have goals and can plan multi-step workflows
 * - Agents can invoke multiple tools in sequence
 * - Agents maintain conversation context
 * - Agents can delegate to other agents
 */
public interface Agent {
    
    /**
     * @return Unique identifier for this agent
     */
    String getName();
    
    /**
     * @return Description of the agent's capabilities and domain
     */
    String getDescription();
    
    /**
     * @return List of tools this agent has access to
     */
    List<Tool> getTools();
    
    /**
     * Process a user message and generate a response.
     * The agent may invoke tools as needed.
     * 
     * @param context Current conversation context
     * @param userMessage The user's input
     * @return The agent's response
     */
    AgentResponse process(AgentContext context, String userMessage);
    
    /**
     * @return List of task types this agent can handle
     */
    List<String> getCapabilities();
    
    /**
     * Evaluate how well-suited this agent is for a given task.
     * 
     * @param taskDescription Description of the task
     * @return Score from 0.0 to 1.0 indicating suitability
     */
    double evaluateFit(String taskDescription);
}
