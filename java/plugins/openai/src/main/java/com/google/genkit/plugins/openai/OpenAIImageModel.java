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

package com.google.genkit.plugins.openai;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.genkit.ai.*;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * OpenAI image generation model implementation for Genkit. Supports DALL-E 2,
 * DALL-E 3, and gpt-image-1 models.
 */
public class OpenAIImageModel implements Model {

  private static final Logger logger = LoggerFactory.getLogger(OpenAIImageModel.class);
  private static final MediaType JSON_MEDIA_TYPE = MediaType.parse("application/json");

  private final String modelName;
  private final OpenAIPluginOptions options;
  private final OkHttpClient client;
  private final ObjectMapper objectMapper;
  private final ModelInfo info;

  /**
   * Creates a new OpenAIImageModel.
   *
   * @param modelName
   *            the model name (dall-e-2, dall-e-3, or gpt-image-1)
   * @param options
   *            the plugin options
   */
  public OpenAIImageModel(String modelName, OpenAIPluginOptions options) {
    this.modelName = modelName;
    this.options = options;
    this.objectMapper = new ObjectMapper();
    this.client = new OkHttpClient.Builder().connectTimeout(options.getTimeout() * 2, TimeUnit.SECONDS)
        .readTimeout(options.getTimeout() * 2, TimeUnit.SECONDS)
        .writeTimeout(options.getTimeout() * 2, TimeUnit.SECONDS).build();
    this.info = createModelInfo();
  }

  private ModelInfo createModelInfo() {
    ModelInfo info = new ModelInfo();
    info.setLabel("OpenAI " + modelName);

    ModelInfo.ModelCapabilities caps = new ModelInfo.ModelCapabilities();
    caps.setMultiturn(false);
    caps.setMedia(false); // Image generation models don't accept image inputs
    caps.setTools(false);
    caps.setSystemRole(false);
    caps.setOutput(Set.of("media")); // Outputs media (images)
    info.setSupports(caps);

    return info;
  }

  @Override
  public String getName() {
    return "openai/" + modelName;
  }

  @Override
  public ModelInfo getInfo() {
    return info;
  }

  @Override
  public boolean supportsStreaming() {
    return false; // Image generation doesn't support streaming
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request) {
    try {
      return callOpenAIImages(request);
    } catch (IOException e) {
      throw new GenkitException("OpenAI Images API call failed", e);
    }
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    // Image generation doesn't support streaming, just call the non-streaming
    // version
    return run(context, request);
  }

  private ModelResponse callOpenAIImages(ModelRequest request) throws IOException {
    ObjectNode requestBody = buildRequestBody(request);

    Request httpRequest = new Request.Builder().url(options.getBaseUrl() + "/images/generations")
        .header("Authorization", "Bearer " + options.getApiKey()).header("Content-Type", "application/json")
        .post(RequestBody.create(requestBody.toString(), JSON_MEDIA_TYPE)).build();

    if (options.getOrganization() != null) {
      httpRequest = httpRequest.newBuilder().header("OpenAI-Organization", options.getOrganization()).build();
    }

    logger.debug("Calling OpenAI Images API with model: {}", modelName);

    try (Response response = client.newCall(httpRequest).execute()) {
      if (!response.isSuccessful()) {
        String errorBody = response.body() != null ? response.body().string() : "No error body";
        throw new GenkitException("OpenAI Images API error: " + response.code() + " - " + errorBody);
      }

      String responseBody = response.body().string();
      return parseResponse(responseBody);
    }
  }

  private ObjectNode buildRequestBody(ModelRequest request) {
    ObjectNode body = objectMapper.createObjectNode();
    body.put("model", modelName);

    // Extract prompt from messages
    String prompt = extractPrompt(request);
    body.put("prompt", prompt);

    // Get config - check both Map config and custom config
    Map<String, Object> config = request.getConfig();

    // Default response format to b64_json for data URI support
    String responseFormat = "b64_json";

    if (config != null) {
      // Size
      if (config.containsKey("size")) {
        body.put("size", (String) config.get("size"));
      }

      // Quality (DALL-E 3 or gpt-image-1)
      if (config.containsKey("quality")) {
        body.put("quality", (String) config.get("quality"));
      }

      // Style (DALL-E 3)
      if (config.containsKey("style")) {
        body.put("style", (String) config.get("style"));
      }

      // Number of images
      if (config.containsKey("n")) {
        body.put("n", ((Number) config.get("n")).intValue());
      }

      // Response format
      if (config.containsKey("responseFormat")) {
        responseFormat = (String) config.get("responseFormat");
      }

      // User
      if (config.containsKey("user")) {
        body.put("user", (String) config.get("user"));
      }

      // gpt-image-1 specific options
      if (modelName.contains("gpt-image")) {
        if (config.containsKey("background")) {
          body.put("background", (String) config.get("background"));
        }
        if (config.containsKey("outputFormat")) {
          body.put("output_format", (String) config.get("outputFormat"));
        }
        if (config.containsKey("outputCompression")) {
          body.put("output_compression", ((Number) config.get("outputCompression")).intValue());
        }
        if (config.containsKey("moderation")) {
          body.put("moderation", (String) config.get("moderation"));
        }
      }
    }

    body.put("response_format", responseFormat);

    return body;
  }

  private String extractPrompt(ModelRequest request) {
    // Get the prompt from the messages
    List<Message> messages = request.getMessages();
    if (messages == null || messages.isEmpty()) {
      throw new GenkitException("No messages provided for image generation");
    }

    // Find user message with text content
    for (Message message : messages) {
      if (message.getRole() == Role.USER || message.getRole() == null) {
        List<Part> content = message.getContent();
        if (content != null) {
          for (Part part : content) {
            if (part.getText() != null) {
              return part.getText();
            }
          }
        }
      }
    }

    throw new GenkitException("No text prompt found in messages for image generation");
  }

  private ModelResponse parseResponse(String responseBody) throws IOException {
    JsonNode root = objectMapper.readTree(responseBody);

    ModelResponse response = new ModelResponse();
    List<Candidate> candidates = new ArrayList<>();
    Candidate candidate = new Candidate();

    Message message = new Message();
    message.setRole(Role.MODEL);
    List<Part> parts = new ArrayList<>();

    // Parse image data
    JsonNode dataNode = root.get("data");
    if (dataNode != null && dataNode.isArray()) {
      for (JsonNode imageNode : dataNode) {
        Part part = new Part();

        // Determine content type based on model
        String contentType = "image/png";
        if (modelName.contains("gpt-image")) {
          // gpt-image-1 might return different formats
          contentType = "image/png"; // Default, could be detected from config
        }

        // Get URL or base64 data
        String url = null;
        if (imageNode.has("url") && !imageNode.get("url").isNull()) {
          url = imageNode.get("url").asText();
        } else if (imageNode.has("b64_json") && !imageNode.get("b64_json").isNull()) {
          String b64Data = imageNode.get("b64_json").asText();
          url = "data:" + contentType + ";base64," + b64Data;
        }

        if (url != null) {
          part.setMedia(new Media(contentType, url));
          parts.add(part);
        }
      }
    }

    // Track image count in usage
    Usage usage = new Usage();
    usage.setOutputImages(parts.size());
    response.setUsage(usage);

    message.setContent(parts);
    candidate.setMessage(message);
    candidate.setFinishReason(FinishReason.STOP);

    candidates.add(candidate);
    response.setCandidates(candidates);

    logger.debug("Generated {} images", parts.size());

    return response;
  }
}
