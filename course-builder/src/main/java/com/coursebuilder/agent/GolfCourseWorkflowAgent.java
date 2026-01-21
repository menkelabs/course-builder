package com.coursebuilder.agent;

import com.coursebuilder.model.GolfCourse;
import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.ToolRegistry;
import com.coursebuilder.tool.ToolResult;
import com.coursebuilder.tool.golfcourse.*;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Main agent for orchestrating the "None to Done" golf course building workflow.
 * 
 * This agent coordinates all 6 phases of the workflow:
 * 1. Terrain Creation (LIDAR)
 * 2. Course Tracing (Phase2a - SAM-based)
 * 3. Terrain Refinement (Unity)
 * 4. SVG Conversion
 * 5. Blender Processing
 * 6. Unity Final Assembly
 * 
 * The agent tracks workflow state and guides users through each phase.
 */
@Component
public class GolfCourseWorkflowAgent extends AbstractAgent {
    
    private final GolfCourseService courseService;
    
    public GolfCourseWorkflowAgent(
            ToolRegistry toolRegistry,
            GolfCourseBuilderMatryoshkaTool courseBuilderTool,
            GolfCourseService courseService
    ) {
        super(
            toolRegistry,
            List.of(courseBuilderTool),
            List.of(
                ".*golf.*course.*",
                ".*create.*course.*",
                ".*build.*course.*",
                ".*none.*done.*",
                ".*workflow.*",
                ".*gspro.*",
                ".*terrain.*",
                ".*lidar.*",
                ".*phase.*"
            )
        );
        this.courseService = courseService;
    }
    
    @Override
    public String getName() {
        return "GolfCourseWorkflowAgent";
    }
    
    @Override
    public String getDescription() {
        return "Orchestrates the complete 'None to Done' golf course creation workflow for GSPro. " +
               "Guides you through all 6 phases from LIDAR terrain to final asset bundle.";
    }
    
    @Override
    public AgentResponse process(AgentContext context, String userMessage) {
        log.info("GolfCourseWorkflowAgent processing: {}", userMessage);
        context.addMessage(AgentContext.Message.user(userMessage));
        
        String lowerMessage = userMessage.toLowerCase();
        
        // Check for workflow status request
        if (lowerMessage.contains("status") || lowerMessage.contains("progress")) {
            return handleStatusRequest(context);
        }
        
        // Check for starting a new course
        if (lowerMessage.contains("new course") || lowerMessage.contains("create course") || 
            lowerMessage.contains("start")) {
            return handleNewCourse(context, userMessage);
        }
        
        // Check for phase-specific requests
        if (lowerMessage.contains("lidar") || lowerMessage.contains("terrain creation") || 
            lowerMessage.contains("phase 1")) {
            return handlePhase1(context, userMessage);
        }
        
        if (lowerMessage.contains("phase2a") || lowerMessage.contains("sam") || 
            lowerMessage.contains("satellite") || lowerMessage.contains("trace") ||
            lowerMessage.contains("phase 2")) {
            return handlePhase2(context, userMessage);
        }
        
        if (lowerMessage.contains("unity terrain") || lowerMessage.contains("contour") ||
            lowerMessage.contains("phase 3")) {
            return handlePhase3(context, userMessage);
        }
        
        if (lowerMessage.contains("svg convert") || lowerMessage.contains("gspro") ||
            lowerMessage.contains("phase 4")) {
            return handlePhase4(context, userMessage);
        }
        
        if (lowerMessage.contains("blender") || lowerMessage.contains("mesh") || 
            lowerMessage.contains("fbx") || lowerMessage.contains("phase 5")) {
            return handlePhase5(context, userMessage);
        }
        
        if (lowerMessage.contains("assembly") || lowerMessage.contains("material") || 
            lowerMessage.contains("vegetation") || lowerMessage.contains("asset bundle") ||
            lowerMessage.contains("phase 6")) {
            return handlePhase6(context, userMessage);
        }
        
        // Default: show workflow overview
        return showWorkflowOverview(context);
    }
    
