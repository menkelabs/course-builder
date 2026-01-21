package com.coursebuilder.model;

import java.util.*;

/**
 * Represents a hole on the golf course.
 * 
 * Special holes:
 * - Hole 98: Cart paths (features that cut through other objects)
 * - Hole 99: Outer mesh (deep rough spanning multiple holes)
 */
public class Hole {
    
    private int number;
    private int par;
    private int yardage;
    private List<CourseFeature> features;
    private String svgLayerId;
    private String meshPath;
    private boolean traced;
    private boolean meshConverted;
    
    public Hole(int number) {
        this.number = number;
        this.features = new ArrayList<>();
        this.traced = false;
        this.meshConverted = false;
        
        // Set default par based on hole number
        if (number >= 1 && number <= 18) {
            this.par = 4; // Default, would be configured per course
        }
    }
    
    public int getNumber() { return number; }
    
    public int getPar() { return par; }
    public void setPar(int par) { this.par = par; }
    
    public int getYardage() { return yardage; }
    public void setYardage(int yardage) { this.yardage = yardage; }
    
    public List<CourseFeature> getFeatures() { return features; }
    
    public void addFeature(CourseFeature feature) {
        features.add(feature);
    }
    
    public List<CourseFeature> getFeaturesByType(CourseFeature.FeatureType type) {
        return features.stream()
            .filter(f -> f.getType() == type)
            .toList();
    }
    
    public String getSvgLayerId() { return svgLayerId; }
    public void setSvgLayerId(String id) { this.svgLayerId = id; }
    
    public String getMeshPath() { return meshPath; }
    public void setMeshPath(String path) { this.meshPath = path; }
    
    public boolean isTraced() { return traced; }
    public void setTraced(boolean traced) { this.traced = traced; }
    
    public boolean isMeshConverted() { return meshConverted; }
    public void setMeshConverted(boolean converted) { this.meshConverted = converted; }
    
    public boolean isSpecialHole() {
        return number == 98 || number == 99;
    }
    
    public boolean isCartPath() {
        return number == 98;
    }
    
    public boolean isOuterMesh() {
        return number == 99;
    }
    
    /**
     * Represents a feature/shape on the hole (fairway, green, bunker, etc.)
     */
    public static class CourseFeature {
        private String id;
        private FeatureType type;
        private List<Point2D> points;
        private String fillColor;
        private String svgPath;
        
        public CourseFeature() {
            this.id = UUID.randomUUID().toString();
            this.points = new ArrayList<>();
        }
        
        public CourseFeature(FeatureType type) {
            this();
            this.type = type;
            this.fillColor = type.getDefaultColor();
        }
        
        public String getId() { return id; }
        
        public FeatureType getType() { return type; }
        public void setType(FeatureType type) { 
            this.type = type;
            this.fillColor = type.getDefaultColor();
        }
        
        public List<Point2D> getPoints() { return points; }
        public void setPoints(List<Point2D> points) { this.points = points; }
        public void addPoint(double x, double y) { points.add(new Point2D(x, y)); }
        
        public String getFillColor() { return fillColor; }
        public void setFillColor(String color) { this.fillColor = color; }
        
        public String getSvgPath() { return svgPath; }
        public void setSvgPath(String path) { this.svgPath = path; }
        
        /**
         * Feature types with their default colors from the GSPro palette.
         */
        public enum FeatureType {
            TEE("Tee Box", "#00FF00"),
            FAIRWAY("Fairway", "#90EE90"),
            ROUGH("Rough", "#228B22"),
            SEMI_ROUGH("Semi Rough", "#32CD32"),
            DEEP_ROUGH("Deep Rough", "#006400"),
            GREEN("Green", "#98FB98"),
            FRINGE("Fringe", "#7CFC00"),
            BUNKER("Bunker", "#F4A460"),
            WATER("Water", "#4169E1"),
            CART_PATH("Cart Path", "#808080"),
            OUT_OF_BOUNDS("Out of Bounds", "#FF0000");
            
            private final String displayName;
            private final String defaultColor;
            
            FeatureType(String displayName, String defaultColor) {
                this.displayName = displayName;
                this.defaultColor = defaultColor;
            }
            
            public String getDisplayName() { return displayName; }
            public String getDefaultColor() { return defaultColor; }
        }
        
        public static class Point2D {
            private double x;
            private double y;
            
            public Point2D() {}
            
            public Point2D(double x, double y) {
                this.x = x;
                this.y = y;
            }
            
            public double getX() { return x; }
            public void setX(double x) { this.x = x; }
            public double getY() { return y; }
            public void setY(double y) { this.y = y; }
        }
    }
}
