package com.coursebuilder.agent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;

/**
 * Routes incoming requests to the most appropriate agent.
 * 
 * The router evaluates each registered agent's fitness for a task
 * and delegates to the best match. This enables specialized agents
 * for different aspects of course building.
 */
@Component
public class AgentRouter {
    
    private static final Logger log = LoggerFactory.getLogger(AgentRouter.class);
    
    private final List<Agent> agents;
    
    public AgentRouter(List<Agent> agents) {
        this.agents = agents;
        log.info("AgentRouter initialized with {} agents: {}", 
            agents.size(), 
            agents.stream().map(Agent::getName).toList());
    }
    
    /**
     * Find the best agent for a given task.
     */
    public Optional<Agent> route(String taskDescription) {
        log.debug("Routing task: {}", taskDescription);
        
        return agents.stream()
            .map(agent -> new AgentScore(agent, agent.evaluateFit(taskDescription)))
            .peek(as -> log.debug("Agent {} scored {} for task", as.agent.getName(), as.score))
            .filter(as -> as.score > 0.0)
            .max(Comparator.comparingDouble(as -> as.score))
            .map(as -> as.agent);
    }
    
    /**
     * Process a user message by routing to the appropriate agent.
     */
    public AgentResponse process(AgentContext context, String userMessage) {
        return route(userMessage)
            .map(agent -> {
                log.info("Routing to agent: {}", agent.getName());
                return agent.process(context, userMessage);
            })
            .orElseGet(() -> AgentResponse.simple(
                "I'm not sure how to help with that. I can assist with course creation, " +
                "curriculum design, content generation, and assessments."
            ));
    }
    
    /**
     * Get all registered agents.
     */
    public List<Agent> getAgents() {
        return agents;
    }
    
    private record AgentScore(Agent agent, double score) {}
}
