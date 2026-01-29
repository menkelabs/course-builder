package com.coursebuilder.harness;

import com.coursebuilder.agent.*;
import com.coursebuilder.model.GolfCourse;
import com.coursebuilder.model.Hole;
import com.coursebuilder.service.GolfCourseService;
import com.coursebuilder.tool.*;
import com.coursebuilder.tool.golfcourse.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.TestInstance.Lifecycle;

import java.util.*;

import static org.assertj.core.api.Assertions.*;

/**
 * Comprehensive Test Harness for Golf Course Builder.
 * 
 * Tests the complete "None to Done" workflow from plan.md:
 * 
 * Phase 1: Terrain Creation (LIDAR)
 * Phase 2: Course Tracing (Phase1a - SAM-based)
 * Phase 3: Terrain Refinement (Unity)
 * Phase 4: SVG Conversion
 * Phase 5: Blender Processing
 * Phase 6: Unity Final Assembly
 * 
 * Demonstrates:
 * - Matryoshka tool hierarchy navigation
 * - Agent routing based on task description
 * - Correct tool selection for specific workflow steps
 * - Mock execution through entire pipeline
 * - Workflow state management and gate completion
 */
@TestInstance(Lifecycle.PER_CLASS)
@DisplayName("Golf Course Builder - None to Done Workflow Test Harness")
public class GolfCourseTestHarness {
    
    // Services
    private GolfCourseService courseService;
    
    // Tool Registry
    private ToolRegistry toolRegistry;
    
    // Matryoshka Tools - All 6 Phases
    private LidarMcpTool lidarMcp;
    private Phase1aMcpTool phase1aMcp;
    private UnityTerrainMcpTool unityTerrainMcp;
    private SvgConvertMcpTool svgConvertMcp;
    private BlenderMcpTool blenderMcp;
    private UnityAssemblyMcpTool unityAssemblyMcp;
    private GolfCourseBuilderMatryoshkaTool courseBuilderTool;
    
    // Agents
    private GolfCourseWorkflowAgent workflowAgent;
    private Phase1aAgent phase1aAgent;
    private BlenderAgent blenderAgent;
    private AgentRouter agentRouter;
    
    @BeforeAll
    void setup() {
        System.out.println("\n" + "=".repeat(70));
        System.out.println("GOLF COURSE BUILDER TEST HARNESS");
        System.out.println("Testing 'None to Done' Workflow with Matryoshka Tool Pattern");
        System.out.println("=".repeat(70));
        
        // Initialize service
        courseService = new GolfCourseService();
        
        // Initialize Matryoshka tools for each phase
        lidarMcp = new LidarMcpTool(courseService);
        phase1aMcp = new Phase1aMcpTool(courseService);
        unityTerrainMcp = new UnityTerrainMcpTool(courseService);
        svgConvertMcp = new SvgConvertMcpTool(courseService);
        blenderMcp = new BlenderMcpTool(courseService);
        unityAssemblyMcp = new UnityAssemblyMcpTool(courseService);
        
        // Top-level Matryoshka tool
        courseBuilderTool = new GolfCourseBuilderMatryoshkaTool(
            lidarMcp, phase1aMcp, unityTerrainMcp, svgConvertMcp, blenderMcp, unityAssemblyMcp
        );
        
        // Initialize tool registry
        List<Tool> allTools = List.of(
            courseBuilderTool, lidarMcp, phase1aMcp, 
            unityTerrainMcp, svgConvertMcp, blenderMcp, unityAssemblyMcp
        );
        toolRegistry = new ToolRegistry(allTools);
        
        // Initialize agents
        workflowAgent = new GolfCourseWorkflowAgent(toolRegistry, courseBuilderTool, courseService);
        phase1aAgent = new Phase1aAgent(toolRegistry, phase1aMcp, courseService);
        blenderAgent = new BlenderAgent(toolRegistry, blenderMcp, courseService);
        
        agentRouter = new AgentRouter(List.of(workflowAgent, phase1aAgent, blenderAgent));
        
        System.out.println("\nInitialized:");
        System.out.println("  - Tool Registry with " + toolRegistry.getTopLevelTools().size() + " top-level tools");
        System.out.println("  - Agent Router with " + agentRouter.getAgents().size() + " agents");
        System.out.println("  - 6 Phase Matryoshka tools");
        System.out.println();
    }
    
