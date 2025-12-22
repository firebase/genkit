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

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.Map;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.Document;
import com.google.genkit.ai.EmbedResponse;
import com.google.genkit.ai.GenerateOptions;
import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.Part;
import com.google.genkit.ai.Tool;
import com.google.genkit.core.ActionContext;
import com.google.genkit.plugins.googlegenai.GoogleGenAIPlugin;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;

/**
 * Sample application demonstrating Google GenAI (Gemini) integration with
 * Genkit.
 *
 * <p>
 * This sample uses the Jetty plugin to expose flows via HTTP endpoints,
 * allowing you to use the Genkit Developer UI.
 *
 * <p>
 * To run this sample:
 * <ol>
 * <li>Set the GOOGLE_API_KEY environment variable with your Gemini API key</li>
 * <li>Run: genkit start -- ./run.sh</li>
 * <li>Open the Genkit Developer UI at http://localhost:4000</li>
 * </ol>
 */
public class GoogleGenAIApp {

  // Output directory for generated media files
  private static final String OUTPUT_DIR = "generated_media";

  public static void main(String[] args) throws Exception {
    System.out.println("=== Google GenAI (Gemini) Sample with Dev UI ===\n");

    // Create output directory for media files
    createOutputDirectory();

    // Create the Jetty server plugin for HTTP endpoints
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // Initialize Genkit with Google GenAI plugin and Jetty
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(GoogleGenAIPlugin.create()).plugin(jetty).build();

    // Define flows for the Dev UI
    defineTextGenerationFlow(genkit);
    defineToolCallingFlow(genkit);
    defineEmbeddingsFlow(genkit);
    defineImageGenerationFlow(genkit);
    defineTextToSpeechFlow(genkit);
    defineVideoGenerationFlow(genkit);

    System.out.println("Server started on http://localhost:8080");
    System.out.println("Use Genkit Developer UI at http://localhost:4000 to interact with flows");
    System.out.println("\nAvailable flows:");
    System.out.println("  - textGeneration: Generate text with Gemini");
    System.out.println("  - toolCalling: Demonstrate tool/function calling");
    System.out.println("  - embeddings: Generate text embeddings");
    System.out.println("  - imageGeneration: Generate images with Imagen (saves to " + OUTPUT_DIR + "/)");
    System.out.println("  - textToSpeech: Generate audio with TTS (saves to " + OUTPUT_DIR + "/)");
    System.out.println("  - videoGeneration: Generate videos with Veo (saves to " + OUTPUT_DIR + "/)");
    System.out.println("\nGenerated media files will be saved to: " + new File(OUTPUT_DIR).getAbsolutePath());
    System.out.println("\nPress Ctrl+C to stop the server.");

    // Keep the application running
    Thread.currentThread().join();
  }

  private static void createOutputDirectory() {
    File dir = new File(OUTPUT_DIR);
    if (!dir.exists()) {
      dir.mkdirs();
      System.out.println("Created output directory: " + dir.getAbsolutePath());
    }
  }

  /**
   * Saves base64-encoded data to a file.
   */
  private static String saveBase64ToFile(String base64Data, String filename) throws IOException {
    byte[] data = Base64.getDecoder().decode(base64Data);
    Path filePath = Paths.get(OUTPUT_DIR, filename);
    try (FileOutputStream fos = new FileOutputStream(filePath.toFile())) {
      fos.write(data);
    }
    return filePath.toAbsolutePath().toString();
  }

  /**
   * Extracts base64 data from a data URL.
   */
  private static String extractBase64FromDataUrl(String dataUrl) {
    if (dataUrl.startsWith("data:")) {
      int commaIndex = dataUrl.indexOf(",");
      if (commaIndex > 0) {
        return dataUrl.substring(commaIndex + 1);
      }
    }
    return dataUrl;
  }

  private static void defineTextGenerationFlow(Genkit genkit) {
    genkit.defineFlow("textGeneration", String.class, String.class, (ctx, prompt) -> {
      GenerationConfig config = GenerationConfig.builder().temperature(0.7).maxOutputTokens(500).build();

      ModelResponse response = genkit.generate(
          GenerateOptions.builder().model("googleai/gemini-2.0-flash").prompt(prompt).config(config).build());

      return response.getText();
    });
  }

