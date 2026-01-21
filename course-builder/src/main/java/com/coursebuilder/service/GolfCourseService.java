package com.coursebuilder.service;

import com.coursebuilder.model.GolfCourse;
import com.coursebuilder.model.Hole;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service for managing golf course projects.
 */
@Service
public class GolfCourseService {
    
    private static final Logger log = LoggerFactory.getLogger(GolfCourseService.class);
    
    private final Map<String, GolfCourse> courses = new ConcurrentHashMap<>();
    
    /**
     * Create a new golf course project.
     */
    public GolfCourse createCourse(String name, String location) {
        GolfCourse course = new GolfCourse(name, location);
        courses.put(course.getId(), course);
        log.info("Created golf course project: {} at {} (ID: {})", name, location, course.getId());
        return course;
    }
    
    /**
     * Get a course by ID.
     */
    public Optional<GolfCourse> getCourse(String courseId) {
        return Optional.ofNullable(courses.get(courseId));
    }
    
    /**
     * List all courses.
     */
    public List<GolfCourse> listCourses() {
        return new ArrayList<>(courses.values());
    }
    
    /**
     * Set geographic bounds for LIDAR data retrieval.
     */
    public void setBounds(String courseId, double northLat, double southLat, 
                          double eastLon, double westLon) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            course.setBounds(new GolfCourse.GeographicBounds(northLat, southLat, eastLon, westLon));
            log.info("Set bounds for course {}: N:{}, S:{}, E:{}, W:{}", 
                courseId, northLat, southLat, eastLon, westLon);
        }
    }
    
    /**
     * Update terrain data from LIDAR processing.
     */
    public void setTerrainData(String courseId, String heightmapPath, 
                               int resolution, double width, double length, double maxHeight) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            GolfCourse.TerrainData terrain = new GolfCourse.TerrainData();
            terrain.setHeightmapPath(heightmapPath);
            terrain.setHeightmapResolution(resolution);
            terrain.setWidth(width);
            terrain.setLength(length);
            terrain.setMaxHeight(maxHeight);
            course.setTerrain(terrain);
            log.info("Set terrain data for course {}: {}x{} at resolution {}", 
                courseId, width, length, resolution);
        }
    }
    
    /**
     * Add a feature to a hole.
     */
    public void addFeatureToHole(String courseId, int holeNumber, 
                                  Hole.CourseFeature.FeatureType featureType,
                                  List<Hole.CourseFeature.Point2D> points) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            Hole hole = course.getHole(holeNumber);
            if (hole != null) {
                Hole.CourseFeature feature = new Hole.CourseFeature(featureType);
                feature.setPoints(points);
                hole.addFeature(feature);
                log.info("Added {} to hole {} of course {}", featureType, holeNumber, courseId);
            }
        }
    }
    
    /**
     * Mark a hole as traced in Inkscape.
     */
    public void markHoleTraced(String courseId, int holeNumber, String svgLayerId) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            Hole hole = course.getHole(holeNumber);
            if (hole != null) {
                hole.setTraced(true);
                hole.setSvgLayerId(svgLayerId);
                log.info("Marked hole {} as traced for course {}", holeNumber, courseId);
            }
        }
    }
    
    /**
     * Store an artifact path.
     */
    public void setArtifact(String courseId, String artifactKey, String path) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            course.setArtifact(artifactKey, path);
            log.info("Set artifact {} = {} for course {}", artifactKey, path, courseId);
        }
    }
    
    /**
     * Advance to the next workflow phase.
     */
    public void advancePhase(String courseId) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            GolfCourse.WorkflowState state = course.getWorkflowState();
            GolfCourse.WorkflowState.Phase current = state.getCurrentPhase();
            
            // Complete the current gate
            state.completeGate(current.getGate());
            
            // Move to next phase
            GolfCourse.WorkflowState.Phase[] phases = GolfCourse.WorkflowState.Phase.values();
            int nextIndex = current.ordinal() + 1;
            if (nextIndex < phases.length) {
                state.setCurrentPhase(phases[nextIndex]);
                log.info("Course {} advanced to phase: {}", courseId, phases[nextIndex].getName());
            }
        }
    }
    
    /**
     * Complete a workflow step.
     */
    public void completeStep(String courseId, String stepName) {
        GolfCourse course = courses.get(courseId);
        if (course != null) {
            course.getWorkflowState().completeStep(stepName);
            log.info("Completed step '{}' for course {}", stepName, courseId);
        }
    }
    
    /**
     * Get workflow progress summary.
     */
    public Map<String, Object> getWorkflowProgress(String courseId) {
        GolfCourse course = courses.get(courseId);
        if (course == null) {
            return Map.of("error", "Course not found");
        }
        
        GolfCourse.WorkflowState state = course.getWorkflowState();
        int totalHoles = 20; // 18 + hole 98 + hole 99
        long tracedHoles = course.getHoles().stream().filter(Hole::isTraced).count();
        
        return Map.of(
            "courseId", courseId,
            "courseName", course.getName(),
            "currentPhase", state.getCurrentPhase().getName(),
            "phaseNumber", state.getCurrentPhase().getNumber(),
            "completedSteps", state.getCompletedSteps().size(),
            "holesTraced", tracedHoles,
            "totalHoles", totalHoles,
            "artifacts", course.getArtifacts()
        );
    }
}
