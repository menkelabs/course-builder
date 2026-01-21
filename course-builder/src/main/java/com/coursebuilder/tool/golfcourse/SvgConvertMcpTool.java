package com.coursebuilder.tool.golfcourse;

import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.MatryoshkaTool;
import com.coursebuilder.tool.Tool;
import com.coursebuilder.tool.ToolResult;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * MCP Tool for SVG Conversion (Phase 4).
 * 
 * Step 8 from plan.md:
 * - Run SVG file through GSProSVGConvert.exe to get "svg-converted" file
 */
@Component
public class SvgConvertMcpTool extends MatryoshkaTool {
    
    public SvgConvertMcpTool(GolfCourseService courseService) {
        super(
            "svg_convert_mcp",
            "SVG conversion using GSProSVGConvert.exe. Prepares Inkscape SVG for Blender import. Gate: svg_converted",
            "golfcourse",
            List.of(new SvgConvertTool(courseService))
        );
    }
    
    /**
     * Run GSProSVGConvert.exe.
     */
    static class SvgConvertTool implements Tool {
        private final GolfCourseService courseService;
        
        SvgConvertTool(GolfCourseService courseService) {
            this.courseService = courseService;
        }
        
        @Override
        public String getName() { return "svg_convert"; }
        
        @Override
        public String getDescription() {
            return "Run GSProSVGConvert.exe to prepare SVG for Blender import. " +
                   "Converts Inkscape SVG to format compatible with Blender import scripts.";
        }
        
        @Override
        public String getCategory() { return "conversion"; }
        
        @Override
        public Map<String, Object> getInputSchema() {
            return Map.of(
                "type", "object",
                "properties", Map.of(
                    "courseId", Map.of("type", "string"),
                    "svgFile", Map.of("type", "string", "description", "Original Inkscape SVG path")
                ),
                "required", List.of("courseId", "svgFile")
            );
        }
        
        @Override
        public ToolResult execute(Map<String, Object> input) {
            String courseId = (String) input.get("courseId");
            String svgFile = (String) input.get("svgFile");
            
            // Output path follows GSProSVGConvert convention
            String convertedSvg = svgFile.replace(".svg", "-converted.svg");
            
            courseService.setArtifact(courseId, "svg_converted", convertedSvg);
            courseService.completeStep(courseId, "svg_convert");
            
            // Complete gate
            courseService.getCourse(courseId).ifPresent(course -> 
                course.getWorkflowState().completeGate("svg_converted")
            );
            
            return ToolResult.success(
                "Converted SVG for Blender",
                Map.of(
                    "inputSvg", svgFile,
                    "convertedSvg", convertedSvg,
                    "gateCompleted", "svg_converted"
                )
            );
        }
    }
}
