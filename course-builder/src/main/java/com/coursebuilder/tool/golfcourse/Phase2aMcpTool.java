package com.coursebuilder.tool.golfcourse;

import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.MatryoshkaTool;
import com.coursebuilder.tool.Tool;
import com.coursebuilder.tool.ToolResult;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * MCP Tool for Phase2a - Automated Satellite Tracing (replaces manual
 * Inkscape).
 * 
 * Phase2a uses SAM (Segment Anything Model) to automatically extract course
 * features
 * from satellite imagery and generate structured SVG geometry.
 * 
 * This replaces the manual Inkscape tracing workflow with automated:
 * - Mask generation using SAM
 * - Feature classification (water, bunker, green, fairway, rough)
 * - Interactive selection workflow for hole-by-hole assignment
 * - SVG generation with proper layers
 * 
 * Pipeline: satellite.png → SAM masks → classification → polygons → course.svg
 */
@Component
public class Phase2aMcpTool extends MatryoshkaTool {

    public Phase2aMcpTool(GolfCourseService courseService) {
        super(
                "phase2a_mcp",
                "Automated satellite tracing using SAM (Segment Anything Model). Replaces manual Inkscape " +
                        "tracing. Generates SVG from satellite imagery with automatic feature extraction and " +
                        "classification. Gate: svg_complete",
                "golfcourse",
                List.of(
                        new Phase2aRunPipelineTool(courseService),
                        new Phase2aGenerateMasksTool(courseService),
                        new Phase2aClassifyFeaturesTool(courseService),
                        new Phase2aInteractiveSelectTool(courseService),
                        new Phase2aGenerateSvgTool(courseService),
                        new Phase2aExportPngTool(courseService),
                        new Phase2aValidateOutputTool(courseService)));
    }

