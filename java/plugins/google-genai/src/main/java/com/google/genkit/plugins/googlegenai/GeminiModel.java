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

package com.google.genkit.plugins.googlegenai;

import java.util.*;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genai.Client;
import com.google.genai.ResponseStream;
import com.google.genai.types.Content;
import com.google.genai.types.FunctionCall;
import com.google.genai.types.FunctionDeclaration;
import com.google.genai.types.FunctionResponse;
import com.google.genai.types.GenerateContentConfig;
import com.google.genai.types.GenerateContentResponse;
import com.google.genai.types.HarmBlockThreshold;
import com.google.genai.types.HarmCategory;
import com.google.genai.types.HttpOptions;
import com.google.genai.types.SafetySetting;
import com.google.genai.types.Schema;
import com.google.genai.types.ThinkingConfig;
import com.google.genai.types.Type;
import com.google.genkit.ai.Media;
import com.google.genkit.ai.Message;
import com.google.genkit.ai.Model;
import com.google.genkit.ai.ModelInfo;
import com.google.genkit.ai.ModelRequest;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.ModelResponseChunk;
import com.google.genkit.ai.Role;
import com.google.genkit.ai.ToolDefinition;
import com.google.genkit.ai.ToolRequest;
import com.google.genkit.ai.ToolResponse;
import com.google.genkit.ai.Usage;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * Gemini model implementation using the official Google GenAI SDK.
 */
public class GeminiModel implements Model {

  private static final Logger logger = LoggerFactory.getLogger(GeminiModel.class);

  private final String modelName;
  private final GoogleGenAIPluginOptions options;
  private final Client client;
  private final ObjectMapper objectMapper;
  private final ModelInfo info;

  /**
   * Creates a new GeminiModel.
   *
   * @param modelName
   *            the model name (e.g., "gemini-2.0-flash", "gemini-2.5-pro")
   * @param options
   *            the plugin options
   */
  public GeminiModel(String modelName, GoogleGenAIPluginOptions options) {
    this.modelName = modelName;
    this.options = options;
    this.objectMapper = new ObjectMapper();
    this.client = createClient();
    this.info = createModelInfo();
  }

  private Client createClient() {
    Client.Builder builder = Client.builder();

    if (options.isVertexAI()) {
      builder.vertexAI(true);
      if (options.getProject() != null) {
        builder.project(options.getProject());
      }
      if (options.getLocation() != null) {
        builder.location(options.getLocation());
      }
      // Vertex AI can also use API key for express mode
      if (options.getApiKey() != null) {
        builder.apiKey(options.getApiKey());
      }
    } else {
      builder.apiKey(options.getApiKey());
    }

    // Apply HTTP options if configured
    HttpOptions httpOptions = options.toHttpOptions();
    if (httpOptions != null) {
      builder.httpOptions(httpOptions);
    }

    return builder.build();
  }

  private ModelInfo createModelInfo() {
    ModelInfo info = new ModelInfo();
    info.setLabel("Google AI " + modelName);

    ModelInfo.ModelCapabilities caps = new ModelInfo.ModelCapabilities();
    caps.setMultiturn(true);
    caps.setMedia(true); // Gemini models support multimodal
    caps.setTools(!isTTSModel()); // TTS models don't support tools
    caps.setSystemRole(!isTTSModel());
    caps.setOutput(Set.of("text", "json"));
    info.setSupports(caps);

    return info;
  }

  private boolean isTTSModel() {
    return modelName.endsWith("-tts");
  }

  private boolean isImageModel() {
    return modelName.contains("-image");
  }

  @Override
  public String getName() {
    return "googleai/" + modelName;
  }

  @Override
  public ModelInfo getInfo() {
    return info;
  }

