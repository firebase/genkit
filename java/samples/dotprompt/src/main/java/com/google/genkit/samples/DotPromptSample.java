/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.samples;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.*;
import com.google.genkit.core.Flow;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;
import com.google.genkit.prompt.DotPrompt;
import com.google.genkit.prompt.ExecutablePrompt;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * Sample application demonstrating Genkit DotPrompt files with complex inputs and outputs.
 *
 * <p>This example shows how to:
 * <ul>
 *   <li>Load and use .prompt files with Handlebars templates</li>
 *   <li>Work with complex input schemas (nested objects, arrays)</li>
 *   <li>Work with complex output schemas (JSON structures)</li>
 *   <li>Use prompt variants (e.g., recipe.robot.prompt)</li>
 *   <li>Use partial templates (e.g., _style.prompt)</li>
 * </ul>
 *
 * <p>To run:
 * <ol>
 *   <li>Set the OPENAI_API_KEY environment variable</li>
 *   <li>Run: mvn exec:java</li>
 * </ol>
 */
public class DotPromptSample {

    private static final Logger logger = LoggerFactory.getLogger(DotPromptSample.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Extracts JSON from a string that may be wrapped in markdown code blocks.
     * Handles formats like: ```json\n{...}\n``` or ```\n{...}\n``` or just {...}
     * Also handles nested wrapper objects like {"recipe": {...}} or {"result": {...}}
     * If no JSON is found, looks for JSON embedded in the text.
     */
    private static String extractJson(String text) {
        if (text == null) return null;
        String trimmed = text.trim();
        
        // Check for ```json or ``` markers
        if (trimmed.startsWith("```")) {
            // Find the end of the first line (after ```json or ```)
            int firstNewline = trimmed.indexOf('\n');
            if (firstNewline == -1) return trimmed;
            
            // Find the closing ```
            int lastBackticks = trimmed.lastIndexOf("```");
            if (lastBackticks > firstNewline) {
                trimmed = trimmed.substring(firstNewline + 1, lastBackticks).trim();
            }
        }
        
        // If the text doesn't start with { or [, try to find JSON embedded in it
        if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
            // Look for JSON object in the text
            int jsonStart = trimmed.indexOf('{');
            int jsonEnd = trimmed.lastIndexOf('}');
            if (jsonStart >= 0 && jsonEnd > jsonStart) {
                trimmed = trimmed.substring(jsonStart, jsonEnd + 1);
            } else {
                // Look for JSON array
                jsonStart = trimmed.indexOf('[');
                jsonEnd = trimmed.lastIndexOf(']');
                if (jsonStart >= 0 && jsonEnd > jsonStart) {
                    trimmed = trimmed.substring(jsonStart, jsonEnd + 1);
                }
            }
        }
        
        // Try to unwrap common wrapper keys like "recipe", "result", "data"
        try {
            Map<String, Object> wrapped = objectMapper.readValue(trimmed, Map.class);
            if (wrapped.size() == 1) {
                String key = wrapped.keySet().iterator().next();
                if (key.equalsIgnoreCase("recipe") || key.equalsIgnoreCase("result") || 
                    key.equalsIgnoreCase("data") || key.equalsIgnoreCase("response") ||
                    key.equalsIgnoreCase("itinerary") || key.equalsIgnoreCase("trip")) {
                    Object inner = wrapped.get(key);
                    if (inner instanceof Map) {
                        return objectMapper.writeValueAsString(inner);
                    }
                }
            }
        } catch (Exception e) {
            // Not valid JSON or not a wrapper object, return as-is
        }
        
        return trimmed;
    }

    public static void main(String[] args) throws Exception {
        // Create the Jetty server plugin
        JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder()
                .port(8080)
                .build());

        // Create Genkit with plugins
        Genkit genkit = Genkit.builder()
                .options(GenkitOptions.builder()
                        .devMode(true)
                        .reflectionPort(3100)
                        .promptDir("/prompts")  // Configure prompt directory (default is /prompts)
                        .build())
                .plugin(OpenAIPlugin.create())
                .plugin(jetty)
                .build();

        // ============================================================
        // Method 1: Load prompts using genkit.prompt() - Recommended!
        // Similar to JavaScript: const helloPrompt = ai.prompt('hello');
        // ============================================================
        
        // Load and auto-register prompts using genkit.prompt()
        // This automatically loads from /prompts directory and registers as actions
        ExecutablePrompt<StoryInput> storyPrompt = genkit.prompt("story", StoryInput.class);
        ExecutablePrompt<TravelInput> travelPrompt = genkit.prompt("travel-planner", TravelInput.class);
        ExecutablePrompt<CodeReviewInput> codeReviewPrompt = genkit.prompt("code-review", CodeReviewInput.class);
        
        // Load prompt with variant (e.g., recipe.robot.prompt)
        ExecutablePrompt<RecipeInput> robotRecipePrompt = genkit.prompt("recipe", RecipeInput.class, "robot");
        
        // ============================================================
        // Method 2: Load prompts manually using DotPrompt.loadFromResource()
        // Useful when you need more control over the loading process
        // ============================================================
        DotPrompt<RecipeInput> recipePrompt = DotPrompt.loadFromResource("/prompts/recipe.prompt");

        // ============================================================
        // Flow Examples: Different ways to use prompts
        // ============================================================