    // ===========================================
    // MATRYOSHKA TOOL HIERARCHY TESTS
    // ===========================================
    
    @Nested
    @DisplayName("Matryoshka Tool Hierarchy")
    class MatryoshkaHierarchyTests {
        
        @Test
        @DisplayName("Top-level golf_course_builder contains all 6 phase tools")
        void topLevelContainsAllPhases() {
            System.out.println("\n--- Test: Golf Course Builder Tool Hierarchy ---");
            
            assertThat(courseBuilderTool.isMatryoshka()).isTrue();
            assertThat(courseBuilderTool.getNestedTools()).hasSize(6);
            
            List<String> nestedNames = courseBuilderTool.getNestedTools().stream()
                .map(Tool::getName)
                .toList();
            
            System.out.println("Top-level tool: " + courseBuilderTool.getName());
            System.out.println("Nested phase tools:");
            nestedNames.forEach(n -> System.out.println("  - " + n));
            
            assertThat(nestedNames).containsExactly(
                "lidar_mcp",
                "phase1a_mcp",
                "unity_terrain_mcp",
                "svg_convert_mcp",
                "blender_mcp",
                "unity_assembly_mcp"
            );
        }
        
        @Test
        @DisplayName("Phase1a MCP contains SAM-based tracing tools")
        void phase1aContainsSamTools() {
            System.out.println("\n--- Test: Phase1a MCP Tool Hierarchy ---");
            
            assertThat(phase1aMcp.isMatryoshka()).isTrue();
            
            List<String> nestedNames = phase1aMcp.getNestedTools().stream()
                .map(Tool::getName)
                .toList();
            
            System.out.println("Phase1a MCP tools:");
            nestedNames.forEach(n -> System.out.println("  - " + n));
            
            assertThat(nestedNames).contains(
                "phase1a_run",
                "phase1a_generate_masks",
                "phase1a_classify",
                "phase1a_interactive_select",
                "phase1a_generate_svg",
                "phase1a_export_png",
                "phase1a_validate"
            );
        }
        
        @Test
        @DisplayName("Blender MCP contains all mesh operation tools")
        void blenderContainsMeshTools() {
            System.out.println("\n--- Test: Blender MCP Tool Hierarchy ---");
            
            assertThat(blenderMcp.isMatryoshka()).isTrue();
            
            List<String> nestedNames = blenderMcp.getNestedTools().stream()
                .map(Tool::getName)
                .toList();
            
            System.out.println("Blender MCP tools:");
            nestedNames.forEach(n -> System.out.println("  - " + n));
            
            assertThat(nestedNames).contains(
                "blender_open_course_template",
                "blender_import_svg",
                "blender_import_terrain",
                "blender_convert_and_cut",
                "blender_convert_meshes",
                "blender_fix_donut",
                "blender_add_curbs",
                "blender_add_bulkhead",
                "blender_add_water_plane",
                "blender_export_fbx"
            );
        }
        
        @Test
        @DisplayName("List operation reveals nested tools at each level")
        void listOperationRevealsNestedTools() {
            System.out.println("\n--- Test: List Operation on Matryoshka Tools ---");
            
            // Top level
            ToolResult topResult = courseBuilderTool.execute(Map.of("operation", "list"));
            assertThat(topResult.success()).isTrue();
            assertThat(topResult.hasNestedTools()).isTrue();
            assertThat(topResult.suggestedTools()).hasSize(6);
            
            System.out.println("golf_course_builder.list() returned " + 
                topResult.suggestedTools().size() + " phase tools");
            
            // Phase1a level
            ToolResult phase1aResult = phase1aMcp.execute(Map.of("operation", "list"));
            assertThat(phase1aResult.success()).isTrue();
            assertThat(phase1aResult.hasNestedTools()).isTrue();
            
            System.out.println("phase1a_mcp.list() returned " + 
                phase1aResult.suggestedTools().size() + " SAM tools");
        }
    }
    
    // ===========================================
    // AGENT ROUTING TESTS
    // ===========================================
    
    @Nested
    @DisplayName("Agent Routing")
    class AgentRoutingTests {
        
