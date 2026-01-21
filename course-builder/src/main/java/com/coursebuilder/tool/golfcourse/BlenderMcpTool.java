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
 * MCP Tool for Blender Mesh Operations (Phase 5).
 * 
 * Steps 9-16 from plan.md:
 * - Open courseconversion.blend file (Blender 2.83 LTS)
 * - Install required addons
 * - Import SVG and Terrain.obj
 * - Convert Mats and Cut
 * - Convert Meshes (conform to terrain)
 * - Add peripherals (bulkheads, curbs, water planes)
 * - Export FBX files
 */
@Component
public class BlenderMcpTool extends MatryoshkaTool {
    
    public BlenderMcpTool(GolfCourseService courseService) {
        super(
            "blender_mcp",
            "Blender mesh operations for course conversion. Import SVG/terrain, convert and cut meshes, " +
            "add peripherals, and export FBX files. Uses Blender 2.83 LTS. Gate: fbx_exported",
            "golfcourse",
            List.of(
                new BlenderOpenCourseTemplateTool(courseService),
                new BlenderInstallAddonsTool(courseService),
                new BlenderImportSvgTool(courseService),
                new BlenderImportTerrainTool(courseService),
                new BlenderConvertAndCutTool(courseService),
                new BlenderConvertMeshesTool(courseService),
                new BlenderFixDonutTool(courseService),
                new BlenderAddCurbsTool(courseService),
                new BlenderAddBulkheadTool(courseService),
                new BlenderAddWaterPlaneTool(courseService),
                new BlenderRetopoHole99Tool(courseService),
                new BlenderExportFbxTool(courseService)
            )
        );
    }
    
    static class BlenderOpenCourseTemplateTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderOpenCourseTemplateTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_open_course_template"; }
        
        @Override
        public String getDescription() {
            return "Open the courseconversion.blend template file in Blender 2.83 LTS.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "templatePath", Map.of("type", "string", "description", "Path to courseconversion.blend")
                ),
                "required", List.of("courseId", "templatePath")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String templatePath = (String) input.get("templatePath");
            
            String sessionId = "blender_" + UUID.randomUUID().toString().substring(0, 8);
            courseService.setArtifact(courseId, "blender_session", sessionId);
            courseService.completeStep(courseId, "blender_open_course_template");
            