  @Override
  public boolean supportsStreaming() {
    return true;
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request) {
    try {
      return callGemini(request);
    } catch (Exception e) {
      throw new GenkitException("Gemini API call failed: " + e.getMessage(), e);
    }
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    if (streamCallback == null) {
      return run(context, request);
    }
    try {
      return callGeminiStreaming(request, streamCallback);
    } catch (Exception e) {
      throw new GenkitException("Gemini streaming API call failed: " + e.getMessage(), e);
    }
  }

  private ModelResponse callGemini(ModelRequest request) {
    GenerateContentConfig config = buildConfig(request);
    List<Content> contents = buildContents(request);

    GenerateContentResponse response = client.models.generateContent(modelName, contents, config);

    return parseResponse(response);
  }

  private ModelResponse callGeminiStreaming(ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    GenerateContentConfig config = buildConfig(request);
    List<Content> contents = buildContents(request);

    StringBuilder fullContent = new StringBuilder();
    List<ToolRequest> toolRequests = new ArrayList<>();
    String finishReason = null;

    ResponseStream<GenerateContentResponse> responseStream = client.models.generateContentStream(modelName,
        contents, config);

    try {
      for (GenerateContentResponse chunk : responseStream) {
        String text = chunk.text();
        if (text != null && !text.isEmpty()) {
          fullContent.append(text);
          ModelResponseChunk responseChunk = ModelResponseChunk.text(text);
          streamCallback.accept(responseChunk);
        }

        // Handle tool calls in streaming
        if (chunk.candidates().isPresent()) {
          for (com.google.genai.types.Candidate candidate : chunk.candidates().get()) {
            if (candidate.finishReason().isPresent()) {
              finishReason = candidate.finishReason().get().toString();
            }
            if (candidate.content().isPresent()) {
              Content candidateContent = candidate.content().get();
              if (candidateContent.parts().isPresent()) {
                for (com.google.genai.types.Part part : candidateContent.parts().get()) {
                  if (part.functionCall().isPresent()) {
                    FunctionCall fc = part.functionCall().get();
                    ToolRequest toolRequest = new ToolRequest();
                    toolRequest.setName(fc.name().orElse(""));
                    if (fc.args().isPresent()) {
                      toolRequest.setInput(fc.args().get());
                    }
                    toolRequests.add(toolRequest);
                  }
                }
              }
            }
          }
        }
      }
    } finally {
      responseStream.close();
    }

    // Build final response
    ModelResponse response = new ModelResponse();
    List<com.google.genkit.ai.Candidate> candidates = new ArrayList<>();
    com.google.genkit.ai.Candidate candidate = new com.google.genkit.ai.Candidate();

    Message message = new Message();
    message.setRole(Role.MODEL);
    List<com.google.genkit.ai.Part> parts = new ArrayList<>();

    if (fullContent.length() > 0) {
      com.google.genkit.ai.Part textPart = new com.google.genkit.ai.Part();
      textPart.setText(fullContent.toString());
      parts.add(textPart);
    }

    for (ToolRequest toolRequest : toolRequests) {
      com.google.genkit.ai.Part toolPart = new com.google.genkit.ai.Part();
      toolPart.setToolRequest(toolRequest);
      parts.add(toolPart);
    }

    message.setContent(parts);
    candidate.setMessage(message);
    candidate.setFinishReason(mapFinishReason(finishReason));

    candidates.add(candidate);
    response.setCandidates(candidates);

    return response;
  }

