package com.coursebuilder.controller;

import com.coursebuilder.agent.AgentContext;
import com.coursebuilder.agent.AgentResponse;
import com.coursebuilder.agent.AgentRouter;
import com.coursebuilder.service.ChatService;
import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.ToolRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST controller for the Golf Course Builder chat interface.
 * 
 * Provides endpoints for:
 * - Sending chat messages to orchestrate the "None to Done" workflow
 * - Getting conversation history
 * - Listing available agents and tools
 * - Tracking workflow progress
 */
@RestController
@RequestMapping("/api/chat")
@CrossOrigin(origins = "*")
public class ChatController {
    
    private static final Logger log = LoggerFactory.getLogger(ChatController.class);
    
    private final ChatService chatService;
    private final AgentRouter agentRouter;
    private final ToolRegistry toolRegistry;
    private final GolfCourseService courseService;
    
    public ChatController(ChatService chatService, AgentRouter agentRouter, 
                          ToolRegistry toolRegistry, GolfCourseService courseService) {
        this.chatService = chatService;
        this.agentRouter = agentRouter;
        this.toolRegistry = toolRegistry;
        this.courseService = courseService;
    }
    
    /**
     * Send a message and get a response from the appropriate agent.
     */
    @PostMapping("/message")
    public ResponseEntity<ChatResponse> sendMessage(@RequestBody ChatRequest request) {
        log.info("Received message: {}", request.message());
        
        AgentResponse response = chatService.processMessage(
            request.sessionId(),
            request.message()
        );
        
        return ResponseEntity.ok(new ChatResponse(
            response.message(),
            response.toolInvocations().stream()
                .map(t -> new ToolInvocationDto(t.toolName(), t.input(), t.output(), t.success()))
                .toList(),
            response.requiresFollowUp(),
            response.suggestedNextStep()
        ));
    }
    
    /**
     * Get available agents and their capabilities.
     */
    @GetMapping("/agents")
    public ResponseEntity<List<AgentInfo>> getAgents() {
        List<AgentInfo> agents = agentRouter.getAgents().stream()
            .map(a -> new AgentInfo(a.getName(), a.getDescription(), a.getCapabilities()))
            .toList();
        return ResponseEntity.ok(agents);
    }
    
    /**
     * Get available tools organized by category.
     */
    @GetMapping("/tools")
    public ResponseEntity<Map<String, List<ToolInfo>>> getTools() {
        var toolsByCategory = new java.util.HashMap<String, List<ToolInfo>>();
        
        for (String category : toolRegistry.getCategories()) {
            toolsByCategory.put(category, toolRegistry.getToolsByCategory(category).stream()
                .map(t -> new ToolInfo(t.getName(), t.getDescription(), t.isMatryoshka()))
                .toList()
            );
        }
        
        return ResponseEntity.ok(toolsByCategory);
    }
    
    /**
     * Get the tool hierarchy (for visualization).
     */
    @GetMapping("/tools/hierarchy")
    public ResponseEntity<List<ToolHierarchy>> getToolHierarchy() {
        List<ToolHierarchy> hierarchy = toolRegistry.getTopLevelTools().stream()
            .map(this::buildToolHierarchy)
            .toList();
        return ResponseEntity.ok(hierarchy);
    }
    
    /**
     * Get conversation history for a session.
     */
    @GetMapping("/history/{sessionId}")
    public ResponseEntity<List<MessageDto>> getHistory(@PathVariable String sessionId) {
        AgentContext context = chatService.getContext(sessionId);
        if (context == null) {
            return ResponseEntity.notFound().build();
        }
        
        List<MessageDto> messages = context.getConversationHistory().stream()
            .map(m -> new MessageDto(m.role(), m.content()))
            .toList();
        return ResponseEntity.ok(messages);
    }
    
    /**
     * Create a new session.
     */
    @PostMapping("/session")
    public ResponseEntity<SessionInfo> createSession() {
        String sessionId = chatService.createSession();
        return ResponseEntity.ok(new SessionInfo(sessionId));
    }
    
    /**
     * Get workflow progress for a course.
     */
    @GetMapping("/workflow/{courseId}")
    public ResponseEntity<Map<String, Object>> getWorkflowProgress(@PathVariable String courseId) {
        Map<String, Object> progress = courseService.getWorkflowProgress(courseId);
        if (progress.containsKey("error")) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(progress);
    }
    
    /**
     * List all courses.
     */
    @GetMapping("/courses")
    public ResponseEntity<List<CourseInfo>> listCourses() {
        List<CourseInfo> courses = courseService.listCourses().stream()
            .map(c -> new CourseInfo(c.getId(), c.getName(), c.getLocation(),
                c.getWorkflowState().getCurrentPhase().getName()))
            .toList();
        return ResponseEntity.ok(courses);
    }
    
    public record CourseInfo(String id, String name, String location, String currentPhase) {}
    
    private ToolHierarchy buildToolHierarchy(com.coursebuilder.tool.Tool tool) {
        List<ToolHierarchy> children = List.of();
        
        if (tool instanceof com.coursebuilder.tool.MatryoshkaTool mt) {
            children = mt.getNestedTools().stream()
                .map(this::buildToolHierarchy)
                .toList();
        }
        
        return new ToolHierarchy(tool.getName(), tool.getDescription(), tool.isMatryoshka(), children);
    }
    
    // DTOs
    
    public record ChatRequest(String sessionId, String message) {}
    
    public record ChatResponse(
        String message,
        List<ToolInvocationDto> toolInvocations,
        boolean requiresFollowUp,
        String suggestedNextStep
    ) {}
    
    public record ToolInvocationDto(
        String toolName,
        Map<String, Object> input,
        Map<String, Object> output,
        boolean success
    ) {}
    
    public record AgentInfo(String name, String description, List<String> capabilities) {}
    
    public record ToolInfo(String name, String description, boolean isMatryoshka) {}
    
    public record ToolHierarchy(String name, String description, boolean isMatryoshka, List<ToolHierarchy> children) {}
    
    public record MessageDto(String role, String content) {}
    
    public record SessionInfo(String sessionId) {}
}
