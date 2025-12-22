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

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.*;
import com.google.genkit.core.Flow;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating Genkit with OpenAI.
 *
 * This example shows how to: - Configure Genkit with the OpenAI plugin - Define
 * flows - Use tools - Generate text with OpenAI models - Expose flows via HTTP
 * endpoints - Process images with vision models - Generate images with DALL-E
 *
 * To run: 1. Set the OPENAI_API_KEY environment variable 2. Run: mvn exec:java
 */
public class OpenAISample {

  public static void main(String[] args) throws Exception {
    // Create the Jetty server plugin
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // Create Genkit with plugins
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).plugin(jetty).build();

    // Define a simple greeting flow
    Flow<String, String, Void> greetingFlow = genkit.defineFlow("greeting", String.class, String.class,
        (name) -> "Hello, " + name + "!");

    // Define a joke generator flow using OpenAI
    Flow<String, String, Void> jokeFlow = genkit.defineFlow("tellJoke", String.class, String.class,
        (ctx, topic) -> {
          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .prompt("Tell me a short, funny joke about: " + topic)
              .config(GenerationConfig.builder().temperature(0.9).maxOutputTokens(200).build()).build());

          return response.getText();
        });

    // Define a tool for getting current weather (mock implementation)
    @SuppressWarnings("unchecked")
    Tool<Map<String, Object>, Map<String, Object>> weatherTool = genkit.defineTool("getWeather",
        "Gets the current weather for a location",
        Map.of("type", "object", "properties",
            Map.of("location", Map.of("type", "string", "description", "The city name")), "required",
            new String[]{"location"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String location = (String) input.get("location");
          Map<String, Object> weather = new HashMap<>();
          weather.put("location", location);
          weather.put("temperature", "72°F");
          weather.put("conditions", "Sunny");
          return weather;
        });

    // Define a chat flow
    Flow<String, String, Void> chatFlow = genkit.defineFlow("chat", String.class, String.class,
        (ctx, userMessage) -> {
          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o")
              .system("You are a helpful assistant.").prompt(userMessage).build());

          return response.getText();
        });

    // Define a flow that uses the weather tool
    Flow<String, String, Void> weatherAssistantFlow = genkit.defineFlow("weatherAssistant", String.class,
        String.class, (ctx, userMessage) -> {
          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o").system(
              "You are a helpful weather assistant. Use the getWeather tool to provide weather information when asked about the weather in a specific location.")
              .prompt(userMessage).tools(List.of(weatherTool)).build());

          return response.getText();
        });

    // Define a streaming chat flow
    Flow<String, String, Void> streamingChatFlow = genkit.defineFlow("streamingChat", String.class, String.class,
        (ctx, userMessage) -> {
          StringBuilder result = new StringBuilder();

          ModelResponse response = genkit.generateStream(GenerateOptions.builder().model("openai/gpt-4o")
              .system("You are a helpful assistant that provides detailed, comprehensive responses.")
              .prompt(userMessage).config(GenerationConfig.builder().maxOutputTokens(1000).build())
              .build(), (chunk) -> {
                // Process each chunk as it arrives
                String text = chunk.getText();
                if (text != null) {
                  result.append(text);
                  System.out.print(text); // Print chunks in real-time
                }
              });

          System.out.println(); // New line after streaming completes
          return response.getText();
        });

    // Define a streaming flow that uses tools - combines both features!
    Flow<String, String, Void> streamingWeatherFlow = genkit.defineFlow("streamingWeather", String.class,
        String.class, (ctx, userMessage) -> {
          StringBuilder result = new StringBuilder();

          System.out.println("\n--- Streaming Weather Assistant ---");
          System.out.println("Query: " + userMessage);
          System.out.println("Response: ");

          ModelResponse response = genkit.generateStream(
              GenerateOptions.builder().model("openai/gpt-4o")
                  .system("You are a helpful weather assistant. When asked about weather, "
                      + "use the getWeather tool to get current conditions, then provide "
                      + "a friendly, detailed response about the weather.")
                  .prompt(userMessage).tools(List.of(weatherTool))
                  .config(GenerationConfig.builder().maxOutputTokens(500).build()).build(),
              (chunk) -> {
                // Stream chunks as they arrive
                String text = chunk.getText();
                if (text != null) {
                  result.append(text);
                  System.out.print(text);
                }
              });

          System.out.println("\n--- End of Response ---\n");
          return response.getText();
        });

    // ====================
    // IMAGE EXAMPLES
    // ====================

    // Define a flow that analyzes an image using GPT-4 Vision
    // This flow accepts an image URL and returns a description
    Flow<String, String, Void> describeImageFlow = genkit.defineFlow("describeImage", String.class, String.class,
        (ctx, imageUrl) -> {
          System.out.println("\n--- Image Description Flow ---");
          System.out.println("Analyzing image: " + imageUrl);

          // Create a message with both text and image
          Message userMessage = new Message();
          userMessage.setRole(Role.USER);
          userMessage.setContent(List.of(Part.text(
              "Describe this image in detail. What do you see? Include colors, objects, people, and any text visible."),
              Part.media("image/jpeg", imageUrl) // Can also be image/png, image/gif, image/webp
          ));

          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o") // GPT-4o
              // supports
              // vision
              .messages(List.of(userMessage))
              .config(GenerationConfig.builder().maxOutputTokens(500).temperature(0.7).build()).build());

          System.out.println("Description: " + response.getText());
          System.out.println("--- End of Image Description ---\n");

          return response.getText();
        });

    // Define a flow that generates an image using DALL-E 3
    // This flow accepts a prompt and returns the generated image URL (base64 data
    // URI)
    Flow<String, String, Void> generateImageFlow = genkit.defineFlow("generateImage", String.class, String.class,
        (ctx, prompt) -> {
          System.out.println("\n--- Image Generation Flow ---");
          System.out.println("Generating image for prompt: " + prompt);

          // Create image-specific config options using the custom field
          Map<String, Object> imageOptions = new HashMap<>();
          imageOptions.put("size", "1024x1024"); // Image size
          imageOptions.put("quality", "standard"); // "standard" or "hd"
          imageOptions.put("style", "vivid"); // "vivid" or "natural"
          imageOptions.put("n", 1); // Number of images

          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/dall-e-3") // DALL-E
              // 3 for
              // image
              // generation
              .prompt(prompt).config(GenerationConfig.builder().custom(imageOptions).build()).build());

          // Get the generated image media
          Message message = response.getCandidates().get(0).getMessage();
          List<Part> parts = message.getContent();

          // The response contains media parts with the generated images
          for (Part part : parts) {
            if (part.getMedia() != null) {
              String imageUrl = part.getMedia().getUrl();
              String contentType = part.getMedia().getContentType();
              System.out.println("Generated image (" + contentType + ")");

              // The URL will be a data URI like: data:image/png;base64,<base64data>
              // You can save this or display it in your application
              if (imageUrl.startsWith("data:")) {
                System.out.println(
                    "Image returned as base64 data URI (length: " + imageUrl.length() + " chars)");
              } else {
                System.out.println("Image URL: " + imageUrl);
              }

              return imageUrl;
            }
          }

          System.out.println("--- End of Image Generation ---\n");
          return "No image generated";
        });

    System.out.println("Genkit Sample Application Started!");
    System.out.println("=====================================");
    System.out.println("Dev UI: http://localhost:3100");
    System.out.println("API Endpoints:");
    System.out.println("  POST http://localhost:8080/api/flows/greeting");
    System.out.println("  POST http://localhost:8080/api/flows/tellJoke");
    System.out.println("  POST http://localhost:8080/api/flows/chat");
    System.out.println("  POST http://localhost:8080/api/flows/weatherAssistant (uses tools)");
    System.out.println("  POST http://localhost:8080/api/flows/streamingChat (uses streaming)");
    System.out.println("  POST http://localhost:8080/api/flows/streamingWeather (uses streaming + tools)");
    System.out.println("  POST http://localhost:8080/api/flows/describeImage (vision - analyze images)");
    System.out.println("  POST http://localhost:8080/api/flows/generateImage (DALL-E - generate images)");
    System.out.println("");
    System.out.println("Example usage:");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/greeting -d '\"World\"' -H 'Content-Type: application/json'");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/tellJoke -d '\"programming\"' -H 'Content-Type: application/json'");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/weatherAssistant -d '\"What is the weather in San Francisco?\"' -H 'Content-Type: application/json'");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/streamingChat -d '\"Explain quantum computing\"' -H 'Content-Type: application/json'");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/streamingWeather -d '\"How is the weather in Tokyo today?\"' -H 'Content-Type: application/json'");
    System.out.println("");
    System.out.println("Image Examples:");
    System.out.println("  # Analyze an image with GPT-4 Vision (use a direct image URL, not a webpage):");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/describeImage -d '\"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg\"' -H 'Content-Type: application/json'");
    System.out.println("");
    System.out.println("  # Generate an image with DALL-E 3:");
    System.out.println(
        "  curl -X POST http://localhost:8080/api/flows/generateImage -d '\"A serene Japanese garden with a koi pond at sunset, digital art\"' -H 'Content-Type: application/json'");
    System.out.println("");
    System.out.println("Press Ctrl+C to stop...");

    // Start the server and block - keeps the application running
    jetty.start();
  }
}