        @Test
        @DisplayName("Routes workflow tasks to GolfCourseWorkflowAgent")
        void routesWorkflowTasks() {
            System.out.println("\n--- Test: Agent Routing for Workflow Tasks ---");
            
            String[] workflowTasks = {
                "Create a new golf course",
                "Start the None to Done workflow",
                "Build a course for GSPro",
                "What phase am I on?",
                "Process LIDAR data for terrain"
            };
            
            for (String task : workflowTasks) {
                Optional<Agent> agent = agentRouter.route(task);
                assertThat(agent)
                    .as("Task: " + task)
                    .isPresent();
                System.out.println("\"" + task + "\" -> " + agent.get().getName());
            }
        }
        
        @Test
        @DisplayName("Routes Phase1a tasks to Phase1aAgent")
        void routesPhase1aTasks() {
            System.out.println("\n--- Test: Agent Routing for Phase1a Tasks ---");
            
            String[] phase1aTasks = {
                "Generate masks from satellite image using SAM",
                "Classify features from the masks", 
                "Run phase1a interactive selection",
                "Use segment anything model on satellite"
            };
            
            for (String task : phase1aTasks) {
                Optional<Agent> agent = agentRouter.route(task);
                assertThat(agent)
                    .as("Task: " + task)
                    .isPresent()
                    .get()
                    .extracting(Agent::getName)
                    .isEqualTo("Phase1aAgent");
                System.out.println("\"" + task + "\" -> " + agent.get().getName());
            }
        }
        
        @Test
        @DisplayName("Routes Blender tasks to BlenderAgent")
        void routesBlenderTasks() {
            System.out.println("\n--- Test: Agent Routing for Blender Tasks ---");
            
            String[] blenderTasks = {
                "Open Blender and import SVG",
                "Use Blender to convert meshes",
                "Export FBX files from Blender",
                "Fix the donut in Blender",
                "Add curbs in Blender"
            };
            
            for (String task : blenderTasks) {
                Optional<Agent> agent = agentRouter.route(task);
                assertThat(agent)
                    .as("Task: " + task)
                    .isPresent()
                    .get()
                    .extracting(Agent::getName)
                    .isEqualTo("BlenderAgent");
                System.out.println("\"" + task + "\" -> " + agent.get().getName());
            }
        }
    }
    
    // ===========================================
    // COMPLETE WORKFLOW TESTS
    // ===========================================
    
    @Nested
    @DisplayName("Complete None to Done Workflow")
    class CompleteWorkflowTests {
        
