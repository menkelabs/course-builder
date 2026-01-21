package com.coursebuilder.tool;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Annotation to mark a class as containing nested Matryoshka tools.
 * 
 * When a class is annotated with @MatryoshkaTools, all @LlmTool methods
 * within it are grouped under a single parent tool. This prevents
 * flooding the LLM context with too many individual tools.
 * 
 * Example:
 * <pre>
 * {@literal @}MatryoshkaTools(
 *     name = "content_creation",
 *     description = "Tools for creating course content"
 * )
 * public class ContentCreationTools {
 *     
 *     {@literal @}LlmTool(description = "Create a lesson")
 *     public Lesson createLesson(String title, String content) { ... }
 *     
 *     {@literal @}LlmTool(description = "Create a quiz")
 *     public Quiz createQuiz(List<Question> questions) { ... }
 * }
 * </pre>
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
public @interface MatryoshkaTools {
    
    /**
     * Name of the parent tool that contains the nested tools.
     */
    String name();
    
    /**
     * Description of the tool group. This is what the LLM sees
     * before drilling down into specific tools.
     */
    String description();
    
    /**
     * Category for the tool group.
     */
    String category() default "general";
}
