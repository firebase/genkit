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

package com.google.genkit.ai.session;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

import com.google.genkit.ai.*;
import com.google.genkit.core.Action;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.ActionType;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.JsonUtils;
import com.google.genkit.core.Registry;

/**
 * Chat represents a conversation within a session thread.
 *
 * <p>
 * Chat provides a simple interface for multi-turn conversations with automatic
 * history management. Messages are persisted to the session store after each
 * interaction.
 *
 * <p>
 * Example usage:
 * 
 * <pre>{@code
 * // Simple chat
 * Chat<MyState> chat = session.chat();
 * ModelResponse response = chat.send("Hello!");
 * 
 * // Chat with system prompt
 * Chat<MyState> chat = session
 * 		.chat(ChatOptions.<MyState>builder().model("openai/gpt-4o").system("You are a helpful assistant.").build());
 * 
 * // Multi-turn conversation
 * chat.send("What is the capital of France?");
 * chat.send("And what about Germany?"); // Context is preserved
 * }</pre>
 *
 * @param <S>
 *            the type of the session state
 */
public class Chat<S> {

  private static final String PREAMBLE_KEY = "preamble";

  private final Session<S> session;
  private final String threadName;
  private final ChatOptions<S> originalOptions;
  private final Registry registry;
  private final Map<String, Agent> effectiveAgentRegistry;
  private List<Message> history;

  /** Pending interrupt requests from the last send. */
  private List<InterruptRequest> pendingInterrupts;

  /** Current agent context (mutable for handoffs). */
  private String currentAgentName;
  private String currentSystem;
  private String currentModel;
  private List<Tool<?, ?>> currentTools;

  /**
   * Creates a new Chat instance.
   *
   * @param session
   *            the parent session
   * @param threadName
   *            the thread name
   * @param options
   *            the chat options
   * @param registry
   *            the Genkit registry
   * @param sessionAgentRegistry
   *            the agent registry from the session (may be null)
   */
  Chat(Session<S> session, String threadName, ChatOptions<S> options, Registry registry,
      Map<String, Agent> sessionAgentRegistry) {
    this.session = session;
    this.threadName = threadName;
    this.originalOptions = options;
    this.registry = registry;
    // Use agent registry from options if provided, otherwise fall back to session's
    // registry
    this.effectiveAgentRegistry = options.getAgentRegistry() != null
        ? options.getAgentRegistry()
        : sessionAgentRegistry;
    this.history = new ArrayList<>(session.getMessages(threadName));
    this.pendingInterrupts = new ArrayList<>();

    // Initialize current context from options
    this.currentAgentName = null;
    this.currentSystem = options.getSystem();
    this.currentModel = options.getModel();
    this.currentTools = options.getTools();
  }