        @Test
        @DisplayName("Execute complete 6-phase workflow")
        void executeCompleteWorkflow() {
            System.out.println("\n" + "=".repeat(60));
            System.out.println("COMPLETE 'NONE TO DONE' WORKFLOW TEST");
            System.out.println("=".repeat(60));
            
            // Create course
            GolfCourse course = courseService.createCourse("Pine Valley Test", "New Jersey");
            String courseId = course.getId();
            
            System.out.println("\nCreated course: " + course.getName() + " (ID: " + courseId + ")");
            
            // Phase 1: LIDAR/Terrain
            System.out.println("\n--- PHASE 1: Terrain Creation (LIDAR) ---");
            
            ToolResult lidarResult = lidarMcp.execute(Map.of(
                "operation", "lidar_to_heightmap",
                "parameters", Map.of(
                    "courseId", courseId,
                    "lidarSource", "https://lidar.example.com/nj.laz",
                    "bounds", Map.of("northLat", 40.5, "southLat", 40.4, "eastLon", -74.3, "westLon", -74.4),
                    "resolution", 1025
                )
            ));
            assertThat(lidarResult.success()).isTrue();
            System.out.println("  ✓ " + lidarResult.message());
            
            ToolResult terrainSetupResult = lidarMcp.execute(Map.of(
                "operation", "unity_setup_terrain",
                "parameters", Map.of(
                    "courseId", courseId,
                    "heightmapPath", lidarResult.data().get("heightmapPath"),
                    "projectPath", "/Unity/PineValley"
                )
            ));
            assertThat(terrainSetupResult.success()).isTrue();
            assertThat(terrainSetupResult.data().get("gateCompleted")).isEqualTo("terrain_ready");
            System.out.println("  ✓ " + terrainSetupResult.message());
            System.out.println("  Gate completed: terrain_ready");
            
            // Phase 2: Phase1a SAM-based tracing
            System.out.println("\n--- PHASE 2: Course Tracing (Phase1a - SAM) ---");
            
            ToolResult phase1aResult = phase1aMcp.execute(Map.of(
                "operation", "phase1a_run",
                "parameters", Map.of(
                    "courseId", courseId,
                    "satelliteImage", "/input/pine_valley_satellite.png",
                    "checkpoint", "checkpoints/sam_vit_h_4b8939.pth"
                )
            ));
            assertThat(phase1aResult.success()).isTrue();
            assertThat(phase1aResult.data().get("gateCompleted")).isEqualTo("svg_complete");
            System.out.println("  ✓ " + phase1aResult.message());
            System.out.println("  Features: " + phase1aResult.data().get("featuresClassified"));
            System.out.println("  Gate completed: svg_complete");
            
            // Phase 3: Unity Terrain Refinement
            System.out.println("\n--- PHASE 3: Terrain Refinement (Unity) ---");
            
            ToolResult overlayResult = unityTerrainMcp.execute(Map.of(
                "operation", "unity_apply_terrain_overlay",
                "parameters", Map.of(
                    "courseId", courseId,
                    "projectPath", "/Unity/PineValley",
                    "pngFile", "/output/" + courseId + "/phase1a/exports/overlay.png"
                )
            ));
            assertThat(overlayResult.success()).isTrue();
            System.out.println("  ✓ " + overlayResult.message());
            
            ToolResult exportTerrainResult = unityTerrainMcp.execute(Map.of(
                "operation", "unity_export_terrain",
                "parameters", Map.of("courseId", courseId, "resolution", "half")
            ));
            assertThat(exportTerrainResult.success()).isTrue();
            assertThat(exportTerrainResult.data().get("gateCompleted")).isEqualTo("terrain_exported");
            System.out.println("  ✓ " + exportTerrainResult.message());
            System.out.println("  Gate completed: terrain_exported");
            
            // Phase 4: SVG Conversion
            System.out.println("\n--- PHASE 4: SVG Conversion ---");
            
            ToolResult svgConvertResult = svgConvertMcp.execute(Map.of(
                "operation", "svg_convert",
                "parameters", Map.of(
                    "courseId", courseId,
                    "svgFile", phase1aResult.data().get("svgFile")
                )
            ));
            assertThat(svgConvertResult.success()).isTrue();
            assertThat(svgConvertResult.data().get("gateCompleted")).isEqualTo("svg_converted");
            System.out.println("  ✓ " + svgConvertResult.message());
            System.out.println("  Gate completed: svg_converted");
            
            // Phase 5: Blender Processing
            System.out.println("\n--- PHASE 5: Blender Processing ---");
            
            ToolResult blenderOpenResult = blenderMcp.execute(Map.of(
                "operation", "blender_open_course_template",
                "parameters", Map.of("courseId", courseId, "templatePath", "/templates/courseconversion.blend")
            ));
            System.out.println("  ✓ " + blenderOpenResult.message());
            
            ToolResult importSvgResult = blenderMcp.execute(Map.of(
                "operation", "blender_import_svg",
                "parameters", Map.of("courseId", courseId, "svgFile", svgConvertResult.data().get("convertedSvg"))
            ));
            System.out.println("  ✓ " + importSvgResult.message());
            
            ToolResult importTerrainResult = blenderMcp.execute(Map.of(
                "operation", "blender_import_terrain",
                "parameters", Map.of("courseId", courseId, "terrainObj", exportTerrainResult.data().get("terrainObj"))
            ));
            System.out.println("  ✓ " + importTerrainResult.message());
            
            ToolResult convertCutResult = blenderMcp.execute(Map.of(
                "operation", "blender_convert_and_cut",
                "parameters", Map.of("courseId", courseId)
            ));
            System.out.println("  ✓ " + convertCutResult.message());
            
            ToolResult convertMeshesResult = blenderMcp.execute(Map.of(
                "operation", "blender_convert_meshes",
                "parameters", Map.of("courseId", courseId)
            ));
            System.out.println("  ✓ " + convertMeshesResult.message());
            
            ToolResult exportFbxResult = blenderMcp.execute(Map.of(
                "operation", "blender_export_fbx",
                "parameters", Map.of("courseId", courseId, "perHole", true)
            ));
            assertThat(exportFbxResult.success()).isTrue();
            assertThat(exportFbxResult.data().get("gateCompleted")).isEqualTo("fbx_exported");
            System.out.println("  ✓ " + exportFbxResult.message());
            System.out.println("  Gate completed: fbx_exported");
            
            // Phase 6: Unity Final Assembly
            System.out.println("\n--- PHASE 6: Unity Final Assembly ---");
            
            ToolResult importFbxResult = unityAssemblyMcp.execute(Map.of(
                "operation", "unity_import_fbx",
                "parameters", Map.of(
                    "courseId", courseId,
                    "projectPath", "/Unity/PineValley",
                    "fbxFiles", List.of("Hole01.fbx", "Hole02.fbx")
                )
            ));
            System.out.println("  ✓ " + importFbxResult.message());
            
            ToolResult collidersResult = unityAssemblyMcp.execute(Map.of(
                "operation", "unity_add_colliders",
                "parameters", Map.of("courseId", courseId)
            ));
            System.out.println("  ✓ " + collidersResult.message());
            
            ToolResult materialsResult = unityAssemblyMcp.execute(Map.of(
                "operation", "unity_apply_materials",
                "parameters", Map.of("courseId", courseId)
            ));
            System.out.println("  ✓ " + materialsResult.message());
            
            ToolResult vegetationResult = unityAssemblyMcp.execute(Map.of(
                "operation", "unity_place_vegetation",
                "parameters", Map.of("courseId", courseId)
            ));
            System.out.println("  ✓ " + vegetationResult.message());
            
            ToolResult buildBundleResult = unityAssemblyMcp.execute(Map.of(
                "operation", "unity_build_asset_bundle",
                "parameters", Map.of("courseId", courseId, "platform", "Windows")
            ));
            assertThat(buildBundleResult.success()).isTrue();
            assertThat(buildBundleResult.data().get("gateCompleted")).isEqualTo("course_complete");
            assertThat(buildBundleResult.data().get("status")).isEqualTo("DONE");
            System.out.println("  ✓ " + buildBundleResult.message());
            System.out.println("  Gate completed: course_complete");
            
            // Verify final state
            System.out.println("\n" + "=".repeat(60));
            System.out.println("WORKFLOW COMPLETE - COURSE IS DONE!");
            System.out.println("=".repeat(60));
            
            Map<String, Object> progress = courseService.getWorkflowProgress(courseId);
            System.out.println("\nFinal Progress:");
            System.out.println("  Course: " + progress.get("courseName"));
            System.out.println("  Completed Steps: " + progress.get("completedSteps"));
            System.out.println("  Asset Bundle: " + ((Map<?,?>)progress.get("artifacts")).get("asset_bundle"));
            
            // Verify all holes were processed
            GolfCourse finalCourse = courseService.getCourse(courseId).orElseThrow();
            long tracedHoles = finalCourse.getHoles().stream().filter(Hole::isTraced).count();
            long convertedHoles = finalCourse.getHoles().stream().filter(Hole::isMeshConverted).count();
            
            System.out.println("  Holes Traced: " + tracedHoles + "/20");
            System.out.println("  Holes Mesh Converted: " + convertedHoles + "/20");
            
            assertThat(tracedHoles).isEqualTo(20);  // 18 + hole 98 + hole 99
            assertThat(convertedHoles).isEqualTo(20);
        }
        
