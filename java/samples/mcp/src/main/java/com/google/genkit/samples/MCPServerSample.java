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

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.plugins.mcp.MCPServer;
import com.google.genkit.plugins.mcp.MCPServerOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating an MCP Server built with Genkit.
 *
 * <p>
 * This example shows how to:
 * <ul>
 * <li>Create a Genkit application with custom tools</li>
 * <li>Expose those tools as an MCP server</li>
 * <li>Use STDIO transport for integration with Claude Desktop and other MCP
 * clients</li>
 * </ul>
 *
 * <p>
 * This server exposes several demonstration tools:
 * <ul>
 * <li>calculator: Performs basic math operations</li>
 * <li>weather: Gets mock weather information</li>
 * <li>datetime: Gets current date and time</li>
 * <li>greet: Creates personalized greetings</li>
 * <li>translate_mock: Mock translation tool</li>
 * </ul>
 *
 * <p>
 * To use with Claude Desktop, add to your claude_desktop_config.json:
 *
 * <pre>{@code
 * {
 *   "mcpServers": {
 *     "genkit-tools": {
 *       "command": "java",
 *       "args": ["-jar", "/path/to/genkit-mcp-server-sample.jar"]
 *     }
 *   }
 * }
 * }</pre>
 *
 * <p>
 * Or run directly for testing:
 *
 * <pre>
 * mvn exec:java -Dexec.mainClass="com.google.genkit.samples.MCPServerSample"
 * </pre>
 */
public class MCPServerSample {

  private static final Logger logger = LoggerFactory.getLogger(MCPServerSample.class);

  public static void main(String[] args) throws Exception {
    // Note: For MCP server mode, we minimize console output since
    // STDIO is used for communication with the MCP client.
    // Logging goes to stderr which is separate from the protocol.

    logger.info("Initializing Genkit MCP Server...");

    // =======================================================
    // Create Genkit instance
    // =======================================================

    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(false) // Disable dev mode for server
        .build()).plugin(OpenAIPlugin.create()) // Optional: Include if tools need AI
        .build();

    // =======================================================
    // Define tools to expose via MCP
    // =======================================================