        // Flow using DotPrompt.render() + manual generate
        Flow<RecipeInput, Recipe, Void> chefFlow = genkit.defineFlow(
                "chefFlow",
                RecipeInput.class,
                Recipe.class,
                (ctx, input) -> {
                    // Validate input
                    if (input == null || input.getFood() == null || input.getFood().isEmpty()) {
                        throw new IllegalArgumentException("Input 'food' is required. Example: {\"food\": \"pasta\", \"ingredients\": [\"tomatoes\", \"basil\"]}");
                    }

                    // Render the prompt
                    String prompt = recipePrompt.render(input);
                    logger.info("Generated prompt: {}", prompt);

                    // Generate response
                    ModelResponse response = genkit.generate(
                            GenerateOptions.builder()
                                    .model("openai/gpt-5.2")
                                    .prompt(prompt)
                                    .config(GenerationConfig.builder()
                                            .temperature(0.7)
                                            .build())
                                    .build());

                    // Parse JSON response to Recipe object (extract from markdown if needed)
                    String jsonResponse = extractJson(response.getText());
                    logger.debug("Extracted JSON: {}", jsonResponse);
                    try {
                        return objectMapper.readValue(jsonResponse, Recipe.class);
                    } catch (JsonProcessingException e) {
                        throw new RuntimeException("Failed to parse recipe response: " + jsonResponse, e);
                    }
                });

        // Flow using ExecutablePrompt.generate() - Direct generation!
        // This is the recommended approach - similar to JS: const { text } = await helloPrompt({ name: 'John' });
        Flow<RecipeInput, Recipe, Void> robotChefFlow = genkit.defineFlow(
                "robotChefFlow",
                RecipeInput.class,
                Recipe.class,
                (ctx, input) -> {
                    // Generate directly from the prompt - no need to manually call genkit.generate()!
                    ModelResponse response = robotRecipePrompt.generate(input);
                    
                    try {
                        return objectMapper.readValue(extractJson(response.getText()), Recipe.class);
                    } catch (JsonProcessingException e) {
                        throw new RuntimeException("Failed to parse recipe response", e);
                    }
                });

        // Flow for story telling using ExecutablePrompt.generate() with custom options
        // Demonstrates overriding generation config at call time
        Flow<StoryInput, String, Void> tellStoryFlow = genkit.defineFlow(
                "tellStory",
                StoryInput.class,
                String.class,
                (ctx, input) -> {
                    // Generate with custom temperature override
                    ModelResponse response = storyPrompt.generate(input, 
                            GenerateOptions.builder()
                                    .config(GenerationConfig.builder()
                                            .temperature(0.9)
                                            .build())
                                    .build());
                    return response.getText();
                });

        // Flow for travel planning using ExecutablePrompt.generate()
        Flow<TravelInput, TravelItinerary, Void> planTripFlow = genkit.defineFlow(
                "planTrip",
                TravelInput.class,
                TravelItinerary.class,
                (ctx, input) -> {
                    // Direct generation from ExecutablePrompt
                    ModelResponse response = travelPrompt.generate(input,
                            GenerateOptions.builder()
                                    .config(GenerationConfig.builder()
                                            .temperature(0.7)
                                            .build())
                                    .build());
                    try {
                        return objectMapper.readValue(extractJson(response.getText()), TravelItinerary.class);
                    } catch (JsonProcessingException e) {
                        throw new RuntimeException("Failed to parse travel itinerary response", e);
                    }
                });

        // Flow for code review using ExecutablePrompt.generate()
        Flow<CodeReviewInput, CodeReview, Void> reviewCodeFlow = genkit.defineFlow(
                "reviewCode",
                CodeReviewInput.class,
                CodeReview.class,
                (ctx, input) -> {
                    // Direct generation with lower temperature for more focused analysis
                    ModelResponse response = codeReviewPrompt.generate(input,
                            GenerateOptions.builder()
                                    .config(GenerationConfig.builder()
                                            .temperature(0.3)
                                            .build())
                                    .build());
                    try {
                        return objectMapper.readValue(extractJson(response.getText()), CodeReview.class);
                    } catch (JsonProcessingException e) {
                        throw new RuntimeException("Failed to parse code review response", e);
                    }
                });

        logger.info("=".repeat(60));
        logger.info("Genkit DotPrompt Sample Started");
        logger.info("=".repeat(60));
        logger.info("");
        logger.info("Available flows:");
        logger.info("  - chefFlow: Generate recipes from food and ingredients");
        logger.info("  - robotChefFlow: Generate recipes with robot personality");
        logger.info("  - tellStory: Generate stories with optional personality");
        logger.info("  - planTrip: Generate detailed travel itineraries");
        logger.info("  - reviewCode: Analyze and review code");
        logger.info("");
        logger.info("Example calls:");
        logger.info("  curl -X POST http://localhost:8080/chefFlow \\");
        logger.info("    -H 'Content-Type: application/json' \\");
        logger.info("    -d '{\"food\":\"pasta\",\"ingredients\":[\"tomatoes\",\"basil\"]}'");
        logger.info("");
        logger.info("  curl -X POST http://localhost:8080/tellStory \\");
        logger.info("    -H 'Content-Type: application/json' \\");
        logger.info("    -d '{\"subject\":\"a brave knight\",\"personality\":\"dramatic\"}'");
        logger.info("");
        logger.info("  curl -X POST http://localhost:8080/planTrip \\");
        logger.info("    -H 'Content-Type: application/json' \\");
        logger.info("    -d '{\"destination\":\"Tokyo\",\"duration\":5,\"budget\":\"$3000\",\"interests\":[\"food\",\"culture\"]}'");
        logger.info("");
        logger.info("Reflection API: http://localhost:3100");
        logger.info("HTTP API: http://localhost:8080");
        logger.info("=".repeat(60));

        // Start the server and block - keeps the application running
        jetty.start();
    }
}
