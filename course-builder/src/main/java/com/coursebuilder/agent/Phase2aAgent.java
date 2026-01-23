package com.coursebuilder.agent;

import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.ToolRegistry;
import com.coursebuilder.tool.ToolResult;
import com.coursebuilder.tool.golfcourse.Phase2aMcpTool;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Agent specialized in Phase2a - Automated Satellite Tracing.
 * 
 * This agent handles:
 * - SAM mask generation from satellite imagery
 * - Feature classification
 * - Interactive selection workflow
 * - SVG generation
 */
@Component
public class Phase2aAgent extends AbstractAgent {

    private final GolfCourseService courseService;

    public Phase2aAgent(
            ToolRegistry toolRegistry,
            Phase2aMcpTool phase2aMcp,
            GolfCourseService courseService) {
        super(
                toolRegistry,
                List.of(phase2aMcp),
                List.of(
                        ".*phase2a.*",
                        ".*\\bsam\\b.*",
                        ".*satellite.*image.*using.*",
                        ".*generate.*mask.*",
                        ".*mask.*from.*satellite.*",
                        ".*trace.*satellite.*",
                        ".*classify.*feature.*",
                        ".*feature.*classif.*",
                        ".*interactive.*select.*phase2a.*",
                        ".*segment.*anything.*",
                        ".*run.*phase2a.*"));
        this.courseService = courseService;
    }

    @Override
    public String getName() {
        return "Phase2aAgent";
    }

    @Override
    public String getDescription() {
        return "Specialized in Phase2a automated satellite tracing using SAM (Segment Anything Model). " +
                "Handles mask generation, feature classification, interactive selection, and SVG generation.";
    }

    @Override
    public AgentResponse process(AgentContext context, String userMessage) {
        log.info("Phase2aAgent processing: {}", userMessage);
        context.addMessage(AgentContext.Message.user(userMessage));

        String lowerMessage = userMessage.toLowerCase();

        if (lowerMessage.contains("run") || lowerMessage.contains("pipeline") ||
                lowerMessage.contains("full")) {
            return handleRunPipeline(context, userMessage);
        }

        if (lowerMessage.contains("mask") || lowerMessage.contains("generate")) {
            return handleGenerateMasks(context, userMessage);
        }

        if (lowerMessage.contains("classify")) {
            return handleClassify(context, userMessage);
        }

        if (lowerMessage.contains("interactive") || lowerMessage.contains("select")) {
            return handleInteractiveSelect(context, userMessage);
        }

        if (lowerMessage.contains("svg")) {
            return handleGenerateSvg(context, userMessage);
        }

        if (lowerMessage.contains("validate")) {
            return handleValidate(context, userMessage);
        }

        // Default: show Phase2a capabilities
        return AgentResponse.withFollowUp(
                "# Phase2a - Automated Satellite Tracing\n\n" +
                        "I can help with SAM-based course feature extraction:\n\n" +
                        "- **Run full pipeline**: `phase2a run satellite.png`\n" +
                        "- **Generate masks**: Extract candidate masks from satellite image\n" +
                        "- **Classify features**: Identify greens, fairways, bunkers, water\n" +
                        "- **Interactive selection**: GUI for hole-by-hole feature assignment\n" +
                        "- **Generate SVG**: Create layered course.svg\n" +
                        "- **Validate output**: Check generated files\n\n" +
                        "What would you like to do?",
                "Tell me what Phase2a operation you need");
    }

