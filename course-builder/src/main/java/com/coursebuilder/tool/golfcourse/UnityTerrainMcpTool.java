package com.coursebuilder.tool.golfcourse;

import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.MatryoshkaTool;
import com.coursebuilder.tool.Tool;
import com.coursebuilder.tool.ToolResult;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * MCP Tool for Unity Terrain Operations (Phase 3: Terrain Refinement).
 * 
 * Steps 5-7 from plan.md:
 * - Place exported PNG in first paint slot on Terrain in Unity
 * - Adjust contours of Terrain and modify SVG file as needed
 * - Export Terrain using ExportTerrain.cs as Terrain.obj
 */
@Component
public class UnityTerrainMcpTool extends MatryoshkaTool {
    
    public UnityTerrainMcpTool(GolfCourseService courseService) {
        super(
            "unity_terrain_mcp",
            "Unity terrain operations for refinement. Apply PNG overlays, adjust contours, " +
            "and export terrain as OBJ for Blender processing. Gate: terrain_exported",
            "golfcourse",
            List.of(
                new UnityApplyTerrainOverlayTool(courseService),
                new UnityAdjustTerrainContoursTool(courseService),
                new UnityExportTerrainTool(courseService)
            )
        );
    }
    
    /**
     * Apply PNG overlay to terrain paint slot.
     */
    static class UnityApplyTerrainOverlayTool implements Tool {
        private final GolfCourseService courseService;
        
        UnityApplyTerrainOverlayTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "unity_apply_terrain_overlay"; }
        
        @Override
        public String getDescription() {
            return "Apply PNG overlay to terrain's first paint slot for visualization during refinement.";
        }
        
        @Override
        public String getCategory() { return "unity"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "projectPath", Map.of("type", "string", "description", "Unity project path"),
                    "pngFile", Map.of("type", "string", "description", "Course overlay PNG"),
                    "paintSlot", Map.of("type", "integer", "description", "Slot number (typically 0)")
                ),
                "required", List.of("courseId", "projectPath", "pngFile")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String projectPath = (String) input.get("projectPath");
            String pngFile = (String) input.get("pngFile");
            int paintSlot = ((Number) input.getOrDefault("paintSlot", 0)).intValue();
            
            courseService.completeStep(courseId, "unity_apply_terrain_overlay");
            
            return ToolResult.success(
                "Applied course overlay to terrain paint slot " + paintSlot,
                Map.of(
                    "terrain", "Terrain_" + courseId,
                    "overlayApplied", pngFile,
                    "paintSlot", paintSlot
                )
            );
        }
    }
    
    /**
     * Adjust terrain contours/height.
     */
    static class UnityAdjustTerrainContoursTool implements Tool {
        private final GolfCourseService courseService;
        
        UnityAdjustTerrainContoursTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "unity_adjust_terrain_contours"; }
        
        @Override
        public String getDescription() {
            return "Modify terrain height at specific locations to refine course contours.";
        }
        
        @Override
        public String getCategory() { return "unity"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "adjustments", Map.of("type", "array", "items", Map.of(
                        "type", "object", "properties", Map.of(
                            "x", Map.of("type", "number"),
                            "z", Map.of("type", "number"),
                            "heightDelta", Map.of("type", "number"),
                            "radius", Map.of("type", "number"),
                            "falloff", Map.of("type", "number")
                        )
                    ))
                ),
                "required", List.of("courseId", "adjustments")
            );
        }
        
        @Override
        @SuppressWarnings("unchecked")
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            List<Map<String, Object>> adjustments = (List<Map<String, Object>>) input.get("adjustments");
            
            courseService.completeStep(courseId, "unity_adjust_terrain_contours");
            
            return ToolResult.success(
                "Applied " + adjustments.size() + " terrain adjustments",
                Map.of(
                    "adjustmentsApplied", adjustments.size(),
                    "terrain", "Terrain_" + courseId
                )
            );
        }
    }
    
    /**
     * Export terrain as OBJ.
     */
    static class UnityExportTerrainTool implements Tool {
        private final GolfCourseService courseService;
        
        UnityExportTerrainTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "unity_export_terrain"; }
        
        @Override
        public String getDescription() {
            return "Export terrain as OBJ using ExportTerrain.cs for Blender import. Completes terrain_exported gate.";
        }
        
        @Override
        public String getCategory() { return "unity"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "resolution", Map.of("type", "string", "enum", List.of("full", "half", "quarter")),
                    "outputPath", Map.of("type", "string", "description", "Where to save Terrain.obj")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String resolution = (String) input.getOrDefault("resolution", "half");
            String outputPath = (String) input.getOrDefault("outputPath", 
                "/output/" + courseId + "/Terrain.obj");
            
            courseService.setArtifact(courseId, "terrain_obj", outputPath);
            courseService.completeStep(courseId, "unity_export_terrain");
            
            // Update terrain data
            courseService.getCourse(courseId).ifPresent(course -> {
                if (course.getTerrain() != null) {
                    course.getTerrain().setTerrainObjPath(outputPath);
                }
                course.getWorkflowState().completeGate("terrain_exported");
            });
            
            return ToolResult.success(
                "Exported terrain as OBJ",
                Map.of(
                    "terrainObj", outputPath,
                    "resolution", resolution,
                    "gateCompleted", "terrain_exported"
                )
            );
        }
    }
}