  @SuppressWarnings("unchecked")
  private static void defineToolCallingFlow(Genkit genkit) {
    // Define a simple weather tool
    Tool<Map<String, Object>, Map<String, Object>> weatherTool = genkit.defineTool("getWeather",
        "Get the current weather for a location",
        Map.of("type", "object", "properties", Map.of("location",
            Map.of("type", "string", "description", "The city and state, e.g., San Francisco, CA"), "unit",
            Map.of("type", "string", "enum", Arrays.asList("celsius", "fahrenheit"), "description",
                "The temperature unit")),
            "required", Arrays.asList("location")),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ActionContext ctx, Map<String, Object> input) -> {
          String location = (String) input.get("location");
          String unit = input.get("unit") != null ? (String) input.get("unit") : "celsius";
          // Mock weather response
          Map<String, Object> result = Map.of("location", location, "temperature", 22, "unit", unit,
              "condition", "Sunny");
          return result;
        });

    genkit.defineFlow("toolCalling", String.class, String.class, (ctx, prompt) -> {
      ModelResponse response = genkit.generate(GenerateOptions.builder().model("googleai/gemini-2.0-flash")
          .prompt(prompt).tools(List.of(weatherTool)).build());

      return response.getText();
    });
  }

  private static void defineEmbeddingsFlow(Genkit genkit) {
    genkit.defineFlow("embeddings", String.class, String.class, (ctx, text) -> {
      List<Document> documents = Arrays.asList(Document.fromText(text));
      EmbedResponse response = genkit.embed("googleai/text-embedding-004", documents);

      if (response.getEmbeddings() != null && !response.getEmbeddings().isEmpty()) {
        EmbedResponse.Embedding embedding = response.getEmbeddings().get(0);
        return "Generated embedding with " + embedding.getValues().length + " dimensions";
      }
      return "Failed to generate embedding";
    });
  }

  private static void defineImageGenerationFlow(Genkit genkit) {
    genkit.defineFlow("imageGeneration", String.class, String.class, (ctx, prompt) -> {
      Map<String, Object> imagenOptions = Map.of("numberOfImages", 1, "aspectRatio", "1:1");

      GenerationConfig config = GenerationConfig.builder().custom(imagenOptions).build();

      ModelResponse response = genkit.generate(GenerateOptions.builder()
          .model("googleai/imagen-4.0-fast-generate-001").prompt(prompt).config(config).build());

      // Save the generated image
      if (response.getMessage() != null && response.getMessage().getContent() != null) {
        StringBuilder result = new StringBuilder();
        int imageCount = 0;

        for (Part part : response.getMessage().getContent()) {
          if (part.getMedia() != null) {
            imageCount++;
            String url = part.getMedia().getUrl();
            String contentType = part.getMedia().getContentType();

            if (url.startsWith("data:")) {
              // Extract and save base64 data
              String base64Data = extractBase64FromDataUrl(url);
              String extension = contentType != null && contentType.contains("png") ? "png" : "jpg";
              String filename = "image_" + System.currentTimeMillis() + "_" + imageCount + "."
                  + extension;

              try {
                String savedPath = saveBase64ToFile(base64Data, filename);
                result.append("Image ").append(imageCount).append(" saved to: ").append(savedPath)
                    .append("\n");
              } catch (IOException e) {
                result.append("Image ").append(imageCount).append(" failed to save: ")
                    .append(e.getMessage()).append("\n");
              }
            } else if (url.startsWith("gs://")) {
              result.append("Image ").append(imageCount).append(" available at GCS: ").append(url)
                  .append("\n");
            }
          }
        }

        return result.length() > 0 ? result.toString().trim() : "No images generated";
      }

      return "No images generated";
    });
  }

  private static void defineTextToSpeechFlow(Genkit genkit) {
    genkit.defineFlow("textToSpeech", String.class, String.class, (ctx, text) -> {
      Map<String, Object> ttsOptions = Map.of("voiceName", "Zephyr" // Available: Zephyr, Puck, Charon, Kore,
      // Fenrir, etc.
      );

      GenerationConfig config = GenerationConfig.builder().custom(ttsOptions).build();

      ModelResponse response = genkit.generate(GenerateOptions.builder()
          .model("googleai/gemini-2.5-flash-preview-tts").prompt(text).config(config).build());

      // Save the generated audio
      if (response.getMessage() != null && response.getMessage().getContent() != null) {
        StringBuilder result = new StringBuilder();
        int audioCount = 0;

        for (Part part : response.getMessage().getContent()) {
          if (part.getMedia() != null) {
            audioCount++;
            String url = part.getMedia().getUrl();
            String contentType = part.getMedia().getContentType();

            if (url.startsWith("data:")) {
              // Extract and save base64 data
              String base64Data = extractBase64FromDataUrl(url);
              // Determine file extension from content type
              String extension = "wav";
              if (contentType != null) {
                if (contentType.contains("mp3") || contentType.contains("mpeg")) {
                  extension = "mp3";
                } else if (contentType.contains("ogg")) {
                  extension = "ogg";
                } else if (contentType.contains("pcm")) {
                  extension = "pcm";
                }
              }
              String filename = "audio_" + System.currentTimeMillis() + "_" + audioCount + "."
                  + extension;

              try {
                String savedPath = saveBase64ToFile(base64Data, filename);
                result.append("Audio ").append(audioCount).append(" saved to: ").append(savedPath)
                    .append("\n");
              } catch (IOException e) {
                result.append("Audio ").append(audioCount).append(" failed to save: ")
                    .append(e.getMessage()).append("\n");
              }
            }
          }
        }

        return result.length() > 0 ? result.toString().trim() : "No audio generated";
      }

      return "No audio generated";
    });
  }

  private static void defineVideoGenerationFlow(Genkit genkit) {
    genkit.defineFlow("videoGeneration", String.class, String.class, (ctx, prompt) -> {
      Map<String, Object> veoOptions = Map.of("numberOfVideos", 1, "durationSeconds", 8, // Valid range: 4-8
          // seconds
          "aspectRatio", "16:9",
          // Note: "generateAudio" and "enhancePrompt" are only available for Vertex AI
          "timeoutMs", 600000 // 10 minutes timeout
      );

      GenerationConfig config = GenerationConfig.builder().custom(veoOptions).build();

      ModelResponse response = genkit.generate(GenerateOptions.builder().model("googleai/veo-3.0-generate-001")
          .prompt(prompt).config(config).build());

      // Save the generated video
      if (response.getMessage() != null && response.getMessage().getContent() != null) {
        StringBuilder result = new StringBuilder();
        int videoCount = 0;

        for (Part part : response.getMessage().getContent()) {
          if (part.getMedia() != null) {
            videoCount++;
            String url = part.getMedia().getUrl();
            String contentType = part.getMedia().getContentType();

            if (url.startsWith("data:")) {
              // Extract and save base64 data
              String base64Data = extractBase64FromDataUrl(url);
              String extension = "mp4";
              if (contentType != null && contentType.contains("webm")) {
                extension = "webm";
              }
              String filename = "video_" + System.currentTimeMillis() + "_" + videoCount + "."
                  + extension;

              try {
                String savedPath = saveBase64ToFile(base64Data, filename);
                result.append("Video ").append(videoCount).append(" saved to: ").append(savedPath)
                    .append("\n");
              } catch (IOException e) {
                result.append("Video ").append(videoCount).append(" failed to save: ")
                    .append(e.getMessage()).append("\n");
              }
            } else if (url.startsWith("gs://")) {
              result.append("Video ").append(videoCount).append(" available at GCS: ").append(url)
                  .append("\n");
            }
          }
        }

        return result.length() > 0 ? result.toString().trim() : "No videos generated";
      }

      return "No videos generated";
    });
  }
}