            return ToolResult.success(
                "Opened Blender with course template",
                Map.of(
                    "blenderSession", sessionId,
                    "templateFile", templatePath,
                    "blenderVersion", "2.83 LTS"
                )
            );
        }
    }
    
    static class BlenderInstallAddonsTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderInstallAddonsTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_install_addons"; }
        
        @Override
        public String getDescription() {
            return "Install required Blender addons: Boundary Align Remesh, Mesh Tools, Loop Tools, Course Builder Blender Tools.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "addons", Map.of("type", "array", "items", Map.of("type", "string"))
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            
            List<String> requiredAddons = List.of(
                "Boundary Align Remesh",
                "Mesh Tools", 
                "Loop Tools",
                "Course Builder Blender Tools"
            );
            
            courseService.completeStep(courseId, "blender_install_addons");
            
            return ToolResult.success(
                "Installed and enabled required addons",
                Map.of("addonsEnabled", requiredAddons)
            );
        }
    }
    
    static class BlenderImportSvgTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderImportSvgTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_import_svg"; }
        
        @Override
        public String getDescription() {
            return "Import the converted SVG file into Blender.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "svgFile", Map.of("type", "string", "description", "Path to svg-converted file")
                ),
                "required", List.of("courseId", "svgFile")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String svgFile = (String) input.get("svgFile");
            
            courseService.completeStep(courseId, "blender_import_svg");
            
            return ToolResult.success(
                "Imported SVG curves into Blender",
                Map.of(
                    "svgFile", svgFile,
                    "curvesImported", 20 // Mock: number of hole layers
                )
            );
        }
    }
    
    static class BlenderImportTerrainTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderImportTerrainTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_import_terrain"; }
        
        @Override
        public String getDescription() {
            return "Import Terrain.obj from Unity export into Blender.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "terrainObj", Map.of("type", "string", "description", "Path to Terrain.obj")
                ),
                "required", List.of("courseId", "terrainObj")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String terrainObj = (String) input.get("terrainObj");
            
            courseService.completeStep(courseId, "blender_import_terrain");
            
            return ToolResult.success(
                "Imported terrain mesh into Blender",
                Map.of(
                    "terrainObj", terrainObj,
                    "terrainMesh", "Terrain_imported"
                )
            );
        }
    }
    
    static class BlenderConvertAndCutTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderConvertAndCutTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_convert_and_cut"; }
        
        @Override
        public String getDescription() {
            return "Run 'Convert Mats and Cut' operation from Course Builder Blender Tools.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            
            courseService.completeStep(courseId, "blender_convert_and_cut");
            
            return ToolResult.success(
                "Converted materials and cut meshes by hole",
                Map.of(
                    "meshesCreated", 20,
                    "operation", "Convert Mats and Cut"
                )
            );
        }
    }
    
    static class BlenderConvertMeshesTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderConvertMeshesTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_convert_meshes"; }
        
        @Override
        public String getDescription() {
            return "Conform shapes to terrain surface using Convert Meshes operation.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            
            // Mark all holes as mesh converted
            courseService.getCourse(courseId).ifPresent(course -> 
                course.getHoles().forEach(hole -> hole.setMeshConverted(true))
            );
            courseService.completeStep(courseId, "blender_convert_meshes");
            
            return ToolResult.success(
                "Conformed all meshes to terrain surface",
                Map.of("meshesProjected", 20)
            );
        }
    }
    
    static class BlenderFixDonutTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderFixDonutTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_fix_donut"; }
        
        @Override
        public String getDescription() {
            return "Fix cart path (Hole98) donut corruption caused by looping paths.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            
            courseService.completeStep(courseId, "blender_fix_donut");
            
            return ToolResult.success(
                "Fixed cart path donut corruption",
                Map.of(
                    "holeFixed", 98,
                    "operation", "Remove corrupt face from looped cart path"
                )
            );
        }
    }
    
    static class BlenderAddCurbsTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderAddCurbsTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_add_curbs"; }
        
        @Override
        public String getDescription() {
            return "Add curbs to cart paths (Hole98).";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "curbHeight", Map.of("type", "number", "description", "Height of curbs"),
                    "curbWidth", Map.of("type", "number", "description", "Width of curbs")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            double curbHeight = ((Number) input.getOrDefault("curbHeight", 0.1)).doubleValue();
            double curbWidth = ((Number) input.getOrDefault("curbWidth", 0.05)).doubleValue();
            
            courseService.completeStep(courseId, "blender_add_curbs");
            
            return ToolResult.success(
                "Added curbs to cart paths",
                Map.of(
                    "curbHeight", curbHeight,
                    "curbWidth", curbWidth,
                    "appliedTo", "Hole98"
                )
            );
        }
    }
    
    static class BlenderAddBulkheadTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderAddBulkheadTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_add_bulkhead"; }
        
        @Override
        public String getDescription() {
            return "Add bulkhead edging to water features.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "waterMeshes", Map.of("type", "array", "items", Map.of("type", "string")),
                    "bulkheadStyle", Map.of("type", "string", "enum", List.of("wood", "stone", "concrete"))
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String style = (String) input.getOrDefault("bulkheadStyle", "wood");
            
            courseService.completeStep(courseId, "blender_add_bulkhead");
            
            return ToolResult.success(
                "Added bulkhead to water features",
                Map.of("bulkheadStyle", style)
            );
        }
    }
    
    static class BlenderAddWaterPlaneTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderAddWaterPlaneTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_add_water_plane"; }
        
        @Override
        public String getDescription() {
            return "Add water plane meshes to water hazards.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "waterLevel", Map.of("type", "number", "description", "Height of water surface")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            double waterLevel = ((Number) input.getOrDefault("waterLevel", 0.0)).doubleValue();
            
            courseService.completeStep(courseId, "blender_add_water_plane");
            
            return ToolResult.success(
                "Added water planes to water hazards",
                Map.of("waterLevel", waterLevel)
            );
        }
    }
    
    static class BlenderRetopoHole99Tool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderRetopoHole99Tool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_retopo_hole99"; }
        
        @Override
        public String getDescription() {
            return "Retopologize Hole99 (outer mesh) for cleaner geometry.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            
            courseService.completeStep(courseId, "blender_retopo_hole99");
            
            return ToolResult.success(
                "Retopologized Hole99 outer mesh",
                Map.of("hole", 99, "operation", "retopology")
            );
        }
    }
    
    static class BlenderExportFbxTool implements Tool {
        private final GolfCourseService courseService;
        
        BlenderExportFbxTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "blender_export_fbx"; }
        
        @Override
        public String getDescription() {
            return "Export all meshes as FBX files for Unity import. Completes fbx_exported gate.";
        }
        
        @Override
        public String getCategory() { return "blender"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "outputDirectory", Map.of("type", "string", "description", "Export location"),
                    "perHole", Map.of("type", "boolean", "description", "Export per hole or combined")
                ),
                "required", List.of("courseId")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String outputDir = (String) input.getOrDefault("outputDirectory", 
                "/output/" + courseId + "/fbx/");
            boolean perHole = (Boolean) input.getOrDefault("perHole", true);
            
            List<String> exportedFiles = List.of(
                outputDir + "Hole01.fbx", outputDir + "Hole02.fbx",
                outputDir + "Hole98_cartpaths.fbx", outputDir + "Hole99_outer.fbx"
            );
            
            courseService.setArtifact(courseId, "fbx_directory", outputDir);
            courseService.completeStep(courseId, "blender_export_fbx");
            
            // Complete gate
            courseService.getCourse(courseId).ifPresent(course -> 
                course.getWorkflowState().completeGate("fbx_exported")
            );
            
            return ToolResult.success(
                "Exported FBX files",
                Map.of(
                    "outputDirectory", outputDir,
                    "filesExported", exportedFiles.size(),
                    "perHole", perHole,
                    "gateCompleted", "fbx_exported"
                )
            );
        }
    }
}