  private GenerateContentConfig buildConfig(ModelRequest request) {
    GenerateContentConfig.Builder configBuilder = GenerateContentConfig.builder();

    // System instruction
    Message systemMessage = findSystemMessage(request);
    if (systemMessage != null) {
      Content systemContent = Content
          .fromParts(com.google.genai.types.Part.fromText(getTextFromMessage(systemMessage)));
      configBuilder.systemInstruction(systemContent);
    }

    // Generation config from request
    Map<String, Object> config = request.getConfig();
    if (config != null) {
      if (config.containsKey("temperature")) {
        configBuilder.temperature(((Number) config.get("temperature")).floatValue());
      }
      if (config.containsKey("maxOutputTokens")) {
        configBuilder.maxOutputTokens(((Number) config.get("maxOutputTokens")).intValue());
      }
      if (config.containsKey("topP")) {
        configBuilder.topP(((Number) config.get("topP")).floatValue());
      }
      if (config.containsKey("topK")) {
        configBuilder.topK(Float.valueOf(((Number) config.get("topK")).floatValue()));
      }
      if (config.containsKey("stopSequences")) {
        @SuppressWarnings("unchecked")
        List<String> stopSequences = (List<String>) config.get("stopSequences");
        configBuilder.stopSequences(stopSequences);
      }
      if (config.containsKey("candidateCount")) {
        configBuilder.candidateCount(((Number) config.get("candidateCount")).intValue());
      }

      // Safety settings
      if (config.containsKey("safetySettings")) {
        @SuppressWarnings("unchecked")
        List<Map<String, String>> safetySettingsConfig = (List<Map<String, String>>) config
            .get("safetySettings");
        List<SafetySetting> safetySettings = new ArrayList<>();
        for (Map<String, String> setting : safetySettingsConfig) {
          safetySettings
              .add(SafetySetting.builder().category(HarmCategory.Known.valueOf(setting.get("category")))
                  .threshold(HarmBlockThreshold.Known.valueOf(setting.get("threshold"))).build());
        }
        configBuilder.safetySettings(safetySettings);
      }

      // Thinking config for Gemini 2.5+
      if (config.containsKey("thinkingConfig")) {
        @SuppressWarnings("unchecked")
        Map<String, Object> thinkingConfig = (Map<String, Object>) config.get("thinkingConfig");
        ThinkingConfig.Builder thinkingBuilder = ThinkingConfig.builder();
        if (thinkingConfig.containsKey("thinkingBudget")) {
          thinkingBuilder.thinkingBudget(((Number) thinkingConfig.get("thinkingBudget")).intValue());
        }
        configBuilder.thinkingConfig(thinkingBuilder);
      }

      // JSON response schema
      if (config.containsKey("responseSchema")) {
        configBuilder.responseMimeType("application/json");
        @SuppressWarnings("unchecked")
        Map<String, Object> schemaMap = (Map<String, Object>) config.get("responseSchema");
        configBuilder.responseSchema(convertToSchema(schemaMap));
      }
    }

    // Tools
    if (request.getTools() != null && !request.getTools().isEmpty()) {
      List<com.google.genai.types.Tool> tools = new ArrayList<>();
      for (ToolDefinition toolDef : request.getTools()) {
        FunctionDeclaration.Builder funcBuilder = FunctionDeclaration.builder().name(toolDef.getName())
            .description(toolDef.getDescription() != null ? toolDef.getDescription() : "");

        if (toolDef.getInputSchema() != null) {
          funcBuilder.parameters(convertToSchema(toolDef.getInputSchema()));
        }

        tools.add(com.google.genai.types.Tool.builder().functionDeclarations(funcBuilder.build()).build());
      }
      configBuilder.tools(tools);
    }

    return configBuilder.build();
  }

