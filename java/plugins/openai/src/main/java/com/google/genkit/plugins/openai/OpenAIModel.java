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
import java.util.*;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.genkit.ai.*;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

import okhttp3.*;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSourceListener;
import okhttp3.sse.EventSources;

/**
 * OpenAI model implementation for Genkit.
 */
public class OpenAIModel implements Model {

  private static final Logger logger = LoggerFactory.getLogger(OpenAIModel.class);
  private static final MediaType JSON_MEDIA_TYPE = MediaType.parse("application/json");

  private final String modelName;
  private final OpenAIPluginOptions options;
  private final OkHttpClient client;
  private final ObjectMapper objectMapper;
  private final ModelInfo info;

  /**
   * Creates a new OpenAIModel.
   *
   * @param modelName
   *            the model name
   * @param options
   *            the plugin options
   */
  public OpenAIModel(String modelName, OpenAIPluginOptions options) {
    this.modelName = modelName;
    this.options = options;
    this.objectMapper = new ObjectMapper();
    this.client = new OkHttpClient.Builder().connectTimeout(options.getTimeout(), TimeUnit.SECONDS)
        .readTimeout(options.getTimeout(), TimeUnit.SECONDS)
        .writeTimeout(options.getTimeout(), TimeUnit.SECONDS).build();
    this.info = createModelInfo();
  }

  private ModelInfo createModelInfo() {
    ModelInfo info = new ModelInfo();
    info.setLabel("OpenAI " + modelName);

    ModelInfo.ModelCapabilities caps = new ModelInfo.ModelCapabilities();
    caps.setMultiturn(true);
    caps.setMedia(modelName.contains("gpt-4o") || modelName.contains("gpt-4-vision"));
    caps.setTools(!modelName.startsWith("o1"));
    caps.setSystemRole(!modelName.startsWith("o1"));
    caps.setOutput(Set.of("text", "json"));
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
    return true;
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request) {
    try {
      return callOpenAI(request);
    } catch (IOException e) {
      throw new GenkitException("OpenAI API call failed", e);
    }
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    if (streamCallback == null) {
      return run(context, request);
    }
    try {
      return callOpenAIStreaming(request, streamCallback);
    } catch (Exception e) {
      throw new GenkitException("OpenAI streaming API call failed", e);
    }
  }

  private ModelResponse callOpenAI(ModelRequest request) throws IOException {
    ObjectNode requestBody = buildRequestBody(request);

    Request httpRequest = new Request.Builder().url(options.getBaseUrl() + "/chat/completions")
        .header("Authorization", "Bearer " + options.getApiKey()).header("Content-Type", "application/json")
        .post(RequestBody.create(requestBody.toString(), JSON_MEDIA_TYPE)).build();

    if (options.getOrganization() != null) {
      httpRequest = httpRequest.newBuilder().header("OpenAI-Organization", options.getOrganization()).build();
    }

    try (Response response = client.newCall(httpRequest).execute()) {
      if (!response.isSuccessful()) {
        String errorBody = response.body() != null ? response.body().string() : "No error body";
        throw new GenkitException("OpenAI API error: " + response.code() + " - " + errorBody);
      }

      String responseBody = response.body().string();
      return parseResponse(responseBody);
    }
  }

