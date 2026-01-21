package com.coursebuilder.model;

import java.time.Instant;
import java.util.*;

/**
 * Represents a golf course being built for GSPro.
 * 
 * The course goes through the "None to Done" workflow:
 * LIDAR → Unity (Terrain) → Inkscape (SVG) → Unity (PNG) → Blender (Mesh) → Unity (Final)
 */
public class GolfCourse {
    
    private String id;
    private String name;
    private String location;
    private GeographicBounds bounds;
    private TerrainData terrain;
    private List<Hole> holes;
    private WorkflowState workflowState;
    private Map<String, String> artifacts;  // file paths for generated artifacts
    private Instant createdAt;
    private Instant updatedAt;
    
    public GolfCourse() {
        this.id = UUID.randomUUID().toString();
        this.holes = new ArrayList<>();
        this.artifacts = new HashMap<>();
        this.workflowState = new WorkflowState();
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        
        // Initialize 18 holes + special holes
        for (int i = 1; i <= 18; i++) {
            holes.add(new Hole(i));
        }
        holes.add(new Hole(98));  // Cart paths
        holes.add(new Hole(99));  // Outer mesh
    }
    
    public GolfCourse(String name, String location) {
        this();
        this.name = name;
        this.location = location;
    }
    
    // Getters and setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    
    public String getName() { return name; }
    public void setName(String name) { 
        this.name = name;
        this.updatedAt = Instant.now();
    }
    
    public String getLocation() { return location; }
    public void setLocation(String location) { this.location = location; }
    
    public GeographicBounds getBounds() { return bounds; }
    public void setBounds(GeographicBounds bounds) { this.bounds = bounds; }
    
    public TerrainData getTerrain() { return terrain; }
    public void setTerrain(TerrainData terrain) { this.terrain = terrain; }
    
    public List<Hole> getHoles() { return holes; }
    
    public Hole getHole(int number) {
        return holes.stream()
            .filter(h -> h.getNumber() == number)
            .findFirst()
            .orElse(null);
    }
    
    public WorkflowState getWorkflowState() { return workflowState; }
    
    public Map<String, String> getArtifacts() { return artifacts; }
    
    public void setArtifact(String key, String path) {
        artifacts.put(key, path);
        this.updatedAt = Instant.now();
    }
    
    public String getArtifact(String key) {
        return artifacts.get(key);
    }
    
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    
    /**
     * Geographic bounds for the course (for LIDAR data retrieval).
     */
    public static class GeographicBounds {
        private double northLat;
        private double southLat;
        private double eastLon;
        private double westLon;
        
        public GeographicBounds() {}
        
        public GeographicBounds(double northLat, double southLat, double eastLon, double westLon) {
            this.northLat = northLat;
            this.southLat = southLat;
            this.eastLon = eastLon;
            this.westLon = westLon;
        }
        
        public double getNorthLat() { return northLat; }
        public void setNorthLat(double northLat) { this.northLat = northLat; }
        public double getSouthLat() { return southLat; }
        public void setSouthLat(double southLat) { this.southLat = southLat; }
        public double getEastLon() { return eastLon; }
        public void setEastLon(double eastLon) { this.eastLon = eastLon; }
        public double getWestLon() { return westLon; }
        public void setWestLon(double westLon) { this.westLon = westLon; }
    }
    
    /**
     * Terrain data generated from LIDAR.
     */
    public static class TerrainData {
        private String heightmapPath;
        private int heightmapResolution;
        private double width;
        private double length;
        private double maxHeight;
        private String terrainObjPath;
        
        public String getHeightmapPath() { return heightmapPath; }
        public void setHeightmapPath(String path) { this.heightmapPath = path; }
        public int getHeightmapResolution() { return heightmapResolution; }
        public void setHeightmapResolution(int resolution) { this.heightmapResolution = resolution; }
        public double getWidth() { return width; }
        public void setWidth(double width) { this.width = width; }
        public double getLength() { return length; }
        public void setLength(double length) { this.length = length; }
        public double getMaxHeight() { return maxHeight; }
        public void setMaxHeight(double height) { this.maxHeight = height; }
        public String getTerrainObjPath() { return terrainObjPath; }
        public void setTerrainObjPath(String path) { this.terrainObjPath = path; }
    }
    
    /**
     * Tracks the workflow state through all 6 phases.
     */
    public static class WorkflowState {
        private Phase currentPhase;
        private int currentStep;
        private Map<String, Boolean> gatesCompleted;
        private List<String> completedSteps;
        private String lastError;
        
        public WorkflowState() {
            this.currentPhase = Phase.TERRAIN_CREATION;
            this.currentStep = 1;
            this.gatesCompleted = new HashMap<>();
            this.completedSteps = new ArrayList<>();
        }
        
        public Phase getCurrentPhase() { return currentPhase; }
        public void setCurrentPhase(Phase phase) { this.currentPhase = phase; }
        public int getCurrentStep() { return currentStep; }
        public void setCurrentStep(int step) { this.currentStep = step; }
        
        public void completeGate(String gateName) {
            gatesCompleted.put(gateName, true);
        }
        
        public boolean isGateCompleted(String gateName) {
            return gatesCompleted.getOrDefault(gateName, false);
        }
        
        public void completeStep(String stepName) {
            completedSteps.add(stepName);
        }
        
        public List<String> getCompletedSteps() { return completedSteps; }
        
        public String getLastError() { return lastError; }
        public void setLastError(String error) { this.lastError = error; }
        
        public enum Phase {
            TERRAIN_CREATION(1, "Terrain Creation", "terrain_ready"),
            COURSE_TRACING(2, "Course Tracing", "svg_complete"),
            TERRAIN_REFINEMENT(3, "Terrain Refinement", "terrain_exported"),
            SVG_CONVERSION(4, "SVG Conversion", "svg_converted"),
            BLENDER_PROCESSING(5, "Blender Processing", "fbx_exported"),
            UNITY_ASSEMBLY(6, "Unity Assembly", "course_complete");
            
            private final int number;
            private final String name;
            private final String gate;
            
            Phase(int number, String name, String gate) {
                this.number = number;
                this.name = name;
                this.gate = gate;
            }
            
            public int getNumber() { return number; }
            public String getName() { return name; }
            public String getGate() { return gate; }
        }
    }
}
