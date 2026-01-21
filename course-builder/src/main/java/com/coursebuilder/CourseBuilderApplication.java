package com.coursebuilder;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Course Builder Application with Matryoshka Tool Pattern
 * 
 * This application demonstrates the nested tools pattern (Matryoshka tools)
 * for building AI-powered course content. The pattern allows hierarchical
 * organization of tools to prevent overwhelming LLMs with too many options.
 * 
 * Key concepts:
 * - Agents: High-level coordinators that understand user intent
 * - Matryoshka Tools: Nested tool hierarchies (like Russian dolls)
 * - Tool Discovery: Dynamic tool selection based on context
 */
@SpringBootApplication
public class CourseBuilderApplication {
    
    public static void main(String[] args) {
        SpringApplication.run(CourseBuilderApplication.class, args);
    }
}