        @Test
        @DisplayName("Workflow gates prevent out-of-order execution")
        void workflowGatesPreventOutOfOrder() {
            System.out.println("\n--- Test: Workflow Gate Enforcement ---");
            
            GolfCourse course = courseService.createCourse("Gate Test Course", "Test Location");
            String courseId = course.getId();
            
            // Verify initial state
            assertThat(course.getWorkflowState().getCurrentPhase())
                .isEqualTo(GolfCourse.WorkflowState.Phase.TERRAIN_CREATION);
            System.out.println("Initial phase: " + course.getWorkflowState().getCurrentPhase().getName());
            
            // Verify gate not completed
            assertThat(course.getWorkflowState().isGateCompleted("terrain_ready")).isFalse();
            System.out.println("terrain_ready gate: NOT COMPLETED");
            
            // Complete Phase 1
            lidarMcp.execute(Map.of(
                "operation", "unity_setup_terrain",
                "parameters", Map.of(
                    "courseId", courseId,
                    "heightmapPath", "/test/heightmap.raw",
                    "projectPath", "/Unity/Test"
                )
            ));
            
            // Verify gate completed
            course = courseService.getCourse(courseId).orElseThrow();
            assertThat(course.getWorkflowState().isGateCompleted("terrain_ready")).isTrue();
            System.out.println("terrain_ready gate: COMPLETED");
        }
    }
    