  private Schema convertToSchema(Map<String, Object> inputSchema) {
    Schema.Builder schemaBuilder = Schema.builder();

    if (inputSchema.containsKey("type")) {
      String type = (String) inputSchema.get("type");
      schemaBuilder.type(Type.Known.valueOf(type.toUpperCase()));
    }

    if (inputSchema.containsKey("description")) {
      schemaBuilder.description((String) inputSchema.get("description"));
    }

    if (inputSchema.containsKey("properties")) {
      @SuppressWarnings("unchecked")
      Map<String, Object> properties = (Map<String, Object>) inputSchema.get("properties");
      Map<String, Schema> schemaProperties = new HashMap<>();
      for (Map.Entry<String, Object> entry : properties.entrySet()) {
        @SuppressWarnings("unchecked")
        Map<String, Object> propSchema = (Map<String, Object>) entry.getValue();
        schemaProperties.put(entry.getKey(), convertToSchema(propSchema));
      }
      schemaBuilder.properties(schemaProperties);
    }

    if (inputSchema.containsKey("required")) {
      @SuppressWarnings("unchecked")
      List<String> required = (List<String>) inputSchema.get("required");
      schemaBuilder.required(required);
    }

    if (inputSchema.containsKey("items")) {
      @SuppressWarnings("unchecked")
      Map<String, Object> items = (Map<String, Object>) inputSchema.get("items");
      schemaBuilder.items(convertToSchema(items));
    }

    if (inputSchema.containsKey("enum")) {
      @SuppressWarnings("unchecked")
      List<String> enumValues = (List<String>) inputSchema.get("enum");
      schemaBuilder.enum_(enumValues);
    }

    return schemaBuilder.build();
  }

  private List<Content> buildContents(ModelRequest request) {
    List<Content> contents = new ArrayList<>();

    for (Message message : request.getMessages()) {
      // Skip system messages (handled separately in config)
      if (message.getRole() == Role.SYSTEM) {
        continue;
      }

      List<com.google.genai.types.Part> parts = new ArrayList<>();

      for (com.google.genkit.ai.Part part : message.getContent()) {
        if (part.getText() != null) {
          parts.add(com.google.genai.types.Part.fromText(part.getText()));
        } else if (part.getMedia() != null) {
          Media media = part.getMedia();
          String url = media.getUrl();
          String contentType = media.getContentType();

          if (url.startsWith("data:")) {
            // Inline data URL
            String base64Data = url.substring(url.indexOf(",") + 1);
            if (contentType == null) {
              contentType = url.substring(url.indexOf(":") + 1, url.indexOf(";"));
            }
            parts.add(com.google.genai.types.Part.fromBytes(Base64.getDecoder().decode(base64Data),
                contentType));
          } else if (url.startsWith("gs://") || url.startsWith("http://") || url.startsWith("https://")) {
            // File URI
            parts.add(com.google.genai.types.Part.fromUri(url,
                contentType != null ? contentType : "application/octet-stream"));
          }
        } else if (part.getToolRequest() != null) {
          // Tool request (function call from model)
          ToolRequest toolReq = part.getToolRequest();
          FunctionCall.Builder fcBuilder = FunctionCall.builder().name(toolReq.getName());
          if (toolReq.getInput() != null) {
            @SuppressWarnings("unchecked")
            Map<String, Object> args = (Map<String, Object>) toolReq.getInput();
            fcBuilder.args(args);
          }
          parts.add(com.google.genai.types.Part.builder().functionCall(fcBuilder.build()).build());
        } else if (part.getToolResponse() != null) {
          // Tool response
          ToolResponse toolResp = part.getToolResponse();
          FunctionResponse.Builder frBuilder = FunctionResponse.builder().name(toolResp.getName());
          if (toolResp.getOutput() != null) {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = toolResp.getOutput() instanceof Map
                ? (Map<String, Object>) toolResp.getOutput()
                : Map.of("result", toolResp.getOutput());
            frBuilder.response(response);
          }
          parts.add(com.google.genai.types.Part.builder().functionResponse(frBuilder.build()).build());
        }
      }

      // Convert Genkit role to Gemini role
      String geminiRole = toGeminiRole(message.getRole());
      Content content = Content.builder().role(geminiRole).parts(parts).build();
      contents.add(content);
    }

    return contents;
  }

  /**
   * Converts Genkit role to Gemini role. Gemini only supports "user" and "model"
   * roles. TOOL role maps to "user" as it represents the user providing function
   * results.
   */
  private String toGeminiRole(Role role) {
    switch (role) {
      case USER :
        return "user";
      case MODEL :
        return "model";
      case TOOL :
        // Tool responses are sent as user role in Gemini
        return "user";
      default :
        return "user";
    }
  }