    private AgentResponse showWorkflowOverview(AgentContext context) {
        String courseId = context.getCurrentCourseId();
        
        StringBuilder response = new StringBuilder();
        response.append("# Golf Course Builder - 'None to Done' Workflow\n\n");
        response.append("I can help you build a complete GSPro golf course through these 6 phases:\n\n");
        response.append("**Phase 1: Terrain Creation** (LIDAR)\n");
        response.append("  - Download LIDAR data and create heightmap\n");
        response.append("  - Set up Unity terrain with dimensions\n\n");
        response.append("**Phase 2: Course Tracing** (Phase2a - Automated SAM)\n");
        response.append("  - Generate masks from satellite imagery using SAM\n");
        response.append("  - Classify features (greens, fairways, bunkers, water)\n");
        response.append("  - Interactive hole-by-hole assignment\n");
        response.append("  - Generate course.svg\n\n");
        response.append("**Phase 3: Terrain Refinement** (Unity)\n");
        response.append("  - Apply PNG overlay to terrain\n");
        response.append("  - Adjust contours\n");
        response.append("  - Export Terrain.obj\n\n");
        response.append("**Phase 4: SVG Conversion**\n");
        response.append("  - Run GSProSVGConvert.exe\n\n");
        response.append("**Phase 5: Blender Processing**\n");
        response.append("  - Import SVG and terrain\n");
        response.append("  - Convert and cut meshes\n");
        response.append("  - Add peripherals (curbs, bulkheads, water planes)\n");
        response.append("  - Export FBX files\n\n");
        response.append("**Phase 6: Unity Assembly**\n");
        response.append("  - Import FBX, add colliders\n");
        response.append("  - Apply materials, place vegetation\n");
        response.append("  - Build asset bundle\n\n");
        
        if (courseId != null) {
            var progress = courseService.getWorkflowProgress(courseId);
            response.append("---\n**Current Course**: ").append(progress.get("courseName")).append("\n");
            response.append("**Current Phase**: ").append(progress.get("currentPhase")).append("\n");
            response.append("**Completed Steps**: ").append(progress.get("completedSteps")).append("\n");
        } else {
            response.append("---\nTo begin, say **'create new course'** with the course name and location.");
        }
        
        return AgentResponse.simple(response.toString());
    }
    