  private ModelResponse callOpenAIStreaming(ModelRequest request, Consumer<ModelResponseChunk> streamCallback)
      throws IOException, InterruptedException {
    ObjectNode requestBody = buildRequestBody(request);
    requestBody.put("stream", true);

    Request httpRequest = new Request.Builder().url(options.getBaseUrl() + "/chat/completions")
        .header("Authorization", "Bearer " + options.getApiKey()).header("Content-Type", "application/json")
        .header("Accept", "text/event-stream").post(RequestBody.create(requestBody.toString(), JSON_MEDIA_TYPE))
        .build();

    if (options.getOrganization() != null) {
      httpRequest = httpRequest.newBuilder().header("OpenAI-Organization", options.getOrganization()).build();
    }

    StringBuilder fullContent = new StringBuilder();
    AtomicReference<String> finishReason = new AtomicReference<>();
    AtomicReference<GenkitException> error = new AtomicReference<>();
    CountDownLatch latch = new CountDownLatch(1);

    // Track tool calls being streamed (tool calls come in chunks)
    List<Map<String, Object>> toolCallsInProgress = new ArrayList<>();

    EventSourceListener listener = new EventSourceListener() {
      @Override
      public void onEvent(EventSource eventSource, String id, String type, String data) {
        if ("[DONE]".equals(data)) {
          latch.countDown();
          return;
        }

        try {
          JsonNode chunk = objectMapper.readTree(data);
          JsonNode choices = chunk.get("choices");
          if (choices != null && choices.isArray() && choices.size() > 0) {
            JsonNode choice = choices.get(0);
            JsonNode delta = choice.get("delta");

            if (delta != null) {
              // Handle text content
              JsonNode contentNode = delta.get("content");
              if (contentNode != null && !contentNode.isNull()) {
                String text = contentNode.asText();
                fullContent.append(text);

                // Create and send chunk
                ModelResponseChunk responseChunk = ModelResponseChunk.text(text);
                responseChunk.setIndex(choice.has("index") ? choice.get("index").asInt() : 0);
                streamCallback.accept(responseChunk);
              }

              // Handle tool calls (streamed incrementally)
              JsonNode toolCallsNode = delta.get("tool_calls");
              if (toolCallsNode != null && toolCallsNode.isArray()) {
                for (JsonNode toolCallDelta : toolCallsNode) {
                  int index = toolCallDelta.has("index") ? toolCallDelta.get("index").asInt() : 0;

                  // Expand list if needed
                  while (toolCallsInProgress.size() <= index) {
                    Map<String, Object> newToolCall = new java.util.HashMap<>();
                    newToolCall.put("arguments", new StringBuilder());
                    toolCallsInProgress.add(newToolCall);
                  }

                  Map<String, Object> toolCall = toolCallsInProgress.get(index);

                  // Capture id if present
                  if (toolCallDelta.has("id")) {
                    toolCall.put("id", toolCallDelta.get("id").asText());
                  }

                  // Capture function name and arguments
                  JsonNode functionNode = toolCallDelta.get("function");
                  if (functionNode != null) {
                    if (functionNode.has("name")) {
                      toolCall.put("name", functionNode.get("name").asText());
                    }
                    if (functionNode.has("arguments")) {
                      StringBuilder args = (StringBuilder) toolCall.get("arguments");
                      args.append(functionNode.get("arguments").asText());
                    }
                  }
                }
              }
            }

            JsonNode finishReasonNode = choice.get("finish_reason");
            if (finishReasonNode != null && !finishReasonNode.isNull()) {
              finishReason.set(finishReasonNode.asText());
            }
          }
        } catch (Exception e) {
          logger.error("Error parsing streaming chunk", e);
        }
      }

      @Override
      public void onFailure(EventSource eventSource, Throwable t, Response response) {
        String errorMsg = "Streaming failed";
        if (response != null) {
          try {
            errorMsg = "Streaming failed: " + response.code();
            if (response.body() != null) {
              errorMsg += " - " + response.body().string();
            }
          } catch (IOException e) {
            // Ignore
          }
        }
        error.set(new GenkitException(errorMsg, t));
        latch.countDown();
      }

      @Override
      public void onClosed(EventSource eventSource) {
        latch.countDown();
      }
    };

    EventSource.Factory factory = EventSources.createFactory(client);
    EventSource eventSource = factory.newEventSource(httpRequest, listener);

    // Wait for streaming to complete
    boolean completed = latch.await(options.getTimeout(), TimeUnit.SECONDS);
    if (!completed) {
      eventSource.cancel();
      throw new GenkitException("Streaming request timed out");
    }

    if (error.get() != null) {
      throw error.get();
    }

    // Build the final response
    ModelResponse response = new ModelResponse();
    List<Candidate> candidates = new ArrayList<>();
    Candidate candidate = new Candidate();

    Message message = new Message();
    message.setRole(Role.MODEL);
    List<Part> parts = new ArrayList<>();

    // Add text content if present
    if (fullContent.length() > 0) {
      Part textPart = new Part();
      textPart.setText(fullContent.toString());
      parts.add(textPart);
    }

    // Add tool calls if present
    for (Map<String, Object> toolCall : toolCallsInProgress) {
      String toolId = (String) toolCall.get("id");
      String toolName = (String) toolCall.get("name");
      StringBuilder argsBuilder = (StringBuilder) toolCall.get("arguments");

      if (toolId != null && toolName != null) {
        Part toolPart = new Part();
        ToolRequest toolRequest = new ToolRequest();
        toolRequest.setRef(toolId);
        toolRequest.setName(toolName);

        // Parse arguments JSON
        String argsJson = argsBuilder.toString();
        if (argsJson != null && !argsJson.isEmpty()) {
          try {
            @SuppressWarnings("unchecked")
            Map<String, Object> args = objectMapper.readValue(argsJson, Map.class);
            toolRequest.setInput(args);
          } catch (Exception e) {
            logger.warn("Failed to parse tool arguments: {}", argsJson, e);
            toolRequest.setInput(new java.util.HashMap<>());
          }
        }

        toolPart.setToolRequest(toolRequest);
        parts.add(toolPart);
      }
    }

    message.setContent(parts);
    candidate.setMessage(message);

    // Set finish reason
    String reason = finishReason.get();
    if (reason != null) {
      switch (reason) {
        case "stop" :
          candidate.setFinishReason(FinishReason.STOP);
          break;
        case "length" :
          candidate.setFinishReason(FinishReason.LENGTH);
          break;
        case "tool_calls" :
          candidate.setFinishReason(FinishReason.OTHER);
          break;
        default :
          candidate.setFinishReason(FinishReason.OTHER);
      }
    }

    candidates.add(candidate);
    response.setCandidates(candidates);

    return response;
  }