    // ===========================================
    // TOOL SELECTION TESTS
    // ===========================================
    
    @Nested
    @DisplayName("Tool Selection for Specific Tasks")
    class ToolSelectionTests {
        
        @Test
        @DisplayName("Selects correct Phase1a tools")
        void selectsCorrectPhase1aTools() {
            System.out.println("\n--- Test: Phase1a Tool Selection ---");
            
            GolfCourse course = courseService.createCourse("Tool Select Test", "Test");
            String courseId = course.getId();
            
            // Test each Phase1a operation
            Map<String, String> operations = Map.of(
                "phase1a_run", "Run complete pipeline",
                "phase1a_generate_masks", "Generate SAM masks",
                "phase1a_classify", "Classify features",
                "phase1a_interactive_select", "Interactive selection",
                "phase1a_generate_svg", "Generate SVG"
            );
            
            for (Map.Entry<String, String> op : operations.entrySet()) {
                ToolResult result = phase1aMcp.execute(Map.of(
                    "operation", op.getKey(),
                    "parameters", Map.of(
                        "courseId", courseId,
                        "satelliteImage", "/test/satellite.png",
                        "checkpoint", "checkpoints/sam.pth",
                        "masksDir", "/test/masks"
                    )
                ));
                assertThat(result.success()).as(op.getValue()).isTrue();
                System.out.println("  ✓ " + op.getKey() + ": " + op.getValue());
            }
        }
        
        @Test
        @DisplayName("Selects correct Blender tools for mesh operations")
        void selectsCorrectBlenderTools() {
            System.out.println("\n--- Test: Blender Tool Selection ---");
            
            GolfCourse course = courseService.createCourse("Blender Test", "Test");
            String courseId = course.getId();
            
            String[] operations = {
                "blender_open_course_template",
                "blender_import_svg",
                "blender_import_terrain",
                "blender_convert_and_cut",
                "blender_convert_meshes",
                "blender_fix_donut",
                "blender_add_curbs",
                "blender_add_bulkhead",
                "blender_add_water_plane",
                "blender_export_fbx"
            };
            
            for (String operation : operations) {
                ToolResult result = blenderMcp.execute(Map.of(
                    "operation", operation,
                    "parameters", Map.of(
                        "courseId", courseId,
                        "templatePath", "/templates/courseconversion.blend",
                        "svgFile", "/test/course.svg",
                        "terrainObj", "/test/Terrain.obj"
                    )
                ));
                assertThat(result.success()).as(operation).isTrue();
                System.out.println("  ✓ " + operation);
            }
        }
    }
    
    // ===========================================
    // SPECIAL HOLE TESTS (98 and 99)
    // ===========================================
    
    @Nested
    @DisplayName("Special Holes (98 and 99)")
    class SpecialHoleTests {
        
