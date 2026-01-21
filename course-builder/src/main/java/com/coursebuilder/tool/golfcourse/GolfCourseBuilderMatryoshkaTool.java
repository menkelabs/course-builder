package com.coursebuilder.tool.golfcourse;

import com.coursebuilder.tool.MatryoshkaTool;
import com.coursebuilder.tool.Tool;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Top-level Matryoshka tool for Golf Course Building (GSPro).
 * 
 * This tool serves as the entry point for the "None to Done" workflow.
 * It contains nested tools for each MCP server in the pipeline:
 * 
 * LIDAR → Unity (Terrain) → Phase2a (SAM-based SVG) → Unity (PNG) → Blender (Mesh) → Unity (Final)
 * 
 * Hierarchy matches plan.md (with Phase2a replacing manual Inkscape):
 * GolfCourseBuilderTool
 * ├── LidarMcpTool (Phase 1: Terrain Creation)
 * ├── Phase2aMcpTool (Phase 2: Automated SAM-based SVG generation - replaces Inkscape)
 * ├── UnityTerrainMcpTool (Phase 3: Terrain Refinement)
 * ├── SvgConvertMcpTool (Phase 4: SVG Conversion)
 * ├── BlenderMcpTool (Phase 5: Blender Mesh Operations)
 * └── UnityAssemblyMcpTool (Phase 6: Unity Final Assembly)
 */
@Component
public class GolfCourseBuilderMatryoshkaTool extends MatryoshkaTool {
    
    public GolfCourseBuilderMatryoshkaTool(
            LidarMcpTool lidarMcp,
            Phase2aMcpTool phase2aMcp,
            UnityTerrainMcpTool unityTerrainMcp,
            SvgConvertMcpTool svgConvertMcp,
            BlenderMcpTool blenderMcp,
            UnityAssemblyMcpTool unityAssemblyMcp
    ) {
        super(
            "golf_course_builder",
            "Complete GSPro golf course creation toolkit implementing the 'None to Done' workflow. " +
            "Orchestrates LIDAR processing, Phase2a SAM-based SVG generation, Unity terrain, Blender mesh conversion, " +
            "and final Unity assembly. Select 'list' to see available MCP tool groups for each phase.",
            "golfcourse",
            List.of(lidarMcp, phase2aMcp, unityTerrainMcp, svgConvertMcp, blenderMcp, unityAssemblyMcp)
        );
    }
}