  private ObjectNode buildRequestBody(ModelRequest request) {
    ObjectNode body = objectMapper.createObjectNode();
    body.put("model", modelName);

    // Convert messages
    ArrayNode messages = body.putArray("messages");
    for (Message message : request.getMessages()) {
      ObjectNode msg = messages.addObject();
      String role = convertRole(message.getRole());
      msg.put("role", role);

      // Handle content
      List<Part> content = message.getContent();

      // Check if this message contains tool requests (assistant with tool_calls)
      boolean hasToolRequests = content.stream().anyMatch(p -> p.getToolRequest() != null);
      // Check if this message contains tool responses
      boolean hasToolResponses = content.stream().anyMatch(p -> p.getToolResponse() != null);

      if (hasToolRequests) {
        // Assistant message with tool calls
        // Add text content if present
        String textContent = content.stream().filter(p -> p.getText() != null).map(Part::getText).findFirst()
            .orElse(null);
        if (textContent != null) {
          msg.put("content", textContent);
        } else {
          msg.putNull("content");
        }

        // Add tool_calls array
        ArrayNode toolCallsArray = msg.putArray("tool_calls");
        for (Part part : content) {
          if (part.getToolRequest() != null) {
            ToolRequest toolReq = part.getToolRequest();
            ObjectNode toolCall = toolCallsArray.addObject();
            toolCall.put("id", toolReq.getRef());
            toolCall.put("type", "function");
            ObjectNode function = toolCall.putObject("function");
            function.put("name", toolReq.getName());
            if (toolReq.getInput() != null) {
              try {
                function.put("arguments", objectMapper.writeValueAsString(toolReq.getInput()));
              } catch (Exception e) {
                function.put("arguments", "{}");
              }
            } else {
              function.put("arguments", "{}");
            }
          }
        }
      } else if (hasToolResponses) {
        // Tool response messages - each tool response is a separate message
        // Remove the current message from array and add individual tool responses
        messages.remove(messages.size() - 1);

        for (Part part : content) {
          if (part.getToolResponse() != null) {
            ToolResponse toolResp = part.getToolResponse();
            ObjectNode toolMsg = messages.addObject();
            toolMsg.put("role", "tool");
            toolMsg.put("tool_call_id", toolResp.getRef());

            // Convert output to string
            String outputStr;
            if (toolResp.getOutput() instanceof String) {
              outputStr = (String) toolResp.getOutput();
            } else {
              try {
                outputStr = objectMapper.writeValueAsString(toolResp.getOutput());
              } catch (Exception e) {
                outputStr = String.valueOf(toolResp.getOutput());
              }
            }
            toolMsg.put("content", outputStr);
          }
        }
      } else if (content.size() == 1 && content.get(0).getText() != null) {
        // Simple text message
        msg.put("content", content.get(0).getText());
      } else {
        // Multi-part message
        ArrayNode contentArray = msg.putArray("content");
        for (Part part : content) {
          ObjectNode partNode = contentArray.addObject();
          if (part.getText() != null) {
            partNode.put("type", "text");
            partNode.put("text", part.getText());
          } else if (part.getMedia() != null) {
            partNode.put("type", "image_url");
            ObjectNode imageUrl = partNode.putObject("image_url");
            imageUrl.put("url", part.getMedia().getUrl());
          }
        }
      }
    }

    // Add tools if present
    if (request.getTools() != null && !request.getTools().isEmpty()) {
      ArrayNode tools = body.putArray("tools");
      for (ToolDefinition tool : request.getTools()) {
        ObjectNode toolNode = tools.addObject();
        toolNode.put("type", "function");
        ObjectNode function = toolNode.putObject("function");
        function.put("name", tool.getName());
        if (tool.getDescription() != null) {
          function.put("description", tool.getDescription());
        }
        if (tool.getInputSchema() != null) {
          function.set("parameters", objectMapper.valueToTree(tool.getInputSchema()));
        }
      }
    }

    // Add generation config
    Map<String, Object> config = request.getConfig();
    if (config != null) {
      if (config.containsKey("temperature")) {
        body.put("temperature", ((Number) config.get("temperature")).doubleValue());
      }
      if (config.containsKey("maxOutputTokens")) {
        body.put("max_tokens", ((Number) config.get("maxOutputTokens")).intValue());
      }
      if (config.containsKey("topP")) {
        body.put("top_p", ((Number) config.get("topP")).doubleValue());
      }
      if (config.containsKey("presencePenalty")) {
        body.put("presence_penalty", ((Number) config.get("presencePenalty")).doubleValue());
      }
      if (config.containsKey("frequencyPenalty")) {
        body.put("frequency_penalty", ((Number) config.get("frequencyPenalty")).doubleValue());
      }
      if (config.containsKey("stopSequences")) {
        ArrayNode stop = body.putArray("stop");
        @SuppressWarnings("unchecked")
        List<String> stopSequences = (List<String>) config.get("stopSequences");
        for (String seq : stopSequences) {
          stop.add(seq);
        }
      }
      if (config.containsKey("seed")) {
        body.put("seed", ((Number) config.get("seed")).intValue());
      }
    }

    // Handle output format
    OutputConfig output = request.getOutput();
    if (output != null && output.getFormat() == OutputFormat.JSON) {
      ObjectNode responseFormat = body.putObject("response_format");
      responseFormat.put("type", "json_object");
    }

    return body;
  }