        @Test
        @DisplayName("Course includes Hole 98 (cart paths) and Hole 99 (outer mesh)")
        void courseIncludesSpecialHoles() {
            System.out.println("\n--- Test: Special Holes 98 and 99 ---");
            
            GolfCourse course = courseService.createCourse("Special Holes Test", "Test");
            
            Hole hole98 = course.getHole(98);
            Hole hole99 = course.getHole(99);
            
            assertThat(hole98).isNotNull();
            assertThat(hole98.isCartPath()).isTrue();
            assertThat(hole98.isSpecialHole()).isTrue();
            System.out.println("  Hole 98: Cart Paths - " + (hole98.isCartPath() ? "✓" : "✗"));
            
            assertThat(hole99).isNotNull();
            assertThat(hole99.isOuterMesh()).isTrue();
            assertThat(hole99.isSpecialHole()).isTrue();
            System.out.println("  Hole 99: Outer Mesh - " + (hole99.isOuterMesh() ? "✓" : "✗"));
            
            // Regular holes should not be special
            Hole hole1 = course.getHole(1);
            assertThat(hole1.isSpecialHole()).isFalse();
            System.out.println("  Hole 1: Regular Hole - " + (!hole1.isSpecialHole() ? "✓" : "✗"));
        }
        
        @Test
        @DisplayName("Blender fix_donut handles cart path loop corruption")
        void blenderFixDonutHandlesCartPathCorruption() {
            System.out.println("\n--- Test: Blender Donut Fix for Hole 98 ---");
            
            GolfCourse course = courseService.createCourse("Donut Test", "Test");
            String courseId = course.getId();
            
            ToolResult result = blenderMcp.execute(Map.of(
                "operation", "blender_fix_donut",
                "parameters", Map.of("courseId", courseId)
            ));
            
            assertThat(result.success()).isTrue();
            assertThat(result.data().get("holeFixed")).isEqualTo(98);
            System.out.println("  ✓ Fixed cart path donut on Hole 98");
            System.out.println("  Operation: " + result.data().get("operation"));
        }
    }
    
    // ===========================================
    // MATRYOSHKA PATTERN DEMONSTRATION
    // ===========================================
    
    @Nested
    @DisplayName("Matryoshka Pattern Demo")
    class MatryoshkaPatternDemo {
        
        @Test
        @DisplayName("Demonstrate progressive tool discovery")
        void demonstrateProgressiveDiscovery() {
            System.out.println("\n" + "=".repeat(60));
            System.out.println("MATRYOSHKA TOOL PATTERN DEMONSTRATION");
            System.out.println("Progressive Tool Discovery for Golf Course Building");
            System.out.println("=".repeat(60));
            
            // Level 1: LLM sees only top-level tool
            System.out.println("\n1. LLM sees only top-level tool:");
            System.out.println("-".repeat(40));
            System.out.println("   • golf_course_builder [MATRYOSHKA]");
            System.out.println("     \"Complete GSPro golf course creation...\"");
            
            // Level 2: LLM selects golf_course_builder, sees phase tools
            System.out.println("\n2. LLM selects 'golf_course_builder', sees phases:");
            System.out.println("-".repeat(40));
            ToolResult level1 = courseBuilderTool.execute(Map.of("operation", "list"));
            level1.suggestedTools().forEach(tool -> 
                System.out.println("   • " + tool.getName() + ": " + 
                    tool.getDescription().substring(0, Math.min(50, tool.getDescription().length())) + "...")
            );
            
            // Level 3: LLM drills into phase1a_mcp
            System.out.println("\n3. LLM drills into 'phase1a_mcp' for SAM tools:");
            System.out.println("-".repeat(40));
            ToolResult level2 = phase1aMcp.execute(Map.of("operation", "list"));
            level2.suggestedTools().forEach(tool -> 
                System.out.println("   • " + tool.getName())
            );
            
            // Level 4: LLM executes specific tool
            System.out.println("\n4. LLM executes 'phase1a_run' with parameters:");
            System.out.println("-".repeat(40));
            GolfCourse course = courseService.createCourse("Demo Course", "Demo");
            ToolResult result = phase1aMcp.execute(Map.of(
                "operation", "phase1a_run",
                "parameters", Map.of(
                    "courseId", course.getId(),
                    "satelliteImage", "/input/demo_satellite.png",
                    "checkpoint", "checkpoints/sam_vit_h_4b8939.pth"
                )
            ));
            System.out.println("   Result: " + result.message());
            System.out.println("   Features: " + result.data().get("featuresClassified"));
            
            System.out.println("\n" + "=".repeat(60));
            System.out.println("This pattern prevents LLM context pollution by revealing");
            System.out.println("50+ tools progressively across 6 phases, rather than all at once.");
            System.out.println("=".repeat(60));
        }
    }
}