  /**
   * Sends a message and gets a response.
   *
   * <p>
   * This method:
   * <ol>
   * <li>Adds the user message to history</li>
   * <li>Builds a request with all conversation history</li>
   * <li>Sends to the model and gets a response</li>
   * <li>Adds the model response to history</li>
   * <li>Persists the updated history</li>
   * </ol>
   *
   * @param text
   *            the user message
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse send(String text) throws GenkitException {
    return send(Message.user(text));
  }

  /**
   * Sends a message and gets a response.
   *
   * @param message
   *            the message to send
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse send(Message message) throws GenkitException {
    return send(message, null);
  }

  /**
   * Sends a message with send options and gets a response.
   *
   * @param text
   *            the user message
   * @param sendOptions
   *            additional options for this send
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse send(String text, SendOptions sendOptions) throws GenkitException {
    return send(Message.user(text), sendOptions);
  }

  /**
   * Sends a message with send options and gets a response.
   *
   * @param message
   *            the message to send
   * @param sendOptions
   *            additional options for this send
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse send(Message message, SendOptions sendOptions) throws GenkitException {
    // Clear any pending interrupts from previous send
    pendingInterrupts.clear();

    // Check if we're resuming from an interrupt
    ResumeOptions resumeOptions = (sendOptions != null) ? sendOptions.getResumeOptions() : null;
    if (resumeOptions != null) {
      return resumeFromInterrupt(resumeOptions, sendOptions);
    }

    // Add user message to history
    history.add(message);

    return executeGenerationLoop(sendOptions);
  }

  /**
   * Resumes generation after an interrupt.
   *
   * @param resumeOptions
   *            the resume options containing tool responses
   * @param sendOptions
   *            additional send options
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  private ModelResponse resumeFromInterrupt(ResumeOptions resumeOptions, SendOptions sendOptions)
      throws GenkitException {
    // Add tool responses to history
    if (resumeOptions.getRespond() != null && !resumeOptions.getRespond().isEmpty()) {
      List<Part> responseParts = new ArrayList<>();
      for (ToolResponse response : resumeOptions.getRespond()) {
        Part part = new Part();
        part.setToolResponse(response);
        responseParts.add(part);
      }
      Message toolResponseMessage = new Message();
      toolResponseMessage.setRole(Role.TOOL);
      toolResponseMessage.setContent(responseParts);
      history.add(toolResponseMessage);
    }

    // Handle restart requests by re-executing those tools
    if (resumeOptions.getRestart() != null && !resumeOptions.getRestart().isEmpty()) {
      ActionContext ctx = new ActionContext(registry);
      List<Part> restartParts = executeToolsWithInterruptHandling(ctx, resumeOptions.getRestart(), sendOptions);

      // Check if any restarts also triggered interrupts
      if (!pendingInterrupts.isEmpty()) {
        persistHistory();
        return createInterruptResponse();
      }

      Message toolResponseMessage = new Message();
      toolResponseMessage.setRole(Role.TOOL);
      toolResponseMessage.setContent(restartParts);
      history.add(toolResponseMessage);
    }

    return executeGenerationLoop(sendOptions);
  }

  /**
   * Executes the main generation loop with tool handling.
   */
  private ModelResponse executeGenerationLoop(SendOptions sendOptions) throws GenkitException {
    // Build the request
    ModelRequest request = buildRequest(sendOptions);

    // Get the model
    String modelName = resolveModelName(sendOptions);
    if (modelName == null) {
      throw new GenkitException("No model specified. Set model in ChatOptions or SendOptions.");
    }

    Model model = getModel(modelName);
    ActionContext ctx = new ActionContext(registry);

    // Handle tool execution loop with session context
    int maxTurns = resolveMaxTurns(sendOptions);
    int turn = 0;

    while (turn < maxTurns) {
      // Make request effectively final for lambda
      final ModelRequest finalRequest = request;
      ModelResponse response;
      try {
        response = SessionContext.runWithSession(session, () -> model.run(ctx, finalRequest));
      } catch (GenkitException e) {
        throw e;
      } catch (Exception e) {
        throw new GenkitException("Error during model execution", e);
      }

      // Check for tool requests
      List<ToolRequest> toolRequests = extractToolRequests(response);
      if (toolRequests.isEmpty()) {
        // No tool calls, add response to history and persist
        Message responseMessage = response.getMessage();
        if (responseMessage != null) {
          history.add(responseMessage);
          persistHistory();
        }
        return response;
      }

      // Execute tools with interrupt handling
      List<Part> toolResponseParts = executeToolsWithInterruptHandling(ctx, toolRequests, sendOptions);

      // Add assistant message with tool requests to history
      Message assistantMessage = response.getMessage();
      if (assistantMessage != null) {
        history.add(assistantMessage);
      }

      // Check if any tools triggered interrupts
      if (!pendingInterrupts.isEmpty()) {
        persistHistory();
        return createInterruptResponse();
      }

      // Add tool response message to history
      Message toolResponseMessage = new Message();
      toolResponseMessage.setRole(Role.TOOL);
      toolResponseMessage.setContent(toolResponseParts);
      history.add(toolResponseMessage);

      // Rebuild request with updated history
      request = buildRequest(sendOptions);
      turn++;
    }

    throw new GenkitException("Max tool execution turns (" + maxTurns + ") exceeded");
  }

  /**
   * Sends a message with streaming response.
   *
   * @param text
   *            the user message
   * @param streamCallback
   *            callback for each response chunk
   * @return the final aggregated response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse sendStream(String text, Consumer<ModelResponseChunk> streamCallback) throws GenkitException {
    return sendStream(Message.user(text), null, streamCallback);
  }

  /**
   * Sends a message with streaming response.
   *
   * @param message
   *            the message to send
   * @param sendOptions
   *            additional options for this send
   * @param streamCallback
   *            callback for each response chunk
   * @return the final aggregated response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse sendStream(Message message, SendOptions sendOptions,
      Consumer<ModelResponseChunk> streamCallback) throws GenkitException {
    // Add user message to history
    history.add(message);

    // Build the request
    ModelRequest request = buildRequest(sendOptions);

    // Get the model
    String modelName = resolveModelName(sendOptions);
    if (modelName == null) {
      throw new GenkitException("No model specified. Set model in ChatOptions or SendOptions.");
    }

    Model model = getModel(modelName);
    if (!model.supportsStreaming()) {
      throw new GenkitException("Model " + modelName + " does not support streaming");
    }

    ActionContext ctx = new ActionContext(registry);
    ModelResponse response = model.run(ctx, request, streamCallback);

    // Add response to history and persist
    Message responseMessage = response.getMessage();
    if (responseMessage != null) {
      history.add(responseMessage);
      persistHistory();
    }

    return response;
  }

  /**
   * Gets the current conversation history.
   *
   * @return a copy of the message history
   */
  public List<Message> getHistory() {
    return new ArrayList<>(history);
  }