    /**
     * Run complete Phase2a pipeline.
     */
    static class Phase2aRunPipelineTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aRunPipelineTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_run";
        }

        @Override
        public String getDescription() {
            return "Run the complete Phase2a pipeline: satellite image → SAM masks → classification → SVG. " +
                    "Automatically extracts and classifies course features.";
        }

        @Override
        public String getCategory() {
            return "phase2a";
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
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase2a/");

            // Mock: Would invoke Python phase2a CLI
            // phase2a run satellite.png --checkpoint models/sam_vit_h_4b8939.pth -o output/

            String svgPath = outputDir + "course.svg";
            String masksDir = outputDir + "masks/";
            String metadataDir = outputDir + "metadata/";

            courseService.setArtifact(courseId, "satellite_image", satelliteImage);
            courseService.setArtifact(courseId, "phase2a_output", outputDir);
            courseService.setArtifact(courseId, "course_svg", svgPath);
            courseService.setArtifact(courseId, "masks_dir", masksDir);

            // Mark all holes as traced (automated)
            courseService.getCourse(courseId).ifPresent(course -> {
                course.getHoles().forEach(hole -> hole.setTraced(true));
                course.getWorkflowState().completeGate("svg_complete");
            });

            courseService.completeStep(courseId, "phase2a_run");

            return ToolResult.success(
                    "Phase2a pipeline completed - SVG generated from satellite imagery",
                    Map.of(
                            "svgFile", svgPath,
                            "outputDirectory", outputDir,
                            "masksGenerated", 150, // Mock count
                            "featuresClassified", Map.of(
                                    "greens", 18,
                                    "fairways", 18,
                                    "bunkers", 45,
                                    "water", 5,
                                    "tees", 18),
                            "gateCompleted", "svg_complete",
                            "command",
                            "phase2a run " + satelliteImage + " --checkpoint " + checkpoint + " -o " + outputDir));
        }
    }

    /**
     * Generate SAM masks from satellite image.
     */
    static class Phase2aGenerateMasksTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aGenerateMasksTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_generate_masks";
        }

        @Override
        public String getDescription() {
            return "Generate candidate masks from satellite image using SAM (Segment Anything Model).";
        }

        @Override
        public String getCategory() {
            return "phase2a";
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
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase2a/masks/");

            // Mock: Would invoke phase2a generate-masks
            courseService.setArtifact(courseId, "masks_dir", outputDir);
            courseService.completeStep(courseId, "phase2a_generate_masks");

            return ToolResult.success(
                    "Generated SAM masks from satellite image",
                    Map.of(
                            "masksDirectory", outputDir,
                            "masksGenerated", 150,
                            "command",
                            "phase2a generate-masks " + satelliteImage + " --checkpoint ... -o " + outputDir));
        }
    }

    /**
     * Classify masks as course features.
     */
    static class Phase2aClassifyFeaturesTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aClassifyFeaturesTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_classify";
        }

        @Override
        public String getDescription() {
            return "Classify masks as water, bunker, green, fairway, rough, or ignore based on color/texture analysis.";
        }

        @Override
        public String getCategory() {
            return "phase2a";
        }

        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "courseId", Map.of("type", "string"),
                            "masksDir", Map.of("type", "string"),
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

            courseService.completeStep(courseId, "phase2a_classify");

            return ToolResult.success(
                    "Classified mask features",
                    Map.of(
                            "classifications", Map.of(
                                    "green", 18,
                                    "fairway", 18,
                                    "bunker", 45,
                                    "water", 5,
                                    "rough", 30,
                                    "tee", 18,
                                    "ignore", 16),
                            "requiresReview", 8,
                            "metadataFile", masksDir + "../metadata/classifications.json"));
        }
    }

    /**
     * Interactive selection for hole-by-hole feature assignment.
     */
    static class Phase2aInteractiveSelectTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aInteractiveSelectTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_interactive_select";
        }

        @Override
        public String getDescription() {
            return "Launch interactive GUI for hole-by-hole feature assignment. " +
                    "User clicks on masks to assign: green, tee, fairway, bunkers for each hole.";
        }

        @Override
        public String getCategory() {
            return "phase2a";
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
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase2a/");
            int startHole = ((Number) input.getOrDefault("startHole", 1)).intValue();
            int endHole = ((Number) input.getOrDefault("endHole", 18)).intValue();

            // Mock: Would launch phase2a select (interactive GUI)
            String selectionsFile = outputDir + "metadata/interactive_selections.json";
            courseService.setArtifact(courseId, "interactive_selections", selectionsFile);
            courseService.completeStep(courseId, "phase2a_interactive_select");

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
                            "command", "phase2a select " + satelliteImage + " --checkpoint ... -o " + outputDir));
        }
    }

    /**
     * Generate SVG from classified features.
     */
    static class Phase2aGenerateSvgTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aGenerateSvgTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_generate_svg";
        }

        @Override
        public String getDescription() {
            return "Generate layered SVG from classified features and hole assignments. " +
                    "Creates course.svg with proper layers for Unity/Blender/GSPro.";
        }

        @Override
        public String getCategory() {
            return "phase2a";
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
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase2a/");
            boolean includeHole98 = (Boolean) input.getOrDefault("includeHole98", true);
            boolean includeHole99 = (Boolean) input.getOrDefault("includeHole99", true);

            String svgPath = outputDir + "course.svg";

            courseService.setArtifact(courseId, "course_svg", svgPath);
            courseService.completeStep(courseId, "phase2a_generate_svg");

            // Complete gate
            courseService.getCourse(courseId)
                    .ifPresent(course -> course.getWorkflowState().completeGate("svg_complete"));

            int layerCount = 18 + (includeHole98 ? 1 : 0) + (includeHole99 ? 1 : 0);

            return ToolResult.success(
                    "Generated course.svg with " + layerCount + " hole layers",
                    Map.of(
                            "svgFile", svgPath,
                            "holeLayers", layerCount,
                            "includesCartPaths", includeHole98,
                            "includesOuterMesh", includeHole99,
                            "gateCompleted", "svg_complete"));
        }
    }

    /**
     * Export SVG to PNG overlay.
     */
    static class Phase2aExportPngTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aExportPngTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_export_png";
        }

        @Override
        public String getDescription() {
            return "Export SVG to PNG overlay for Unity terrain visualization.";
        }

        @Override
        public String getCategory() {
            return "phase2a";
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
            int resolution = ((Number) input.getOrDefault("resolution", 4096)).intValue();

            String pngPath = "/output/" + courseId + "/phase2a/exports/overlay.png";

            courseService.setArtifact(courseId, "course_png", pngPath);
            courseService.completeStep(courseId, "phase2a_export_png");

            return ToolResult.success(
                    "Exported SVG to PNG overlay",
                    Map.of(
                            "pngFile", pngPath,
                            "resolution", resolution,
                            "command", "phase2a export-png course.svg"));
        }
    }

    /**
     * Validate Phase2a output.
     */
    static class Phase2aValidateOutputTool implements Tool {
        private final GolfCourseService courseService;

        Phase2aValidateOutputTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }

        @Override
        public String getName() {
            return "phase2a_validate";
        }

        @Override
        public String getDescription() {
            return "Validate Phase2a output directory - check all required files and metadata are present.";
        }

        @Override
        public String getCategory() {
            return "phase2a";
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
            String outputDir = (String) input.getOrDefault("outputDir", "/output/" + courseId + "/phase2a/");

            // Mock validation
            List<String> requiredFiles = List.of(
                    "course.svg",
                    "satellite_normalized.png",
                    "metadata/mask_features.json",
                    "metadata/classifications.json",
                    "metadata/hole_assignments.json");

            return ToolResult.success(
                    "Phase2a output validation passed",
                    Map.of(
                            "outputDir", outputDir,
                            "filesChecked", requiredFiles,
                            "valid", true,
                            "command", "phase2a validate " + outputDir));
        }
    }
}
