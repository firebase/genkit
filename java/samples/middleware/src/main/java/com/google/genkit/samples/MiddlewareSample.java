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

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.*;
import com.google.genkit.core.Flow;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.middleware.*;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating Genkit middleware support.
 *
 * <p>
 * This example shows how to:
 * <ul>
 * <li>Create custom middleware for logging, timing, and metrics</li>
 * <li>Use built-in middleware from CommonMiddleware</li>
 * <li>Chain multiple middleware together</li>
 * <li>Apply middleware to flows</li>
 * <li>Create reusable middleware for cross-cutting concerns</li>
 * </ul>
 *
 * <p>
 * To run:
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable</li>
 * <li>Run: mvn exec:java</li>
 * </ol>
 */
public class MiddlewareSample {

  private static final Logger logger = LoggerFactory.getLogger(MiddlewareSample.class);

  // Metrics storage for demonstration
  private static final Map<String, AtomicLong> requestCounts = new ConcurrentHashMap<>();
  private static final Map<String, List<Long>> responseTimes = new ConcurrentHashMap<>();

  public static void main(String[] args) throws Exception {
    // Create the Jetty server plugin
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // Create Genkit with plugins
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).plugin(jetty).build();

    // =======================================================
    // Example 1: Simple logging middleware
    // =======================================================

    // Create a list of middleware for the flow
    List<Middleware<String, String>> loggingMiddleware = List.of(CommonMiddleware.logging("greeting"));

    // Define flow with logging middleware
    Flow<String, String, Void> greetingFlow = genkit.defineFlow("greeting", String.class, String.class,
        (ctx, name) -> "Hello, " + name + "!", loggingMiddleware);

    // =======================================================
    // Example 2: Custom metrics middleware
    // =======================================================

    // Custom middleware that collects metrics
    Middleware<String, String> metricsMiddleware = (request, context, next) -> {
      String flowName = "chat";
      requestCounts.computeIfAbsent(flowName, k -> new AtomicLong(0)).incrementAndGet();

      long start = System.currentTimeMillis();
      try {
        String result = next.apply(request, context);
        long duration = System.currentTimeMillis() - start;
        responseTimes.computeIfAbsent(flowName, k -> new ArrayList<>()).add(duration);
        return result;
      } catch (GenkitException e) {
        logger.error("Flow {} failed: {}", flowName, e.getMessage());
        throw e;
      }
    };

    // =======================================================
    // Example 3: Request/Response transformation middleware
    // =======================================================

    // Middleware that sanitizes input (removes extra whitespace, trims)
    Middleware<String, String> sanitizeMiddleware = CommonMiddleware.transformRequest(input -> {
      if (input == null) {
        return "";
      }
      return input.trim().replaceAll("\\s+", " ");
    });

    // Middleware that formats output
    Middleware<String, String> formatMiddleware = CommonMiddleware.transformResponse(output -> {
      return "[" + Instant.now() + "] " + output;
    });

    // =======================================================
    // Example 4: Validation middleware
    // =======================================================

    Middleware<String, String> validationMiddleware = CommonMiddleware.validate(input -> {
      if (input == null || input.trim().isEmpty()) {
        throw new GenkitException("Input cannot be empty");
      }
      if (input.length() > 1000) {
        throw new GenkitException("Input too long (max 1000 characters)");
      }
    });

    // =======================================================
    // Example 5: Chat flow with multiple middleware
    // =======================================================

    // Combine multiple middleware
    List<Middleware<String, String>> chatMiddleware = List.of(CommonMiddleware.logging("chat"), // Log
        // requests/responses
        metricsMiddleware, // Collect metrics
        sanitizeMiddleware, // Sanitize input
        validationMiddleware, // Validate input
        CommonMiddleware.retry(2, 100) // Retry on failure
    );