  private Message findSystemMessage(ModelRequest request) {
    for (Message message : request.getMessages()) {
      if (message.getRole() == Role.SYSTEM) {
        return message;
      }
    }
    return null;
  }

  private String getTextFromMessage(Message message) {
    StringBuilder sb = new StringBuilder();
    for (com.google.genkit.ai.Part part : message.getContent()) {
      if (part.getText() != null) {
        sb.append(part.getText());
      }
    }
    return sb.toString();
  }

  private ModelResponse parseResponse(GenerateContentResponse response) {
    ModelResponse modelResponse = new ModelResponse();
    List<com.google.genkit.ai.Candidate> candidates = new ArrayList<>();

    if (response.candidates().isPresent()) {
      for (com.google.genai.types.Candidate candidate : response.candidates().get()) {
        com.google.genkit.ai.Candidate genkitCandidate = new com.google.genkit.ai.Candidate();

        Message message = new Message();
        message.setRole(Role.MODEL);
        List<com.google.genkit.ai.Part> parts = new ArrayList<>();

        if (candidate.content().isPresent()) {
          Content content = candidate.content().get();
          if (content.parts().isPresent()) {
            for (com.google.genai.types.Part part : content.parts().get()) {
              // Text content
              if (part.text().isPresent()) {
                com.google.genkit.ai.Part textPart = new com.google.genkit.ai.Part();
                textPart.setText(part.text().get());
                parts.add(textPart);
              }

              // Function call
              if (part.functionCall().isPresent()) {
                FunctionCall fc = part.functionCall().get();
                com.google.genkit.ai.Part toolPart = new com.google.genkit.ai.Part();
                ToolRequest toolRequest = new ToolRequest();
                toolRequest.setName(fc.name().orElse(""));
                if (fc.args().isPresent()) {
                  toolRequest.setInput(fc.args().get());
                }
                toolPart.setToolRequest(toolRequest);
                parts.add(toolPart);
              }
            }
          }
        }

        message.setContent(parts);
        genkitCandidate.setMessage(message);

        // Map finish reason
        if (candidate.finishReason().isPresent()) {
          genkitCandidate.setFinishReason(mapFinishReason(candidate.finishReason().get().toString()));
        }

        candidates.add(genkitCandidate);
      }
    }

    modelResponse.setCandidates(candidates);

    // Usage metadata
    if (response.usageMetadata().isPresent()) {
      com.google.genai.types.GenerateContentResponseUsageMetadata usage = response.usageMetadata().get();
      Usage genkitUsage = new Usage();
      if (usage.promptTokenCount().isPresent()) {
        genkitUsage.setInputTokens(usage.promptTokenCount().get());
      }
      if (usage.candidatesTokenCount().isPresent()) {
        genkitUsage.setOutputTokens(usage.candidatesTokenCount().get());
      }
      if (usage.totalTokenCount().isPresent()) {
        genkitUsage.setTotalTokens(usage.totalTokenCount().get());
      }
      modelResponse.setUsage(genkitUsage);
    }

    return modelResponse;
  }

  private com.google.genkit.ai.FinishReason mapFinishReason(String reason) {
    if (reason == null) {
      return com.google.genkit.ai.FinishReason.OTHER;
    }
    switch (reason.toUpperCase()) {
      case "STOP" :
        return com.google.genkit.ai.FinishReason.STOP;
      case "MAX_TOKENS" :
      case "LENGTH" :
        return com.google.genkit.ai.FinishReason.LENGTH;
      case "SAFETY" :
        return com.google.genkit.ai.FinishReason.BLOCKED;
      case "RECITATION" :
        return com.google.genkit.ai.FinishReason.BLOCKED;
      default :
        return com.google.genkit.ai.FinishReason.OTHER;
    }
  }
}
