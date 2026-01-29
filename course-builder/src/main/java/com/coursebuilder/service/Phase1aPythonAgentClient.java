package com.coursebuilder.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * HTTP client for the Python agent (Phase 1A remote actions).
 * When {@code coursebuilder.python-agent.url} is set, Phase1a Matryoshka tools delegate here
 * instead of mocks. When unset, {@link #execute} returns null and tools use mocks.
 *
 * Expects Python agent at {@code coursebuilder.python-agent.url}, e.g. {@code http://localhost:8000}.
 * API: POST /api/v1/actions/execute with {@code {"action_name": "...", "parameters": {...}}}.
 * Parameters use snake_case; this client converts from Java camelCase.
 */
@Component
public class Phase1aPythonAgentClient {

    private static final Logger log = LoggerFactory.getLogger(Phase1aPythonAgentClient.class);
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Pattern CAMEL = Pattern.compile("([a-z])([A-Z]+)");

    private final WebClient webClient;
    private final String baseUrl;
    private final boolean enabled;

    public Phase1aPythonAgentClient(@Value("${coursebuilder.python-agent.url:}") String baseUrl) {
        this.baseUrl = (baseUrl != null ? baseUrl : "").strip().replaceAll("/$", "");
        this.enabled = !this.baseUrl.isBlank();
        this.webClient = this.enabled
                ? WebClient.builder().baseUrl(this.baseUrl).defaultHeader("Content-Type", "application/json").build()
                : null;
        if (this.enabled) {
            log.info("Phase1a Python agent client configured: {}", this.baseUrl);
        } else {
            log.debug("Phase1a Python agent URL not set; Phase1a tools will use mocks.");
        }
    }

    /**
     * Execute a Phase 1A action via the Python agent.
     *
     * @param actionName e.g. phase1a_run, phase1a_generate_masks
     * @param params     Java-style params (camelCase). Converted to snake_case for Python.
     * @return result map (snake_case keys) or null on error / non-2xx
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> execute(String actionName, Map<String, Object> params) {
        if (!enabled || webClient == null) {
            return null;
        }
        Map<String, Object> snakeParams = toSnakeCaseMap(params);
        Map<String, Object> body = Map.of(
                "action_name", actionName,
                "parameters", snakeParams
        );
        try {
            String json = webClient.post()
                    .uri("/api/v1/actions/execute")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(body)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();
            if (json == null || json.isBlank()) {
                return null;
            }
            JsonNode root = JSON.readTree(json);
            JsonNode status = root.path("status");
            if (!status.asText().equals("success")) {
                log.warn("Python agent action {} returned status {}", actionName, status.asText());
                return null;
            }
            JsonNode result = root.path("result");
            return result.isObject() ? JSON.convertValue(result, Map.class) : Map.of();
        } catch (WebClientResponseException e) {
            log.warn("Python agent action {} failed: {} {}", actionName, e.getStatusCode(), e.getResponseBodyAsString());
            return null;
        } catch (Exception e) {
            log.warn("Python agent action {} error: {}", actionName, e.getMessage());
            return null;
        }
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Convert camelCase keys to snake_case. Nested maps are not recursed.
     */
    static Map<String, Object> toSnakeCaseMap(Map<String, Object> in) {
        Map<String, Object> out = new HashMap<>();
        for (Map.Entry<String, Object> e : in.entrySet()) {
            out.put(toSnakeCase(e.getKey()), e.getValue());
        }
        return out;
    }

    static String toSnakeCase(String camel) {
        Matcher m = CAMEL.matcher(camel);
        return m.replaceAll("$1_$2").toLowerCase();
    }
}