    private AgentResponse handleStatusRequest(AgentContext context) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("No course currently active. Say 'create new course' to start.");
        }
        
        var progress = courseService.getWorkflowProgress(courseId);
        
        StringBuilder response = new StringBuilder();
        response.append("# Workflow Status\n\n");
        response.append("**Course**: ").append(progress.get("courseName")).append("\n");
        response.append("**ID**: ").append(progress.get("courseId")).append("\n");
        response.append("**Current Phase**: ").append(progress.get("currentPhase"));
        response.append(" (").append(progress.get("phaseNumber")).append("/6)\n");
        response.append("**Completed Steps**: ").append(progress.get("completedSteps")).append("\n");
        response.append("**Holes Traced**: ").append(progress.get("holesTraced")).append("/");
        response.append(progress.get("totalHoles")).append("\n\n");
        
        @SuppressWarnings("unchecked")
        Map<String, String> artifacts = (Map<String, String>) progress.get("artifacts");
        if (!artifacts.isEmpty()) {
            response.append("**Generated Artifacts**:\n");
            artifacts.forEach((k, v) -> response.append("  - ").append(k).append(": ").append(v).append("\n"));
        }
        
        return AgentResponse.simple(response.toString());
    }
    
    private AgentResponse handleNewCourse(AgentContext context, String userMessage) {
        // Extract course name from message (simple extraction)
        String courseName = extractQuoted(userMessage);
        if (courseName == null) {
            courseName = "New Golf Course";
        }
        
        GolfCourse course = courseService.createCourse(courseName, "Location TBD");
        context.setCurrentCourseId(course.getId());
        
        return AgentResponse.withFollowUp(
            "Created new course project: **" + courseName + "**\n\n" +
            "Course ID: `" + course.getId() + "`\n\n" +
            "Ready to begin Phase 1: Terrain Creation.\n\n" +
            "To proceed, I'll need:\n" +
            "1. LIDAR data source (URL or file path)\n" +
            "2. Geographic bounds (lat/lon) of the course\n" +
            "3. Unity project path\n\n" +
            "Or say 'skip to phase 2' if you have terrain ready.",
            "Provide LIDAR source and bounds"
        );
    }
    
    private AgentResponse handlePhase1(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("Please create a course first with 'create new course [name]'");
        }
        
        // Execute LIDAR to heightmap
        ToolResult result = executeTool("lidar_mcp", Map.of(
            "operation", "lidar_to_heightmap",
            "parameters", Map.of(
                "courseId", courseId,
                "lidarSource", "https://example.com/lidar/course.laz",
                "bounds", Map.of(
                    "northLat", 40.5,
                    "southLat", 40.4,
                    "eastLon", -74.3,
                    "westLon", -74.4
                ),
                "resolution", 1025
            )
        ), context);
        
        return AgentResponse.withTools(
            "Phase 1: Terrain Creation\n\n" + result.message() + "\n\n" +
            "Heightmap generated at: " + result.data().get("heightmapPath") + "\n\n" +
            "Next step: Set up Unity terrain. Should I proceed?",
            List.of(AgentResponse.ToolInvocation.of("lidar_to_heightmap", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handlePhase2(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("Please create a course first with 'create new course [name]'");
        }
        
        // Check if user wants interactive selection or full pipeline
        boolean interactive = userMessage.toLowerCase().contains("interactive") || 
                             userMessage.toLowerCase().contains("select");
        
        if (interactive) {
            ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_interactive_select",
                "parameters", Map.of(
                    "courseId", courseId,
                    "satelliteImage", "/input/satellite.png",
                    "checkpoint", "checkpoints/sam_vit_h_4b8939.pth"
                )
            ), context);
            
            return AgentResponse.withTools(
                "Phase 2: Interactive Selection Workflow\n\n" +
                "Launching GUI for hole-by-hole feature assignment.\n\n" +
                "**Controls**:\n" +
                "- Click on mask: Toggle selection\n" +
                "- Enter/Space: Confirm selection\n" +
                "- Esc: Clear selection\n" +
                "- Done button: Next feature type\n\n" +
                "The workflow will guide you through assigning greens, tees, fairways, and bunkers for each hole.",
                List.of(AgentResponse.ToolInvocation.of("phase2a_interactive_select", Map.of(), result.data()))
            );
        }
        
        // Full automated pipeline
        ToolResult result = executeTool("phase2a_mcp", Map.of(
            "operation", "phase2a_run",
            "parameters", Map.of(
                "courseId", courseId,
                "satelliteImage", "/input/satellite.png",
                "checkpoint", "checkpoints/sam_vit_h_4b8939.pth"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Phase 2: Automated SAM-based Course Tracing\n\n" + result.message() + "\n\n" +
            "SVG generated with automatic feature classification.\n\n" +
            "Features detected:\n" + result.data().get("featuresClassified") + "\n\n" +
            "Ready for Phase 3: Terrain Refinement. Proceed?",
            List.of(AgentResponse.ToolInvocation.of("phase2a_run", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handlePhase3(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("Please create a course first.");
        }
        
        ToolResult result = executeTool("unity_terrain_mcp", Map.of(
            "operation", "unity_export_terrain",
            "parameters", Map.of(
                "courseId", courseId,
                "resolution", "half"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Phase 3: Terrain Refinement\n\n" + result.message() + "\n\n" +
            "Terrain exported as OBJ for Blender import.\n\n" +
            "Ready for Phase 4: SVG Conversion. Proceed?",
            List.of(AgentResponse.ToolInvocation.of("unity_export_terrain", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handlePhase4(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("Please create a course first.");
        }
        
        String svgFile = courseService.getCourse(courseId)
            .map(c -> c.getArtifact("course_svg"))
            .orElse("/output/" + courseId + "/course.svg");
        
        ToolResult result = executeTool("svg_convert_mcp", Map.of(
            "operation", "svg_convert",
            "parameters", Map.of(
                "courseId", courseId,
                "svgFile", svgFile
            )
        ), context);
        
        return AgentResponse.withTools(
            "Phase 4: SVG Conversion\n\n" + result.message() + "\n\n" +
            "SVG converted for Blender import.\n\n" +
            "Ready for Phase 5: Blender Processing. Proceed?",
            List.of(AgentResponse.ToolInvocation.of("svg_convert", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handlePhase5(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("Please create a course first.");
        }
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_export_fbx",
            "parameters", Map.of(
                "courseId", courseId,
                "perHole", true
            )
        ), context);
        
        return AgentResponse.withTools(
            "Phase 5: Blender Processing\n\n" + result.message() + "\n\n" +
            "FBX files exported for Unity import.\n\n" +
            "Ready for Phase 6: Unity Assembly. This is the final phase!",
            List.of(AgentResponse.ToolInvocation.of("blender_export_fbx", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handlePhase6(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            return AgentResponse.simple("Please create a course first.");
        }
        
        ToolResult result = executeTool("unity_assembly_mcp", Map.of(
            "operation", "unity_build_asset_bundle",
            "parameters", Map.of(
                "courseId", courseId,
                "platform", "Windows"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Phase 6: Unity Assembly - COMPLETE!\n\n" + result.message() + "\n\n" +
            "🎉 **Congratulations!** Your golf course is DONE!\n\n" +
            "Asset bundle: " + result.data().get("assetBundle") + "\n\n" +
            "The course is ready to be loaded in GSPro.",
            List.of(AgentResponse.ToolInvocation.of("unity_build_asset_bundle", Map.of(), result.data()))
        );
    }
    
    private String extractQuoted(String text) {
        int start = text.indexOf('"');
        if (start >= 0) {
            int end = text.indexOf('"', start + 1);
            if (end > start) {
                return text.substring(start + 1, end);
            }
        }
        // Try single quotes
        start = text.indexOf('\'');
        if (start >= 0) {
            int end = text.indexOf('\'', start + 1);
            if (end > start) {
                return text.substring(start + 1, end);
            }
        }
        return null;
    }
}