    private AgentResponse handleRunPipeline(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null) {
            courseId = "demo-course";
        }

        ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_run",
                "parameters", Map.of(
                        "courseId", courseId,
                        "satelliteImage", extractPath(userMessage, "/input/satellite.png"),
                        "checkpoint", "models/sam_vit_h_4b8939.pth")),
                context);

        return AgentResponse.withTools(
                "Running complete Phase2a pipeline...\n\n" + result.message() + "\n\n" +
                        "**Features Classified**:\n" + formatMap(result.data().get("featuresClassified")) + "\n\n" +
                        "SVG output: " + result.data().get("svgFile"),
                List.of(AgentResponse.ToolInvocation.of("phase2a_run", Map.of(), result.data())));
    }

    private AgentResponse handleGenerateMasks(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null)
            courseId = "demo-course";

        ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_generate_masks",
                "parameters", Map.of(
                        "courseId", courseId,
                        "satelliteImage", extractPath(userMessage, "/input/satellite.png"),
                        "checkpoint", "models/sam_vit_h_4b8939.pth")),
                context);

        return AgentResponse.withTools(
                "Generated SAM masks from satellite image.\n\n" + result.message() + "\n\n" +
                        "Masks saved to: " + result.data().get("masksDirectory") + "\n" +
                        "Total masks: " + result.data().get("masksGenerated") + "\n\n" +
                        "Next step: Classify these masks into course features.",
                List.of(AgentResponse.ToolInvocation.of("phase2a_generate_masks", Map.of(), result.data())));
    }

    private AgentResponse handleClassify(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null)
            courseId = "demo-course";

        ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_classify",
                "parameters", Map.of(
                        "courseId", courseId,
                        "masksDir", "/output/" + courseId + "/phase2a/masks/")),
                context);

        return AgentResponse.withTools(
                "Classified mask features.\n\n" + result.message() + "\n\n" +
                        "**Classifications**:\n" + formatMap(result.data().get("classifications")) + "\n\n" +
                        "Masks requiring review: " + result.data().get("requiresReview"),
                List.of(AgentResponse.ToolInvocation.of("phase2a_classify", Map.of(), result.data())));
    }

    private AgentResponse handleInteractiveSelect(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null)
            courseId = "demo-course";

        ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_interactive_select",
                "parameters", Map.of(
                        "courseId", courseId,
                        "satelliteImage", extractPath(userMessage, "/input/satellite.png"),
                        "checkpoint", "models/sam_vit_h_4b8939.pth")),
                context);

        @SuppressWarnings("unchecked")
        Map<String, String> controls = (Map<String, String>) result.data().get("guiControls");

        StringBuilder controlsStr = new StringBuilder();
        controls.forEach((k, v) -> controlsStr.append("- **").append(k).append("**: ").append(v).append("\n"));

        return AgentResponse.withTools(
                "Launching Interactive Selection Workflow\n\n" +
                        "This will open a GUI window for hole-by-hole feature assignment.\n\n" +
                        "**GUI Controls**:\n" + controlsStr + "\n" +
                        "The workflow will guide you through:\n" +
                        "1. Select green for hole 1\n" +
                        "2. Select tee for hole 1\n" +
                        "3. Select fairway for hole 1\n" +
                        "4. Select bunkers for hole 1\n" +
                        "5. Repeat for holes 2-18",
                List.of(AgentResponse.ToolInvocation.of("phase2a_interactive_select", Map.of(), result.data())));
    }

    private AgentResponse handleGenerateSvg(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null)
            courseId = "demo-course";

        ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_generate_svg",
                "parameters", Map.of(
                        "courseId", courseId,
                        "includeHole98", true,
                        "includeHole99", true)),
                context);

        return AgentResponse.withTools(
                "Generated course.svg\n\n" + result.message() + "\n\n" +
                        "SVG file: " + result.data().get("svgFile") + "\n" +
                        "Hole layers: " + result.data().get("holeLayers") + "\n" +
                        "Includes cart paths (Hole98): " + result.data().get("includesCartPaths") + "\n" +
                        "Includes outer mesh (Hole99): " + result.data().get("includesOuterMesh"),
                List.of(AgentResponse.ToolInvocation.of("phase2a_generate_svg", Map.of(), result.data())));
    }

    private AgentResponse handleValidate(AgentContext context, String userMessage) {
        String courseId = context.getCurrentCourseId();
        if (courseId == null)
            courseId = "demo-course";

        ToolResult result = executeTool("phase2a_mcp", Map.of(
                "operation", "phase2a_validate",
                "parameters", Map.of("courseId", courseId)), context);

        boolean isValid = (Boolean) result.data().get("valid");
        String validationStatus = isValid ? "✅ All files present and valid" : "❌ Validation failed";

        return AgentResponse.withTools(
                "Phase2a Output Validation\n\n" + validationStatus +
                        "\n\nFiles checked: " + result.data().get("filesChecked"),
                List.of(AgentResponse.ToolInvocation.of("phase2a_validate", Map.of(), result.data())));
    }

    private String extractPath(String message, String defaultPath) {
        // Simple path extraction - look for file paths
        String[] words = message.split("\\s+");
        for (String word : words) {
            if (word.contains("/") || word.endsWith(".png") || word.endsWith(".jpg")) {
                return word;
            }
        }
        return defaultPath;
    }

    private String formatMap(Object obj) {
        if (obj instanceof Map) {
            StringBuilder sb = new StringBuilder();
            ((Map<?, ?>) obj).forEach((k, v) -> sb.append("  - ").append(k).append(": ").append(v).append("\n"));
            return sb.toString();
        }
        return String.valueOf(obj);
    }
}