    // Define chat flow with middleware chain
    Flow<String, String, Void> chatFlow = genkit.defineFlow("chat", String.class, String.class,
        (ctx, userMessage) -> {
          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .system("You are a helpful assistant. Be concise.").prompt(userMessage)
              .config(GenerationConfig.builder().temperature(0.7).maxOutputTokens(200).build()).build());
          return response.getText();
        }, chatMiddleware);

    // =======================================================
    // Example 6: Caching middleware for expensive operations
    // =======================================================

    // Create a cache with 5 minute TTL
    SimpleCache<String> factCache = new SimpleCache<>(5 * 60 * 1000);

    List<Middleware<String, String>> factMiddleware = List.of(CommonMiddleware.logging("fact"),
        CommonMiddleware.cache(factCache, request -> request.toLowerCase()) // Cache by lowercase input
    );

    Flow<String, String, Void> factFlow = genkit.defineFlow("fact", String.class, String.class, (ctx, topic) -> {
      logger.info("Generating fact for: {} (not cached)", topic);
      ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
          .prompt("Give me an interesting fact about: " + topic + ". Keep it to one sentence.").build());
      return response.getText();
    }, factMiddleware);

    // =======================================================
    // Example 7: Rate limiting middleware
    // =======================================================

    List<Middleware<String, String>> rateLimitedMiddleware = List.of(CommonMiddleware.logging("joke"),
        CommonMiddleware.rateLimit(10, 60000) // Max 10 requests per minute
    );

    Flow<String, String, Void> jokeFlow = genkit.defineFlow("joke", String.class, String.class, (ctx, topic) -> {
      ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
          .prompt("Tell me a short, funny joke about: " + topic)
          .config(GenerationConfig.builder().temperature(0.9).build()).build());
      return response.getText();
    }, rateLimitedMiddleware);

    // =======================================================
    // Example 8: Conditional middleware
    // =======================================================

    // Only log if the request contains "debug"
    Middleware<String, String> conditionalLogging = CommonMiddleware.conditional(
        (request, ctx) -> request.toLowerCase().contains("debug"), CommonMiddleware.logging("debug-echo"));

    List<Middleware<String, String>> echoMiddleware = List.of(conditionalLogging);

    Flow<String, String, Void> echoFlow = genkit.defineFlow("echo", String.class, String.class,
        (ctx, input) -> "Echo: " + input, echoMiddleware);

    // =======================================================
    // Example 9: Before/After hooks
    // =======================================================

    List<Middleware<String, String>> hookMiddleware = List.of(CommonMiddleware.beforeAfter(
        (request, ctx) -> logger.info("🚀 Starting analysis of: {}", request),
        (response, ctx) -> logger.info("✅ Analysis complete, response length: {} chars", response.length())),
        CommonMiddleware.timing(duration -> {
          logger.info("⏱️ Analysis took {}ms", duration);
        }));

    Flow<String, String, Void> analyzeFlow = genkit.defineFlow("analyze", String.class, String.class,
        (ctx, topic) -> {
          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .prompt("Provide a brief analysis of the topic: " + topic)
              .config(GenerationConfig.builder().maxOutputTokens(300).build()).build());
          return response.getText();
        }, hookMiddleware);

    // =======================================================
    // Example 10: Error handling middleware
    // =======================================================

    Middleware<String, String> errorHandling = CommonMiddleware.errorHandler(e -> {
      logger.error("Flow failed with error: {}", e.getMessage());
      return "Sorry, I encountered an error: " + e.getMessage();
    });

    List<Middleware<String, String>> safeMiddleware = List.of(errorHandling, // This goes first to catch errors from
        // other middleware
        CommonMiddleware.logging("safe"));

    Flow<String, String, Void> safeFlow = genkit.defineFlow("safe", String.class, String.class, (ctx, input) -> {
      if (input.equals("error")) {
        throw new GenkitException("Intentional error for demonstration");
      }
      return "Safe result: " + input;
    }, safeMiddleware);

    // =======================================================
    // Example 11: Metrics endpoint flow
    // =======================================================

    Flow<Void, String, Void> metricsFlow = genkit.defineFlow("metrics", Void.class, String.class, (ctx, input) -> {
      StringBuilder sb = new StringBuilder();
      sb.append("=== Middleware Sample Metrics ===\n\n");

      sb.append("Request Counts:\n");
      requestCounts
          .forEach((flow, count) -> sb.append("  ").append(flow).append(": ").append(count).append("\n"));

      sb.append("\nAverage Response Times:\n");
      responseTimes.forEach((flow, times) -> {
        if (!times.isEmpty()) {
          double avg = times.stream().mapToLong(Long::longValue).average().orElse(0);
          sb.append("  ").append(flow).append(": ").append(String.format("%.2f", avg)).append("ms\n");
        }
      });

      return sb.toString();
    });

    // Initialize Genkit
    genkit.init();

    logger.info("\n========================================");
    logger.info("Genkit Middleware Sample Started!");
    logger.info("========================================\n");

    logger.info("Available flows:");
    logger.info("  - greeting: Simple flow with logging middleware");
    logger.info("  - chat: AI chat with multiple middleware (logging, metrics, validation, retry)");
    logger.info("  - fact: AI facts with caching middleware");
    logger.info("  - joke: AI jokes with rate limiting middleware");
    logger.info("  - echo: Echo with conditional logging");
    logger.info("  - analyze: Analysis with before/after hooks and timing");
    logger.info("  - safe: Demonstrates error handling middleware");
    logger.info("  - metrics: View collected metrics\n");

    logger.info("Server running on http://localhost:8080");
    logger.info("Reflection server running on http://localhost:3100");
    logger.info("\nExample requests:");
    logger.info("  curl -X POST http://localhost:8080/greeting -H 'Content-Type: application/json' -d '\"World\"'");
    logger.info(
        "  curl -X POST http://localhost:8080/chat -H 'Content-Type: application/json' -d '\"What is the capital of France?\"'");
    logger.info("  curl -X POST http://localhost:8080/fact -H 'Content-Type: application/json' -d '\"penguins\"'");
    logger.info(
        "  curl -X POST http://localhost:8080/joke -H 'Content-Type: application/json' -d '\"programming\"'");
    logger.info("  curl -X POST http://localhost:8080/safe -H 'Content-Type: application/json' -d '\"error\"'");
    logger.info("  curl -X POST http://localhost:8080/metrics -H 'Content-Type: application/json' -d 'null'");
  }
}
