package com.coursebuilder.tool;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Annotation to mark a method as an LLM-callable tool.
 * 
 * Methods annotated with @LlmTool can be discovered and invoked
 * by the AI agent system. The method parameters become the tool's
 * input schema.
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface LlmTool {
    
    /**
     * Name of the tool. If not specified, uses the method name.
     */
    String name() default "";
    
    /**
     * Description of what the tool does. This is shown to the LLM.
     */
    String description();
    
    /**
     * Category for grouping related tools.
     */
    String category() default "general";
    
    /**
     * Whether this tool should be hidden at the top level
     * and only exposed through a Matryoshka parent.
     */
    boolean nested() default false;
}