  /**
   * Gets the session.
   *
   * @return the parent session
   */
  public Session<S> getSession() {
    return session;
  }

  /**
   * Gets the thread name.
   *
   * @return the thread name
   */
  public String getThreadName() {
    return threadName;
  }

  /**
   * Gets the pending interrupt requests from the last send.
   *
   * <p>
   * If the last {@link #send} call returned with interrupts, this method returns
   * the list of pending interrupts that need to be resolved before continuing.
   *
   * @return the list of pending interrupt requests (empty if none)
   */
  public List<InterruptRequest> getPendingInterrupts() {
    return new ArrayList<>(pendingInterrupts);
  }

  /**
   * Checks if there are pending interrupts.
   *
   * @return true if there are pending interrupts
   */
  public boolean hasPendingInterrupts() {
    return !pendingInterrupts.isEmpty();
  }

  /**
   * Gets the current agent name.
   *
   * <p>
   * Returns null if no agent handoff has occurred, otherwise returns the name of
   * the agent that the conversation was most recently handed off to.
   *
   * @return the current agent name, or null if no handoff has occurred
   */
  public String getCurrentAgentName() {
    return currentAgentName;
  }

  /**
   * Builds a ModelRequest from current history and options.
   */
  private ModelRequest buildRequest(SendOptions sendOptions) {
    ModelRequest.Builder builder = ModelRequest.builder();

    // Build messages list with system prompt (preamble)
    List<Message> messages = new ArrayList<>();

    // Add system prompt if specified (use current context for handoffs)
    String systemPrompt = currentSystem;
    if (systemPrompt != null && !systemPrompt.isEmpty()) {
      Message systemMessage = Message.system(systemPrompt);
      // Mark as preamble in metadata
      Map<String, Object> metadata = new HashMap<>();
      metadata.put(PREAMBLE_KEY, true);
      systemMessage.setMetadata(metadata);
      messages.add(systemMessage);
    }

    // Add conversation history (excluding any existing preamble)
    for (Message msg : history) {
      if (!isPreamble(msg)) {
        messages.add(msg);
      }
    }

    builder.messages(messages);

    // Add tools (use current context for handoffs)
    List<Tool<?, ?>> tools = resolveTools(sendOptions);
    if (tools != null && !tools.isEmpty()) {
      List<ToolDefinition> toolDefs = new ArrayList<>();
      for (Tool<?, ?> tool : tools) {
        toolDefs.add(tool.getDefinition());
      }
      builder.tools(toolDefs);
    }

    // Add config
    if (originalOptions.getConfig() != null) {
      builder.config(convertConfigToMap(originalOptions.getConfig()));
    }

    // Add output config
    if (originalOptions.getOutput() != null) {
      builder.output(originalOptions.getOutput());
    }

    return builder.build();
  }

  /**
   * Checks if a message is a preamble (system prompt).
   */
  private boolean isPreamble(Message message) {
    if (message.getMetadata() == null) {
      return false;
    }
    Object preamble = message.getMetadata().get(PREAMBLE_KEY);
    return Boolean.TRUE.equals(preamble);
  }

  /**
   * Resolves the model name from options.
   */
  private String resolveModelName(SendOptions sendOptions) {
    if (sendOptions != null && sendOptions.getModel() != null) {
      return sendOptions.getModel();
    }
    // Use current context (which may have been updated by handoff)
    return currentModel;
  }

  /**
   * Resolves the max turns from options.
   */
  private int resolveMaxTurns(SendOptions sendOptions) {
    if (sendOptions != null && sendOptions.getMaxTurns() != null) {
      return sendOptions.getMaxTurns();
    }
    if (originalOptions.getMaxTurns() != null) {
      return originalOptions.getMaxTurns();
    }
    return 5; // Default
  }

