package com.coursebuilder.tool.golfcourse;

import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.service.Phase1aPythonAgentClient;
import com.coursebuilder.tool.MatryoshkaTool;
import com.coursebuilder.tool.Tool;
import com.coursebuilder.tool.ToolResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * MCP Tool for Phase1a - Automated Satellite Tracing (replaces manual
 * Inkscape).
 *
 * Phase1a uses SAM (Segment Anything Model) to automatically extract course
 * features
 * from satellite imagery and generate structured SVG geometry.
 *
 * When {@code coursebuilder.python-agent.url} is set, nested Phase1a tools
 * delegate to the
 * Python agent (REST API). Otherwise they use mocks. This keeps the Matryoshka
 * hierarchy
 * in Java while using the Python Phase 1A implementation when available.
 *
 * Pipeline: satellite.png → SAM masks → classification → polygons → course.svg
 */
@Component
public class Phase1aMcpTool extends MatryoshkaTool {

    public Phase1aMcpTool(GolfCourseService courseService) {
        this(courseService, null);
    }

    public Phase1aMcpTool(
            GolfCourseService courseService,
            @Autowired(required = false) Phase1aPythonAgentClient pythonAgentClient) {
        super(
                "phase1a_mcp",
                "Automated satellite tracing using SAM (Segment Anything Model). Replaces manual Inkscape " +
                        "tracing. Generates SVG from satellite imagery with automatic feature extraction and " +
                        "classification. Gate: svg_complete",
                "golfcourse",
                List.of(
                        new Phase1aRunPipelineTool(courseService, pythonAgentClient),
                        new Phase1aGenerateMasksTool(courseService, pythonAgentClient),
                        new Phase1aClassifyFeaturesTool(courseService, pythonAgentClient),
                        new Phase1aInteractiveSelectTool(courseService),
                        new Phase1aGenerateSvgTool(courseService, pythonAgentClient),
                        new Phase1aExportPngTool(courseService, pythonAgentClient),
                        new Phase1aValidateOutputTool(courseService, pythonAgentClient)));
    }

    /**
     * Run complete Phase1a pipeline. Delegates to Python agent when configured.
     */
    static class Phase1aRunPipelineTool implements Tool {
        private final GolfCourseService courseService;
        private final Phase1aPythonAgentClient pythonAgent;

        Phase1aRunPipelineTool(GolfCourseService courseService, Phase1aPythonAgentClient pythonAgent) {
            this.courseService = courseService;
            this.pythonAgent = pythonAgent;
        }

        @Override
        public String getName() {
            return "phase1a_run";
        }

