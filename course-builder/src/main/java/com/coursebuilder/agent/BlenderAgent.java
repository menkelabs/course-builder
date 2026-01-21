package com.coursebuilder.agent;

import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.ToolRegistry;
import com.coursebuilder.tool.ToolResult;
import com.coursebuilder.tool.golfcourse.BlenderMcpTool;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * Agent specialized in Blender mesh operations (Phase 5).
 * 
 * This agent handles:
 * - Opening Blender templates
 * - Importing SVG and terrain
 * - Converting and cutting meshes
 * - Adding peripherals (curbs, bulkheads, water planes)
 * - Exporting FBX files
 */
@Component
public class BlenderAgent extends AbstractAgent {
    
    private final GolfCourseService courseService;
    
    public BlenderAgent(
            ToolRegistry toolRegistry,
            BlenderMcpTool blenderMcp,
            GolfCourseService courseService
    ) {
        super(
            toolRegistry,
            List.of(blenderMcp),
            List.of(
                ".*blender.*",
                ".*mesh.*",
                ".*fbx.*",
                ".*import.*svg.*",
                ".*import.*terrain.*",
                ".*convert.*mesh.*",
                ".*curb.*",
                ".*bulkhead.*",
                ".*water.*plane.*",
                ".*export.*fbx.*",
                ".*donut.*fix.*"
            )
        );
        this.courseService = courseService;
    }
    
    @Override
    public String getName() {
        return "BlenderAgent";
    }
    
    @Override
    public String getDescription() {
        return "Specialized in Blender mesh operations for golf course conversion. " +
               "Handles SVG/terrain import, mesh conversion, peripherals, and FBX export.";
    }
    
    @Override
    public AgentResponse process(AgentContext context, String userMessage) {
        log.info("BlenderAgent processing: {}", userMessage);
        context.addMessage(AgentContext.Message.user(userMessage));
        
        String lowerMessage = userMessage.toLowerCase();
        
        if (lowerMessage.contains("open") || lowerMessage.contains("template")) {
            return handleOpenTemplate(context, userMessage);
        }
        
        if (lowerMessage.contains("import svg")) {
            return handleImportSvg(context, userMessage);
        }
        
        if (lowerMessage.contains("import terrain")) {
            return handleImportTerrain(context, userMessage);
        }
        
        if (lowerMessage.contains("convert") && lowerMessage.contains("cut")) {
            return handleConvertAndCut(context, userMessage);
        }
        
        if (lowerMessage.contains("convert mesh")) {
            return handleConvertMeshes(context, userMessage);
        }
        
        if (lowerMessage.contains("donut") || lowerMessage.contains("fix cart")) {
            return handleFixDonut(context, userMessage);
        }
        
        if (lowerMessage.contains("curb")) {
            return handleAddCurbs(context, userMessage);
        }
        
        if (lowerMessage.contains("bulkhead")) {
            return handleAddBulkhead(context, userMessage);
        }
        
        if (lowerMessage.contains("water plane")) {
            return handleAddWaterPlane(context, userMessage);
        }
        
        if (lowerMessage.contains("export") || lowerMessage.contains("fbx")) {
            return handleExportFbx(context, userMessage);
        }
        
        // Default: show Blender workflow
        return AgentResponse.withFollowUp(
            "# Blender Mesh Operations (Phase 5)\n\n" +
            "I can help with the Blender workflow:\n\n" +
            "1. **Open template**: Load courseconversion.blend\n" +
            "2. **Import SVG**: Load the converted SVG file\n" +
            "3. **Import terrain**: Load Terrain.obj from Unity\n" +
            "4. **Convert and Cut**: Run Convert Mats and Cut\n" +
            "5. **Convert Meshes**: Conform to terrain surface\n" +
            "6. **Fix Donut**: Fix cart path loop corruption (Hole98)\n" +
            "7. **Add Curbs**: Add curbs to cart paths\n" +
            "8. **Add Bulkhead**: Add edging to water features\n" +
            "9. **Add Water Planes**: Create water surfaces\n" +
            "10. **Export FBX**: Export meshes for Unity\n\n" +
            "What operation do you need?",
            "Tell me what Blender operation you need"
        );
    }
    
    private AgentResponse handleOpenTemplate(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_open_course_template",
            "parameters", Map.of(
                "courseId", courseId,
                "templatePath", "/templates/courseconversion.blend"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Opened Blender with course template.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_open_course_template", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleImportSvg(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_import_svg",
            "parameters", Map.of(
                "courseId", courseId,
                "svgFile", "/output/" + courseId + "/course-converted.svg"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Imported SVG into Blender.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_import_svg", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleImportTerrain(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_import_terrain",
            "parameters", Map.of(
                "courseId", courseId,
                "terrainObj", "/output/" + courseId + "/Terrain.obj"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Imported terrain mesh into Blender.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_import_terrain", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleConvertAndCut(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_convert_and_cut",
            "parameters", Map.of("courseId", courseId)
        ), context);
        
        return AgentResponse.withTools(
            "Converted materials and cut meshes by hole.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_convert_and_cut", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleConvertMeshes(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_convert_meshes",
            "parameters", Map.of("courseId", courseId)
        ), context);
        
        return AgentResponse.withTools(
            "Conformed meshes to terrain surface.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_convert_meshes", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleFixDonut(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_fix_donut",
            "parameters", Map.of("courseId", courseId)
        ), context);
        
        return AgentResponse.withTools(
            "Fixed cart path donut corruption.\n\n" + result.message() + "\n\n" +
            "This issue occurs when cart paths loop back on themselves, creating a 'donut' " +
            "that corrupts the mesh. The fix removes the corrupt face from Hole98.",
            List.of(AgentResponse.ToolInvocation.of("blender_fix_donut", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleAddCurbs(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_add_curbs",
            "parameters", Map.of(
                "courseId", courseId,
                "curbHeight", 0.1,
                "curbWidth", 0.05
            )
        ), context);
        
        return AgentResponse.withTools(
            "Added curbs to cart paths.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_add_curbs", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleAddBulkhead(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_add_bulkhead",
            "parameters", Map.of(
                "courseId", courseId,
                "bulkheadStyle", "wood"
            )
        ), context);
        
        return AgentResponse.withTools(
            "Added bulkhead edging to water features.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_add_bulkhead", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleAddWaterPlane(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_add_water_plane",
            "parameters", Map.of(
                "courseId", courseId,
                "waterLevel", 0.0
            )
        ), context);
        
        return AgentResponse.withTools(
            "Added water planes to water hazards.\n\n" + result.message(),
            List.of(AgentResponse.ToolInvocation.of("blender_add_water_plane", Map.of(), result.data()))
        );
    }
    
    private AgentResponse handleExportFbx(AgentContext context, String userMessage) {
        String courseId = ensureCourseId(context);
        
        ToolResult result = executeTool("blender_mcp", Map.of(
            "operation", "blender_export_fbx",
            "parameters", Map.of(
                "courseId", courseId,
                "perHole", true
            )
        ), context);
        
        return AgentResponse.withTools(
            "Exported FBX files for Unity import.\n\n" + result.message() + "\n\n" +
            "Output directory: " + result.data().get("outputDirectory") + "\n" +
            "Files exported: " + result.data().get("filesExported"),
            List.of(AgentResponse.ToolInvocation.of("blender_export_fbx", Map.of(), result.data()))
        );
    }
    
    private String ensureCourseId(AgentContext context) {
        String courseId = context.getCurrentCourseId();
        return courseId != null ? courseId : "demo-course";
    }
}