  /**
   * Resolves the tools from options.
   */
  private List<Tool<?, ?>> resolveTools(SendOptions sendOptions) {
    if (sendOptions != null && sendOptions.getTools() != null) {
      return sendOptions.getTools();
    }
    // Use current context (which may have been updated by handoff)
    return currentTools;
  }

  /**
   * Gets a model by name from the registry.
   */
  private Model getModel(String name) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.MODEL, name);
    if (action == null) {
      throw new GenkitException("Model not found: " + name);
    }
    return (Model) action;
  }

  /**
   * Extracts tool requests from a model response.
   */
  private List<ToolRequest> extractToolRequests(ModelResponse response) {
    List<ToolRequest> requests = new ArrayList<>();
    if (response.getCandidates() != null) {
      for (Candidate candidate : response.getCandidates()) {
        if (candidate.getMessage() != null && candidate.getMessage().getContent() != null) {
          for (Part part : candidate.getMessage().getContent()) {
            if (part.getToolRequest() != null) {
              requests.add(part.getToolRequest());
            }
          }
        }
      }
    }
    return requests;
  }

  /**
   * Executes tools and returns response parts.
   */
  private List<Part> executeTools(ActionContext ctx, List<ToolRequest> toolRequests, SendOptions sendOptions) {
    List<Part> responseParts = new ArrayList<>();
    List<Tool<?, ?>> tools = resolveTools(sendOptions);

    for (ToolRequest toolRequest : toolRequests) {
      String toolName = toolRequest.getName();
      Object toolInput = toolRequest.getInput();

      Tool<?, ?> tool = findTool(toolName, tools);
      if (tool == null) {
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Collections.singletonMap("error", "Tool not found: " + toolName));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
        continue;
      }

      try {
        @SuppressWarnings("unchecked")
        Tool<Object, Object> typedTool = (Tool<Object, Object>) tool;

        // Convert the input to the expected type if necessary
        final Object convertedInput;
        Class<?> inputClass = typedTool.getInputClass();
        if (inputClass != null && toolInput != null && !inputClass.isInstance(toolInput)) {
          convertedInput = JsonUtils.convert(toolInput, inputClass);
        } else {
          convertedInput = toolInput;
        }

        Object result = SessionContext.runWithSession(session, () -> typedTool.run(ctx, convertedInput));

        Part responsePart = new Part();
        ToolResponse toolResponse = new ToolResponse(toolRequest.getRef(), toolName, result);
        responsePart.setToolResponse(toolResponse);
        responseParts.add(responsePart);
      } catch (Exception e) {
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Collections.singletonMap("error", "Tool execution failed: " + e.getMessage()));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
      }
    }

    return responseParts;
  }

  /**
   * Executes tools with interrupt handling and returns response parts.
   * 
   * <p>
   * When a tool throws {@link ToolInterruptException}, the interrupt is captured
   * and added to the pending interrupts list. The tool execution continues for
   * other tools, and an interrupt response is returned after all tools have been
   * processed.
   *
   * <p>
   * When a tool throws {@link AgentHandoffException}, the chat context is
   * switched to the target agent (system prompt, tools, model), enabling
   * multi-agent conversations.
   */
  private List<Part> executeToolsWithInterruptHandling(ActionContext ctx, List<ToolRequest> toolRequests,
      SendOptions sendOptions) {
    List<Part> responseParts = new ArrayList<>();
    List<Tool<?, ?>> tools = resolveTools(sendOptions);

    for (ToolRequest toolRequest : toolRequests) {
      String toolName = toolRequest.getName();
      Object toolInput = toolRequest.getInput();

      Tool<?, ?> tool = findTool(toolName, tools);
      if (tool == null) {
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Collections.singletonMap("error", "Tool not found: " + toolName));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
        continue;
      }

      try {
        @SuppressWarnings("unchecked")
        Tool<Object, Object> typedTool = (Tool<Object, Object>) tool;

        // Convert the input to the expected type if necessary
        final Object convertedInput;
        Class<?> inputClass = typedTool.getInputClass();
        if (inputClass != null && toolInput != null && !inputClass.isInstance(toolInput)) {
          convertedInput = JsonUtils.convert(toolInput, inputClass);
        } else {
          convertedInput = toolInput;
        }

        Object result = SessionContext.runWithSession(session, () -> typedTool.run(ctx, convertedInput));

        Part responsePart = new Part();
        ToolResponse toolResponse = new ToolResponse(toolRequest.getRef(), toolName, result);
        responsePart.setToolResponse(toolResponse);
        responseParts.add(responsePart);
      } catch (AgentHandoffException e) {
        // Handle agent handoff - switch context to the target agent
        handleAgentHandoff(e);

        // Add a response indicating the handoff
        Part handoffPart = new Part();
        Map<String, Object> handoffOutput = new HashMap<>();
        handoffOutput.put("transferred", true);
        handoffOutput.put("transferredTo", e.getTargetAgentName());
        handoffOutput.put("message", "Conversation transferred to " + e.getTargetAgentName());
        ToolResponse handoffResponse = new ToolResponse(toolRequest.getRef(), toolName, handoffOutput);
        handoffPart.setToolResponse(handoffResponse);
        responseParts.add(handoffPart);
      } catch (ToolInterruptException e) {
        // Capture the interrupt
        InterruptRequest interruptRequest = new InterruptRequest(toolRequest, e.getMetadata());
        pendingInterrupts.add(interruptRequest);

        // Add a placeholder response indicating interruption
        Part interruptPart = new Part();
        Map<String, Object> interruptOutput = new HashMap<>();
        interruptOutput.put("__interrupt", true);
        interruptOutput.put("metadata", e.getMetadata());
        ToolResponse interruptResponse = new ToolResponse(toolRequest.getRef(), toolName, interruptOutput);
        interruptPart.setToolResponse(interruptResponse);
        responseParts.add(interruptPart);
      } catch (Exception e) {
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Collections.singletonMap("error", "Tool execution failed: " + e.getMessage()));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
      }
    }

    return responseParts;
  }

  /**
   * Handles an agent handoff by switching the chat context.
   */
  private void handleAgentHandoff(AgentHandoffException handoff) {
    AgentConfig targetConfig = handoff.getTargetAgentConfig();
    currentAgentName = handoff.getTargetAgentName();

    // Update system prompt
    if (targetConfig.getSystem() != null) {
      currentSystem = targetConfig.getSystem();
    }

    // Update model if specified
    if (targetConfig.getModel() != null) {
      currentModel = targetConfig.getModel();
    }

    // Update tools - include the agent's tools plus sub-agent tools
    List<Tool<?, ?>> newTools = new ArrayList<>();
    if (targetConfig.getTools() != null) {
      newTools.addAll(targetConfig.getTools());
    }

    // Add sub-agents as tools if agent registry is available
    if (targetConfig.getAgents() != null && effectiveAgentRegistry != null) {
      for (AgentConfig subAgentConfig : targetConfig.getAgents()) {
        Agent subAgent = effectiveAgentRegistry.get(subAgentConfig.getName());
        if (subAgent != null) {
          newTools.add(subAgent.asTool());
        }
      }
    }

    currentTools = newTools;
  }

  /**
   * Creates a response indicating the generation was interrupted.
   */
  private ModelResponse createInterruptResponse() {
    ModelResponse response = new ModelResponse();

    // Create a message indicating interruption
    Message interruptMessage = new Message();
    interruptMessage.setRole(Role.MODEL);

    Part textPart = new Part();
    textPart.setText("[Generation interrupted - awaiting user input]");
    interruptMessage.setContent(List.of(textPart));

    // Add interrupt metadata
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("interrupted", true);
    metadata.put("interruptCount", pendingInterrupts.size());
    List<Map<String, Object>> interruptData = new ArrayList<>();
    for (InterruptRequest interrupt : pendingInterrupts) {
      Map<String, Object> data = new HashMap<>();
      data.put("toolName", interrupt.getToolRequest().getName());
      data.put("toolRef", interrupt.getToolRequest().getRef());
      data.put("metadata", interrupt.getMetadata());
      interruptData.add(data);
    }
    metadata.put("interrupts", interruptData);
    interruptMessage.setMetadata(metadata);

    // Create candidate
    Candidate candidate = new Candidate();
    candidate.setMessage(interruptMessage);
    candidate.setFinishReason(FinishReason.OTHER);

    response.setCandidates(List.of(candidate));

    return response;
  }

  /**
   * Finds a tool by name.
   */
  private Tool<?, ?> findTool(String toolName, List<Tool<?, ?>> tools) {
    if (tools != null) {
      for (Tool<?, ?> tool : tools) {
        if (tool.getName().equals(toolName)) {
          return tool;
        }
      }
    }

    // Try registry
    Action<?, ?, ?> action = registry.lookupAction(ActionType.TOOL, toolName);
    if (action instanceof Tool) {
      return (Tool<?, ?>) action;
    }

    return null;
  }

  /**
   * Persists the current history to the session store.
   */
  private void persistHistory() {
    session.updateMessages(threadName, history).join();
  }

  /**
   * Converts GenerationConfig to a Map for the ModelRequest.
   */
  private Map<String, Object> convertConfigToMap(GenerationConfig config) {
    Map<String, Object> configMap = new HashMap<>();
    if (config.getTemperature() != null) {
      configMap.put("temperature", config.getTemperature());
    }
    if (config.getMaxOutputTokens() != null) {
      configMap.put("maxOutputTokens", config.getMaxOutputTokens());
    }
    if (config.getTopP() != null) {
      configMap.put("topP", config.getTopP());
    }
    if (config.getTopK() != null) {
      configMap.put("topK", config.getTopK());
    }
    if (config.getStopSequences() != null) {
      configMap.put("stopSequences", config.getStopSequences());
    }
    if (config.getPresencePenalty() != null) {
      configMap.put("presencePenalty", config.getPresencePenalty());
    }
    if (config.getFrequencyPenalty() != null) {
      configMap.put("frequencyPenalty", config.getFrequencyPenalty());
    }
    if (config.getSeed() != null) {
      configMap.put("seed", config.getSeed());
    }
    if (config.getCustom() != null) {
      configMap.putAll(config.getCustom());
    }
    return configMap;
  }

  /**
   * Options for individual send operations.
   */
  public static class SendOptions {
    private String model;
    private List<Tool<?, ?>> tools;
    private Integer maxTurns;
    private ResumeOptions resumeOptions;

    /**
     * Default constructor.
     */
    public SendOptions() {
    }

    /**
     * Gets the model name.
     *
     * @return the model name
     */
    public String getModel() {
      return model;
    }

    /**
     * Sets the model name.
     *
     * @param model
     *            the model name
     */
    public void setModel(String model) {
      this.model = model;
    }

    /**
     * Gets the tools.
     *
     * @return the tools
     */
    public List<Tool<?, ?>> getTools() {
      return tools;
    }

    /**
     * Sets the tools.
     *
     * @param tools
     *            the tools
     */
    public void setTools(List<Tool<?, ?>> tools) {
      this.tools = tools;
    }

    /**
     * Gets the max turns.
     *
     * @return the max turns
     */
    public Integer getMaxTurns() {
      return maxTurns;
    }

    /**
     * Sets the max turns.
     *
     * @param maxTurns
     *            the max turns
     */
    public void setMaxTurns(Integer maxTurns) {
      this.maxTurns = maxTurns;
    }

    /**
     * Gets the resume options.
     *
     * @return the resume options
     */
    public ResumeOptions getResumeOptions() {
      return resumeOptions;
    }

    /**
     * Sets the resume options.
     *
     * @param resumeOptions
     *            the resume options
     */
    public void setResumeOptions(ResumeOptions resumeOptions) {
      this.resumeOptions = resumeOptions;
    }

    /**
     * Creates a builder for SendOptions.
     *
     * @return a new builder
     */
    public static Builder builder() {
      return new Builder();
    }

    /**
     * Builder for SendOptions.
     */
    public static class Builder {
      private String model;
      private List<Tool<?, ?>> tools;
      private Integer maxTurns;
      private ResumeOptions resumeOptions;

      /**
       * Sets the model name.
       *
       * @param model
       *            the model name
       * @return this builder
       */
      public Builder model(String model) {
        this.model = model;
        return this;
      }

      /**
       * Sets the tools.
       *
       * @param tools
       *            the tools
       * @return this builder
       */
      public Builder tools(List<Tool<?, ?>> tools) {
        this.tools = tools;
        return this;
      }

      /**
       * Sets the max turns.
       *
       * @param maxTurns
       *            the max turns
       * @return this builder
       */
      public Builder maxTurns(Integer maxTurns) {
        this.maxTurns = maxTurns;
        return this;
      }

      /**
       * Sets the resume options for resuming after an interrupt.
       *
       * @param resumeOptions
       *            the resume options
       * @return this builder
       */
      public Builder resumeOptions(ResumeOptions resumeOptions) {
        this.resumeOptions = resumeOptions;
        return this;
      }

      /**
       * Builds the SendOptions.
       *
       * @return the built SendOptions
       */
      public SendOptions build() {
        SendOptions options = new SendOptions();
        options.setModel(model);
        options.setTools(tools);
        options.setMaxTurns(maxTurns);
        options.setResumeOptions(resumeOptions);
        return options;
      }
    }
  }
}