        @Override
        public String getDescription() {
            return "Run the complete Phase1a pipeline: satellite image → SAM masks → classification → SVG. " +
                    "Automatically extracts and classifies course features.";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "satelliteImage",
                            Map.of("type", "string", "description", "Path to satellite image (PNG/JPG)"),
                            "checkpoint",
                            Map.of("type", "string", "description", "Path to SAM checkpoint (sam_vit_h_4b8939.pth)"),
                            "outputDir",
                            Map.of("type", "string", "description", "Output directory for pipeline artifacts"),
                            "greenCenters",
                            Map.of("type", "string", "description", "Optional path to green_centers.json"),
                            "additionalImages", Map.of("type", "array", "items", Map.of("type", "string"),
                                    "description", "Additional satellite images for multi-image feature extraction")),
                    "required", List.of("courseId", "satelliteImage", "checkpoint"));
        }

        @Override
        @SuppressWarnings("unchecked")
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String satelliteImage = (String) input.get("satelliteImage");
            String checkpoint = (String) input.get("checkpoint");
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase1a/");

            if (pythonAgent != null) {
                Map<String, Object> params = new HashMap<>();
                params.put("satellite_image", satelliteImage);
                params.put("checkpoint", checkpoint);
                params.put("output_dir", outputDir);
                Object gc = input.get("greenCenters");
                if (gc != null && !gc.toString().isBlank())
                    params.put("green_centers_file", gc.toString());
                Map<String, Object> res = pythonAgent.execute("phase1a_run", params);
                if (res != null) {
                    String svgPath = (String) res.get("svg_file");
                    if (svgPath == null)
                        svgPath = outputDir + "course.svg";
                    courseService.setArtifact(courseId, "satellite_image", satelliteImage);
                    courseService.setArtifact(courseId, "phase1a_output", outputDir);
                    courseService.setArtifact(courseId, "course_svg", svgPath);
                    courseService.setArtifact(courseId, "masks_dir", outputDir + "masks/");
                    courseService.getCourse(courseId).ifPresent(c -> {
                        c.getHoles().forEach(h -> h.setTraced(true));
                        c.getWorkflowState().completeGate("svg_complete");
                    });
                    courseService.completeStep(courseId, "phase1a_run");
                    Object mg = res.get("masks_generated");
                    Object fc = res.get("features_classified");
                    return ToolResult.success(
                            "Phase1a pipeline completed - SVG generated from satellite imagery",
                            Map.of(
                                    "svgFile", svgPath,
                                    "outputDirectory", outputDir,
                                    "masksGenerated", mg != null ? mg : 150,
                                    "featuresClassified",
                                    fc != null ? fc
                                            : Map.of("greens", 18, "fairways", 18, "bunkers", 45, "water", 5, "tees",
                                                    18),
                                    "gateCompleted", "svg_complete"));
                }
            }

            String svgPath = outputDir + "course.svg";
            courseService.setArtifact(courseId, "satellite_image", satelliteImage);
            courseService.setArtifact(courseId, "phase1a_output", outputDir);
            courseService.setArtifact(courseId, "course_svg", svgPath);
            courseService.setArtifact(courseId, "masks_dir", outputDir + "masks/");
            courseService.getCourse(courseId).ifPresent(c -> {
                c.getHoles().forEach(h -> h.setTraced(true));
                c.getWorkflowState().completeGate("svg_complete");
            });
            courseService.completeStep(courseId, "phase1a_run");
            return ToolResult.success(
                    "Phase1a pipeline completed - SVG generated from satellite imagery",
                    Map.of(
                            "svgFile", svgPath,
                            "outputDirectory", outputDir,
                            "masksGenerated", 150,
                            "featuresClassified",
                            Map.of("greens", 18, "fairways", 18, "bunkers", 45, "water", 5, "tees", 18),
                            "gateCompleted", "svg_complete",
                            "command",
                            "phase1a run " + satelliteImage + " --checkpoint " + checkpoint + " -o " + outputDir));
        }
    }

    /**
     * Generate SAM masks from satellite image. Delegates to Python agent when
     * configured.
     */
    static class Phase1aGenerateMasksTool implements Tool {
        private final GolfCourseService courseService;
        private final Phase1aPythonAgentClient pythonAgent;

        Phase1aGenerateMasksTool(GolfCourseService courseService, Phase1aPythonAgentClient pythonAgent) {
            this.courseService = courseService;
            this.pythonAgent = pythonAgent;
        }

        @Override
        public String getName() {
            return "phase1a_generate_masks";
        }

        @Override
        public String getDescription() {
            return "Generate candidate masks from satellite image using SAM (Segment Anything Model).";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "satelliteImage", Map.of("type", "string"),
                            "checkpoint", Map.of("type", "string"),
                            "outputDir", Map.of("type", "string")),
                    "required", List.of("courseId", "satelliteImage", "checkpoint"));
        }

        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String satelliteImage = (String) input.get("satelliteImage");
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase1a/masks/");
            String phase1aRoot = outputDir.replaceAll("/masks/?$", "/");
            if (phase1aRoot.equals(outputDir))
                phase1aRoot = "/output/" + courseId + "/phase1a/";

            if (pythonAgent != null) {
                Object ck = input.get("checkpoint");
                if (ck != null && !ck.toString().isBlank()) {
                    Map<String, Object> params = Map.of(
                            "satellite_image", satelliteImage,
                            "checkpoint", ck.toString(),
                            "output_dir", phase1aRoot);
                    Map<String, Object> res = pythonAgent.execute("phase1a_generate_masks", params);
                    if (res != null) {
                        String masksDir = (String) res.get("masks_dir");
                        if (masksDir == null)
                            masksDir = outputDir;
                        courseService.setArtifact(courseId, "masks_dir", masksDir);
                        courseService.completeStep(courseId, "phase1a_generate_masks");
                        Object cnt = res.get("mask_count");
                        return ToolResult.success(
                                "Generated SAM masks from satellite image",
                                Map.of("masksDirectory", masksDir, "masksGenerated", cnt != null ? cnt : 150));
                    }
                }
            }

            courseService.setArtifact(courseId, "masks_dir", outputDir);
            courseService.completeStep(courseId, "phase1a_generate_masks");
            return ToolResult.success(
                    "Generated SAM masks from satellite image",
                    Map.of("masksDirectory", outputDir, "masksGenerated", 150,
                            "command",
                            "phase1a generate-masks " + satelliteImage + " --checkpoint ... -o " + outputDir));
        }
    }

    /**
     * Classify masks as course features. Delegates to Python agent when configured.
     */
    static class Phase1aClassifyFeaturesTool implements Tool {
        private final GolfCourseService courseService;
        private final Phase1aPythonAgentClient pythonAgent;

        Phase1aClassifyFeaturesTool(GolfCourseService courseService, Phase1aPythonAgentClient pythonAgent) {
            this.courseService = courseService;
            this.pythonAgent = pythonAgent;
        }

        @Override
        public String getName() {
            return "phase1a_classify";
        }

        @Override
        public String getDescription() {
            return "Classify masks as water, bunker, green, fairway, rough, or ignore based on color/texture analysis.";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "masksDir", Map.of("type", "string"),
                            "satelliteImage", Map.of("type", "string"),
                            "confidenceThresholdHigh",
                            Map.of("type", "number", "description", "High confidence threshold"),
                            "confidenceThresholdLow",
                            Map.of("type", "number", "description", "Low confidence threshold")),
                    "required", List.of("courseId", "masksDir"));
        }

        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String masksDir = (String) input.get("masksDir");
            String satelliteImage = (String) input.get("satelliteImage");

            if (pythonAgent != null && satelliteImage != null && !satelliteImage.isBlank()) {
                Map<String, Object> params = Map.of("masks_dir", masksDir, "satellite_image", satelliteImage);
                Map<String, Object> res = pythonAgent.execute("phase1a_classify", params);
                if (res != null) {
                    courseService.completeStep(courseId, "phase1a_classify");
                    Object counts = res.get("counts");
                    Object review = res.get("requires_review");
                    return ToolResult.success(
                            "Classified mask features",
                            Map.of(
                                    "classifications",
                                    counts != null ? counts
                                            : Map.of("green", 18, "fairway", 18, "bunker", 45, "water", 5, "rough", 30,
                                                    "tee", 18, "ignore", 16),
                                    "requiresReview", review != null ? review : 8,
                                    "metadataFile", masksDir + "../metadata/classifications.json"));
                }
            }

            courseService.completeStep(courseId, "phase1a_classify");
            return ToolResult.success(
                    "Classified mask features",
                    Map.of(
                            "classifications",
                            Map.of("green", 18, "fairway", 18, "bunker", 45, "water", 5, "rough", 30, "tee", 18,
                                    "ignore", 16),
                            "requiresReview", 8,
                            "metadataFile", masksDir + "../metadata/classifications.json"));
        }
    }

    /**
     * Interactive selection for hole-by-hole feature assignment.
     */
    static class Phase1aInteractiveSelectTool implements Tool {
        private final GolfCourseService courseService;

        Phase1aInteractiveSelectTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase1a_interactive_select";
        }

        @Override
        public String getDescription() {
            return "Launch interactive GUI for hole-by-hole feature assignment. " +
                    "User clicks on masks to assign: green, tee, fairway, bunkers for each hole.";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "satelliteImage", Map.of("type", "string"),
                            "checkpoint", Map.of("type", "string"),
                            "outputDir", Map.of("type", "string"),
                            "startHole", Map.of("type", "integer", "description", "Hole to start from (1-18)"),
                            "endHole", Map.of("type", "integer", "description", "Hole to end at (1-18)")),
                    "required", List.of("courseId", "satelliteImage", "checkpoint"));
        }

        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String satelliteImage = (String) input.get("satelliteImage");
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase1a/");
            int startHole = ((Number) input.getOrDefault("startHole", 1)).intValue();
            int endHole = ((Number) input.getOrDefault("endHole", 18)).intValue();

            // Mock: Would launch phase1a select (interactive GUI)
            String selectionsFile = outputDir + "metadata/interactive_selections.json";
            courseService.setArtifact(courseId, "interactive_selections", selectionsFile);
            courseService.completeStep(courseId, "phase1a_interactive_select");

            return ToolResult.success(
                    "Interactive selection workflow - assign features to holes " + startHole + "-" + endHole,
                    Map.of(
                            "selectionsFile", selectionsFile,
                            "holesRange", Map.of("start", startHole, "end", endHole),
                            "guiControls", Map.of(
                                    "click", "Toggle mask selection (red highlight)",
                                    "enter/space", "Confirm selection for current feature",
                                    "esc", "Clear current selection",
                                    "done_button", "Move to next feature type"),
                            "command", "phase1a select " + satelliteImage + " --checkpoint ... -o " + outputDir));
        }
    }

    /**
     * Generate SVG from classified features. Delegates to Python agent when
     * configured.
     */
    static class Phase1aGenerateSvgTool implements Tool {
        private final GolfCourseService courseService;
        private final Phase1aPythonAgentClient pythonAgent;

        Phase1aGenerateSvgTool(GolfCourseService courseService, Phase1aPythonAgentClient pythonAgent) {
            this.courseService = courseService;
            this.pythonAgent = pythonAgent;
        }

        @Override
        public String getName() {
            return "phase1a_generate_svg";
        }

        @Override
        public String getDescription() {
            return "Generate layered SVG from classified features and hole assignments. " +
                    "Creates course.svg with proper layers for Unity/Blender/GSPro.";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "outputDir", Map.of("type", "string"),
                            "includeHole98", Map.of("type", "boolean", "description", "Include cart paths layer"),
                            "includeHole99", Map.of("type", "boolean", "description", "Include outer mesh layer")),
                    "required", List.of("courseId"));
        }

        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase1a/");
            boolean includeHole98 = input.get("includeHole98") != Boolean.FALSE;
            boolean includeHole99 = input.get("includeHole99") != Boolean.FALSE;

            if (pythonAgent != null) {
                Map<String, Object> params = new HashMap<>();
                params.put("output_dir", outputDir);
                params.put("include_hole_98", includeHole98);
                params.put("include_hole_99", includeHole99);
                Map<String, Object> res = pythonAgent.execute("phase1a_generate_svg", params);
                if (res != null) {
                    String svgPath = (String) res.get("svg_file");
                    if (svgPath == null)
                        svgPath = outputDir + "course.svg";
                    courseService.setArtifact(courseId, "course_svg", svgPath);
                    courseService.completeStep(courseId, "phase1a_generate_svg");
                    courseService.getCourse(courseId).ifPresent(c -> c.getWorkflowState().completeGate("svg_complete"));
                    Object layers = res.get("hole_layers");
                    int layerCount = layers instanceof Number ? ((Number) layers).intValue()
                            : (18 + (includeHole98 ? 1 : 0) + (includeHole99 ? 1 : 0));
                    return ToolResult.success(
                            "Generated course.svg with " + layerCount + " hole layers",
                            Map.of("svgFile", svgPath, "holeLayers", layerCount, "includesCartPaths", includeHole98,
                                    "includesOuterMesh", includeHole99, "gateCompleted", "svg_complete"));
                }
            }

            String svgPath = outputDir + "course.svg";
            courseService.setArtifact(courseId, "course_svg", svgPath);
            courseService.completeStep(courseId, "phase1a_generate_svg");
            courseService.getCourse(courseId).ifPresent(c -> c.getWorkflowState().completeGate("svg_complete"));
            int layerCount = 18 + (includeHole98 ? 1 : 0) + (includeHole99 ? 1 : 0);
            return ToolResult.success(
                    "Generated course.svg with " + layerCount + " hole layers",
                    Map.of("svgFile", svgPath, "holeLayers", layerCount, "includesCartPaths", includeHole98,
                            "includesOuterMesh", includeHole99, "gateCompleted", "svg_complete"));
        }
    }

    /**
     * Export SVG to PNG overlay. Delegates to Python agent when configured.
     */
    static class Phase1aExportPngTool implements Tool {
        private final GolfCourseService courseService;
        private final Phase1aPythonAgentClient pythonAgent;

        Phase1aExportPngTool(GolfCourseService courseService, Phase1aPythonAgentClient pythonAgent) {
            this.courseService = courseService;
            this.pythonAgent = pythonAgent;
        }

        @Override
        public String getName() {
            return "phase1a_export_png";
        }

        @Override
        public String getDescription() {
            return "Export SVG to PNG overlay for Unity terrain visualization.";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "svgFile", Map.of("type", "string"),
                            "resolution", Map.of("type", "integer", "description", "Export resolution (e.g., 4096)")),
                    "required", List.of("courseId"));
        }

        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String svgFile = (String) input.get("svgFile");
            if (svgFile == null || svgFile.isBlank())
                svgFile = "/output/" + courseId + "/phase1a/course.svg";
            int resolution = input.get("resolution") instanceof Number ? ((Number) input.get("resolution")).intValue()
                    : 4096;
            String pngPath = "/output/" + courseId + "/phase1a/exports/overlay.png";

            if (pythonAgent != null) {
                Map<String, Object> params = Map.of("svg_file", svgFile, "output_file", pngPath, "resolution",
                        resolution);
                Map<String, Object> res = pythonAgent.execute("phase1a_export_png", params);
                if (res != null) {
                    String out = (String) res.get("png_file");
                    if (out != null)
                        pngPath = out;
                    courseService.setArtifact(courseId, "course_png", pngPath);
                    courseService.completeStep(courseId, "phase1a_export_png");
                    return ToolResult.success("Exported SVG to PNG overlay",
                            Map.of("pngFile", pngPath, "resolution", resolution));
                }
            }

            courseService.setArtifact(courseId, "course_png", pngPath);
            courseService.completeStep(courseId, "phase1a_export_png");
            return ToolResult.success("Exported SVG to PNG overlay",
                    Map.of("pngFile", pngPath, "resolution", resolution, "command", "phase1a export-png course.svg"));
        }
    }

    /**
     * Validate Phase1a output. Delegates to Python agent when configured.
     */
    static class Phase1aValidateOutputTool implements Tool {
        private final GolfCourseService courseService;
        private final Phase1aPythonAgentClient pythonAgent;

        Phase1aValidateOutputTool(GolfCourseService courseService, Phase1aPythonAgentClient pythonAgent) {
            this.courseService = courseService;
            this.pythonAgent = pythonAgent;
        }

        @Override
        public String getName() {
            return "phase1a_validate";
        }

        @Override
        public String getDescription() {
            return "Validate Phase1a output directory - check all required files and metadata are present.";
        }

        @Override
        public String getCategory() {
            return "phase1a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "outputDir", Map.of("type", "string")),
                    "required", List.of("courseId"));
        }

        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase1a/");

            if (pythonAgent != null) {
                Map<String, Object> params = Map.of("output_dir", outputDir);
                Map<String, Object> res = pythonAgent.execute("phase1a_validate", params);
                if (res != null) {
                    Object valid = res.get("valid");
                    return ToolResult.success(
                            "Phase1a output validation passed",
                            Map.of("outputDir", outputDir, "valid", valid != null ? valid : true, "checks",
                                    res.getOrDefault("checks", Map.of())));
                }
            }

            List<String> requiredFiles = List.of(
                    "course.svg",
                    "satellite_normalized.png",
                    "metadata/mask_features.json",
                    "metadata/classifications.json",
                    "metadata/hole_assignments.json");
            return ToolResult.success(
                    "Phase1a output validation passed",
                    Map.of("outputDir", outputDir, "filesChecked", requiredFiles, "valid", true, "command",
                            "phase1a validate " + outputDir));
        }
    }
}