  private String convertRole(Role role) {
    switch (role) {
      case SYSTEM :
        return "system";
      case USER :
        return "user";
      case MODEL :
        return "assistant";
      case TOOL :
        return "tool";
      default :
        return "user";
    }
  }

  private ModelResponse parseResponse(String responseBody) throws IOException {
    JsonNode root = objectMapper.readTree(responseBody);

    ModelResponse response = new ModelResponse();
    List<Candidate> candidates = new ArrayList<>();

    JsonNode choices = root.get("choices");
    if (choices != null && choices.isArray()) {
      for (JsonNode choice : choices) {
        Candidate candidate = new Candidate();

        // Parse message
        JsonNode messageNode = choice.get("message");
        if (messageNode != null) {
          Message message = new Message();
          message.setRole(Role.MODEL);

          List<Part> parts = new ArrayList<>();

          // Text content
          JsonNode contentNode = messageNode.get("content");
          if (contentNode != null && !contentNode.isNull()) {
            Part part = new Part();
            part.setText(contentNode.asText());
            parts.add(part);
          }

          // Tool calls
          JsonNode toolCallsNode = messageNode.get("tool_calls");
          if (toolCallsNode != null && toolCallsNode.isArray()) {
            for (JsonNode toolCallNode : toolCallsNode) {
              Part part = new Part();
              ToolRequest toolRequest = new ToolRequest();
              toolRequest.setRef(toolCallNode.get("id").asText());

              JsonNode functionNode = toolCallNode.get("function");
              if (functionNode != null) {
                toolRequest.setName(functionNode.get("name").asText());
                JsonNode argsNode = functionNode.get("arguments");
                if (argsNode != null) {
                  toolRequest.setInput(objectMapper.readValue(argsNode.asText(), Map.class));
                }
              }

              part.setToolRequest(toolRequest);
              parts.add(part);
            }
          }

          message.setContent(parts);
          candidate.setMessage(message);
        }

        // Parse finish reason
        JsonNode finishReasonNode = choice.get("finish_reason");
        if (finishReasonNode != null) {
          String reason = finishReasonNode.asText();
          switch (reason) {
            case "stop" :
              candidate.setFinishReason(FinishReason.STOP);
              break;
            case "length" :
              candidate.setFinishReason(FinishReason.LENGTH);
              break;
            case "tool_calls" :
              candidate.setFinishReason(FinishReason.STOP);
              break;
            case "content_filter" :
              candidate.setFinishReason(FinishReason.BLOCKED);
              break;
            default :
              candidate.setFinishReason(FinishReason.OTHER);
          }
        }

        candidates.add(candidate);
      }
    }

    response.setCandidates(candidates);

    // Parse usage
    JsonNode usageNode = root.get("usage");
    if (usageNode != null) {
      Usage usage = new Usage();
      if (usageNode.has("prompt_tokens")) {
        usage.setInputTokens(usageNode.get("prompt_tokens").asInt());
      }
      if (usageNode.has("completion_tokens")) {
        usage.setOutputTokens(usageNode.get("completion_tokens").asInt());
      }
      if (usageNode.has("total_tokens")) {
        usage.setTotalTokens(usageNode.get("total_tokens").asInt());
      }
      response.setUsage(usage);
    }

    return response;
  }
}