    // Tool 1: Calculator
    genkit.defineTool("calculator", "Performs basic math operations (add, subtract, multiply, divide)",
        Map.of("type", "object", "properties",
            Map.of("operation",
                Map.of("type", "string", "description", "The operation to perform", "enum",
                    new String[]{"add", "subtract", "multiply", "divide"}),
                "a", Map.of("type", "number", "description", "First operand"), "b",
                Map.of("type", "number", "description", "Second operand")),
            "required", new String[]{"operation", "a", "b"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String operation = (String) input.get("operation");
          double a = ((Number) input.get("a")).doubleValue();
          double b = ((Number) input.get("b")).doubleValue();

          double result;
          switch (operation) {
            case "add" :
              result = a + b;
              break;
            case "subtract" :
              result = a - b;
              break;
            case "multiply" :
              result = a * b;
              break;
            case "divide" :
              if (b == 0) {
                throw new IllegalArgumentException("Cannot divide by zero");
              }
              result = a / b;
              break;
            default :
              throw new IllegalArgumentException("Unknown operation: " + operation);
          }

          Map<String, Object> response = new HashMap<>();
          response.put("operation", operation);
          response.put("a", a);
          response.put("b", b);
          response.put("result", result);
          return response;
        });

    // Tool 2: Weather (mock)
    genkit.defineTool("get_weather", "Gets the current weather for a location (mock data)",
        Map.of("type", "object", "properties",
            Map.of("location", Map.of("type", "string", "description", "The city name"), "unit",
                Map.of("type", "string", "description", "Temperature unit (celsius or fahrenheit)",
                    "enum", new String[]{"celsius", "fahrenheit"})),
            "required", new String[]{"location"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String location = (String) input.get("location");
          String unit = input.get("unit") != null ? (String) input.get("unit") : "celsius";

          // Mock weather data
          int tempC = (int) (Math.random() * 30) + 5;
          int tempF = (int) (tempC * 9.0 / 5.0 + 32);

          String[] conditions = {"Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Windy"};
          String condition = conditions[(int) (Math.random() * conditions.length)];

          Map<String, Object> weather = new HashMap<>();
          weather.put("location", location);
          weather.put("temperature", unit.equals("celsius") ? tempC : tempF);
          weather.put("unit", unit);
          weather.put("condition", condition);
          weather.put("humidity", (int) (Math.random() * 60) + 30 + "%");
          weather.put("note", "This is mock weather data for demonstration purposes");
          return weather;
        });

    // Tool 3: Date/Time
    genkit.defineTool("get_datetime", "Gets the current date and time in various formats",
        Map.of("type", "object", "properties", Map.of("timezone",
            Map.of("type", "string", "description", "Timezone (e.g., UTC, America/New_York)"), "format",
            Map.of("type", "string", "description", "Output format (iso, readable, date_only, time_only)")),
            "required", new String[]{}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String format = input.get("format") != null ? (String) input.get("format") : "readable";

          LocalDateTime now = LocalDateTime.now();
          String formatted;

          switch (format) {
            case "iso" :
              formatted = now.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
              break;
            case "date_only" :
              formatted = now.format(DateTimeFormatter.ISO_LOCAL_DATE);
              break;
            case "time_only" :
              formatted = now.format(DateTimeFormatter.ofPattern("HH:mm:ss"));
              break;
            case "readable" :
            default :
              formatted = now.format(DateTimeFormatter.ofPattern("EEEE, MMMM d, yyyy 'at' h:mm a"));
              break;
          }

          Map<String, Object> result = new HashMap<>();
          result.put("datetime", formatted);
          result.put("format", format);
          result.put("timestamp", System.currentTimeMillis());
          return result;
        });

    // Tool 4: Greeting generator
    genkit.defineTool("greet", "Creates a personalized greeting message", Map.of("type", "object", "properties",
        Map.of("name", Map.of("type", "string", "description", "The name of the person to greet"), "style",
            Map.of("type", "string", "description", "Greeting style", "enum",
                new String[]{"formal", "casual", "enthusiastic"})),
        "required", new String[]{"name"}), (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String name = (String) input.get("name");
          String style = input.get("style") != null ? (String) input.get("style") : "casual";

          String greeting;
          switch (style) {
            case "formal" :
              greeting = "Dear " + name + ", it is a pleasure to make your acquaintance.";
              break;
            case "enthusiastic" :
              greeting = "Hey " + name + "! 🎉 So awesome to meet you! Let's do something amazing!";
              break;
            case "casual" :
            default :
              greeting = "Hi " + name + "! Nice to meet you.";
              break;
          }

          Map<String, Object> result = new HashMap<>();
          result.put("greeting", greeting);
          result.put("name", name);
          result.put("style", style);
          return result;
        });

    // Tool 5: Mock translator
    genkit.defineTool("translate_mock", "Mock translation tool - demonstrates how a translation tool might work",
        Map.of("type", "object", "properties",
            Map.of("text", Map.of("type", "string", "description", "The text to translate"),
                "targetLanguage",
                Map.of("type", "string", "description", "Target language code (es, fr, de, ja, etc.)")),
            "required", new String[]{"text", "targetLanguage"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String text = (String) input.get("text");
          String targetLang = (String) input.get("targetLanguage");

          // Mock translations - just add a prefix and note
          Map<String, String> langNames = Map.of("es", "Spanish", "fr", "French", "de", "German", "ja",
              "Japanese", "zh", "Chinese", "ko", "Korean", "pt", "Portuguese", "it", "Italian");

          String langName = langNames.getOrDefault(targetLang, targetLang);
          String mockTranslation = "[" + langName + "] " + text + " (mock translation)";

          Map<String, Object> result = new HashMap<>();
          result.put("originalText", text);
          result.put("translatedText", mockTranslation);
          result.put("targetLanguage", targetLang);
          result.put("targetLanguageName", langName);
          result.put("note", "This is a mock translation. In a real implementation, use a translation API.");
          return result;
        });

    // =======================================================
    // Create and start MCP Server
    // =======================================================
    // Note: genkit.init() is already called by the builder, so we don't need to
    // call it again

    MCPServerOptions serverOptions = MCPServerOptions.builder().name("genkit-tools-server").version("1.0.0")
        .build();

    MCPServer mcpServer = new MCPServer(genkit.getRegistry(), serverOptions);

    logger.info("Starting MCP server with STDIO transport...");
    logger.info("Available tools: calculator, get_weather, get_datetime, greet, translate_mock");

    // Add shutdown hook for cleanup
    Runtime.getRuntime().addShutdownHook(new Thread(() -> {
      logger.info("Shutting down MCP server...");
      mcpServer.stop();
    }));

    // Start the server (blocks until client disconnects)
    mcpServer.start();
  }
}
