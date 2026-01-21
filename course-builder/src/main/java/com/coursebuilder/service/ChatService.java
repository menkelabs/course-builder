package com.coursebuilder.service;

import com.coursebuilder.agent.AgentContext;
import com.coursebuilder.agent.AgentResponse;
import com.coursebuilder.agent.AgentRouter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service for managing chat sessions and routing messages to agents.
 */
@Service
public class ChatService {
    
    private static final Logger log = LoggerFactory.getLogger(ChatService.class);
    
    private final AgentRouter agentRouter;
    private final Map<String, AgentContext> sessions = new ConcurrentHashMap<>();
    
    public ChatService(AgentRouter agentRouter) {
        this.agentRouter = agentRouter;
    }
    
    /**
     * Create a new chat session.
     */
    public String createSession() {
        AgentContext context = new AgentContext();
        sessions.put(context.getSessionId(), context);
        log.info("Created new session: {}", context.getSessionId());
        return context.getSessionId();
    }
    
    /**
     * Process a message in a session.
     */
    public AgentResponse processMessage(String sessionId, String message) {
        AgentContext context = sessions.computeIfAbsent(
            sessionId != null ? sessionId : UUID.randomUUID().toString(),
            k -> new AgentContext()
        );
        
        log.info("Processing message in session {}: {}", context.getSessionId(), message);
        
        AgentResponse response = agentRouter.process(context, message);
        context.addMessage(AgentContext.Message.assistant(response.message()));
        
        return response;
    }
    
    /**
     * Get context for a session.
     */
    public AgentContext getContext(String sessionId) {
        return sessions.get(sessionId);
    }
    
    /**
     * Get or create a session.
     */
    public AgentContext getOrCreateContext(String sessionId) {
        return sessions.computeIfAbsent(
            sessionId != null ? sessionId : UUID.randomUUID().toString(),
            k -> new AgentContext()
        );
    }
}
