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

package com.google.genkit;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiFunction;
import java.util.function.Function;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.ai.*;
import com.google.genkit.ai.evaluation.*;
import com.google.genkit.ai.session.*;
import com.google.genkit.core.*;
import com.google.genkit.core.middleware.Middleware;
import com.google.genkit.core.tracing.SpanMetadata;
import com.google.genkit.core.tracing.Tracer;
import com.google.genkit.prompt.DotPrompt;
import com.google.genkit.prompt.ExecutablePrompt;

/**
 * Genkit is the main entry point for the Genkit framework.
 *
 * It provides methods to define and run flows, configure AI models, and
 * interact with the Genkit ecosystem.
 */
public class Genkit {

  private static final Logger logger = LoggerFactory.getLogger(Genkit.class);

  private final Registry registry;
  private final List<Plugin> plugins;
  private final GenkitOptions options;
  private final Map<String, DotPrompt<?>> promptCache;
  private final Map<String, Agent> agentRegistry;
  private ReflectionServer reflectionServer;
  private EvaluationManager evaluationManager;

  /**
   * Creates a new Genkit instance with default options.
   */
  public Genkit() {
    this(GenkitOptions.builder().build());
  }

  /**
   * Creates a new Genkit instance with the given options.
   *
   * @param options
   *            the Genkit options
   */
  public Genkit(GenkitOptions options) {
    this.options = options;
    this.registry = new DefaultRegistry();
    this.plugins = new ArrayList<>();
    this.promptCache = new ConcurrentHashMap<>();
    this.agentRegistry = new ConcurrentHashMap<>();
  }

  /**
   * Creates a new Genkit builder.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Creates a Genkit instance with the given plugins.
   *
   * @param plugins
   *            the plugins to use
   * @return a configured Genkit instance
   */
  public static Genkit create(Plugin... plugins) {
    Builder builder = builder();
    for (Plugin plugin : plugins) {
      builder.plugin(plugin);
    }
    return builder.build();
  }

  /**
   * Initializes plugins.
   */
  public void init() {
    // Register utility actions
    registerUtilityActions();

    for (Plugin plugin : plugins) {
      try {
        List<Action<?, ?, ?>> actions = plugin.init(registry);
        for (Action<?, ?, ?> action : actions) {
          String key = action.getType().keyFromName(action.getName());
          registry.registerAction(key, action);
        }
        logger.info("Initialized plugin: {}", plugin.getName());
      } catch (Exception e) {
        logger.error("Failed to initialize plugin: {}", plugin.getName(), e);
        throw new GenkitException("Failed to initialize plugin: " + plugin.getName(), e);
      }
    }

    // Start reflection server in dev mode
    if (options.isDevMode()) {
      startReflectionServer();
    }
  }

  /**
   * Registers utility actions like /util/generate.
   */
  private void registerUtilityActions() {
    GenerateAction.define(registry);
  }

  /**
   * Defines a flow.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @param name
   *            the flow name
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param handler
   *            the flow handler
   * @return the flow
   */
  public <I, O> Flow<I, O, Void> defineFlow(String name, Class<I> inputClass, Class<O> outputClass,
      BiFunction<ActionContext, I, O> handler) {
    return Flow.define(registry, name, inputClass, outputClass, handler);
  }

  /**
   * Defines a flow with middleware.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @param name
   *            the flow name
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param handler
   *            the flow handler
   * @param middleware
   *            the middleware to apply
   * @return the flow
   */
  public <I, O> Flow<I, O, Void> defineFlow(String name, Class<I> inputClass, Class<O> outputClass,
      BiFunction<ActionContext, I, O> handler, List<Middleware<I, O>> middleware) {
    return Flow.define(registry, name, inputClass, outputClass, handler, middleware);
  }

  /**
   * Defines a flow with a simple handler.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @param name
   *            the flow name
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param handler
   *            the flow handler
   * @return the flow
   */
  public <I, O> Flow<I, O, Void> defineFlow(String name, Class<I> inputClass, Class<O> outputClass,
      Function<I, O> handler) {
    return Flow.define(registry, name, inputClass, outputClass, (ctx, input) -> handler.apply(input));
  }

  /**
   * Defines a flow with a simple handler and middleware.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @param name
   *            the flow name
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param handler
   *            the flow handler
   * @param middleware
   *            the middleware to apply
   * @return the flow
   */
  public <I, O> Flow<I, O, Void> defineFlow(String name, Class<I> inputClass, Class<O> outputClass,
      Function<I, O> handler, List<Middleware<I, O>> middleware) {
    return Flow.define(registry, name, inputClass, outputClass, (ctx, input) -> handler.apply(input), middleware);
  }

  /**
   * Defines a tool.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @param name
   *            the tool name
   * @param description
   *            the tool description
   * @param inputSchema
   *            the input JSON schema
   * @param inputClass
   *            the input class
   * @param handler
   *            the tool handler
   * @return the tool
   */
  public <I, O> Tool<I, O> defineTool(String name, String description, Map<String, Object> inputSchema,
      Class<I> inputClass, BiFunction<ActionContext, I, O> handler) {
    Tool<I, O> tool = Tool.<I, O>builder().name(name).description(description).inputSchema(inputSchema)
        .inputClass(inputClass).handler(handler).build();
    tool.register(registry);
    return tool;
  }

  /**
   * Loads a prompt by name from the prompts directory.
   * 
   * <p>
   * This is similar to the JavaScript API: `ai.prompt('hello')`. The prompt is
   * loaded from the configured promptDir (default: /prompts). The prompt is
   * automatically registered as an action and cached for reuse.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * ExecutablePrompt<HelloInput> helloPrompt = genkit.prompt("hello", HelloInput.class);
   * ModelResponse response = helloPrompt.generate(new HelloInput("John"));
   * }</pre>
   *
   * @param <I>
   *            the input type
   * @param name
   *            the prompt name (without .prompt extension)
   * @param inputClass
   *            the input class
   * @return the executable prompt
   * @throws GenkitException
   *             if the prompt cannot be loaded
   */
  @SuppressWarnings("unchecked")
  public <I> ExecutablePrompt<I> prompt(String name, Class<I> inputClass) throws GenkitException {
    return prompt(name, inputClass, null);
  }

  /**
   * Loads a prompt by name with an optional variant.
   *
   * <p>
   * Variants allow different versions of the same prompt to be tested. For
   * example: "recipe" with variant "gemini25pro" loads
   * "recipe.gemini25pro.prompt".
   *
   * @param <I>
   *            the input type
   * @param name
   *            the prompt name (without .prompt extension)
   * @param inputClass
   *            the input class
   * @param variant
   *            optional variant name (e.g., "gemini25pro")
   * @return the executable prompt
   * @throws GenkitException
   *             if the prompt cannot be loaded
   */
  @SuppressWarnings("unchecked")
  public <I> ExecutablePrompt<I> prompt(String name, Class<I> inputClass, String variant) throws GenkitException {
    // Build the cache key
    String cacheKey = variant != null ? name + "." + variant : name;

    // Check cache first
    DotPrompt<I> dotPrompt = (DotPrompt<I>) promptCache.get(cacheKey);

    if (dotPrompt == null) {
      // Build the resource path
      String promptDir = options.getPromptDir();
      String fileName = variant != null ? name + "." + variant + ".prompt" : name + ".prompt";
      String resourcePath = promptDir + "/" + fileName;

      // Load the prompt
      dotPrompt = DotPrompt.loadFromResource(resourcePath);
      promptCache.put(cacheKey, dotPrompt);

      // Auto-register as action
      dotPrompt.register(registry, inputClass);
      String registeredKey = ActionType.EXECUTABLE_PROMPT.keyFromName(dotPrompt.getName());
      logger.info("Loaded and registered prompt: {} as {} (variant: {})", name, registeredKey, variant);
    }

    return new ExecutablePrompt<>(dotPrompt, registry, inputClass).withGenerateFunction(this::generate);
  }

  /**
   * Loads a prompt by name using a Map as input type.
   * 
   * <p>
   * This is a convenience method when you don't want to define a specific input
   * class.
   *
   * @param name
   *            the prompt name (without .prompt extension)
   * @return the executable prompt with Map input
   * @throws GenkitException
   *             if the prompt cannot be loaded
   */
  @SuppressWarnings("unchecked")
  public ExecutablePrompt<Map<String, Object>> prompt(String name) throws GenkitException {
    return prompt(name, (Class<Map<String, Object>>) (Class<?>) Map.class, null);
  }

  /**
   * Defines a prompt.
   *
   * @param <I>
   *            the input type
   * @param name
   *            the prompt name
   * @param template
   *            the prompt template
   * @param inputClass
   *            the input class
   * @param renderer
   *            the prompt renderer
   * @return the prompt
   */
  public <I> Prompt<I> definePrompt(String name, String template, Class<I> inputClass,
      BiFunction<ActionContext, I, ModelRequest> renderer) {
    Prompt<I> prompt = Prompt.<I>builder().name(name).template(template).inputClass(inputClass).renderer(renderer)
        .build();
    prompt.register(registry);
    return prompt;
  }

  /**
   * Registers a model.
   *
   * @param model
   *            the model to register
   */
  public void registerModel(Model model) {
    model.register(registry);
  }

  /**
   * Registers an embedder.
   *
   * @param embedder
   *            the embedder to register
   */
  public void registerEmbedder(Embedder embedder) {
    embedder.register(registry);
  }

  /**
   * Registers a retriever.
   *
   * @param retriever
   *            the retriever to register
   */
  public void registerRetriever(Retriever retriever) {
    retriever.register(registry);
  }

  /**
   * Registers an indexer.
   *
   * @param indexer
   *            the indexer to register
   */
  public void registerIndexer(Indexer indexer) {
    indexer.register(registry);
  }

  /**
   * Defines and registers a retriever.
   * 
   * <p>
   * This is the preferred way to create retrievers as it automatically registers
   * them with the Genkit registry.
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * Retriever myRetriever = genkit.defineRetriever("myStore/docs", (ctx, request) -> {
   * 	// Find similar documents
   * 	List<Document> docs = findSimilarDocs(request.getQuery());
   * 	return new RetrieverResponse(docs);
   * });
   * }</pre>
   *
   * @param name
   *            the retriever name
   * @param handler
   *            the retrieval function
   * @return the registered retriever
   */
  public Retriever defineRetriever(String name,
      BiFunction<ActionContext, RetrieverRequest, RetrieverResponse> handler) {
    Retriever retriever = Retriever.builder().name(name).handler(handler).build();
    retriever.register(registry);
    return retriever;
  }

  /**
   * Defines and registers an indexer.
   * 
   * <p>
   * This is the preferred way to create indexers as it automatically registers
   * them with the Genkit registry.
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * Indexer myIndexer = genkit.defineIndexer("myStore/docs", (ctx, request) -> {
   * 	// Index the documents
   * 	indexDocuments(request.getDocuments());
   * 	return new IndexerResponse();
   * });
   * }</pre>
   *
   * @param name
   *            the indexer name
   * @param handler
   *            the indexing function
   * @return the registered indexer
   */
  public Indexer defineIndexer(String name, BiFunction<ActionContext, IndexerRequest, IndexerResponse> handler) {
    Indexer indexer = Indexer.builder().name(name).handler(handler).build();
    indexer.register(registry);
    return indexer;
  }

  /**
   * Gets a model by name.
   *
   * @param name
   *            the model name
   * @return the model
   */
  public Model getModel(String name) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.MODEL, name);
    if (action == null) {
      throw new GenkitException("Model not found: " + name);
    }
    return (Model) action;
  }

  /**
   * Gets an embedder by name.
   *
   * @param name
   *            the embedder name
   * @return the embedder
   */
  public Embedder getEmbedder(String name) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.EMBEDDER, name);
    if (action == null) {
      throw new GenkitException("Embedder not found: " + name);
    }
    return (Embedder) action;
  }

  /**
   * Gets a retriever by name.
   *
   * @param name
   *            the retriever name
   * @return the retriever
   */
  public Retriever getRetriever(String name) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.RETRIEVER, name);
    if (action == null) {
      throw new GenkitException("Retriever not found: " + name);
    }
    return (Retriever) action;
  }

  /**
   * Generates a model response using the specified options.
   * 
   * <p>
   * This method handles tool execution automatically. If the model requests tool
   * calls, this method will execute the tools, add the results to the
   * conversation, and continue generation until the model produces a final
   * response.
   * 
   * <p>
   * When a tool throws a {@link ToolInterruptException}, the generation is halted
   * and the response is returned with {@link FinishReason#INTERRUPTED}. The
   * caller can then use {@link ResumeOptions} to continue generation after
   * handling the interrupt.
   * 
   * <p>
   * Example with interrupts:
   * 
   * <pre>{@code
   * // First generation - may be interrupted
   * ModelResponse response = genkit.generate(GenerateOptions.builder().model("googleai/gemini-pro")
   * 		.prompt("Transfer $100 to account 12345").tools(List.of(confirmTransfer)).build());
   *
   * // Check if interrupted
   * if (response.isInterrupted()) {
   * 	Part interrupt = response.getInterrupts().get(0);
   * 
   * 	// Get user confirmation
   * 	boolean confirmed = askUserForConfirmation();
   * 
   * 	// Resume with user response
   * 	Part responseData = confirmTransfer.respond(interrupt, new ConfirmOutput(confirmed));
   * 	ModelResponse resumed = genkit.generate(GenerateOptions.builder().model("googleai/gemini-pro")
   * 			.messages(response.getMessages()).tools(List.of(confirmTransfer))
   * 			.resume(ResumeOptions.builder().respond(responseData).build()).build());
   * }
   * }</pre>
   *
   * @param options
   *            the generate options
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(GenerateOptions options) throws GenkitException {
    Model model = getModel(options.getModel());
    ModelRequest request = options.toModelRequest();
    ActionContext ctx = new ActionContext(registry);

    int maxTurns = options.getMaxTurns() != null ? options.getMaxTurns() : 5;
    int turn = 0;

    // Handle resume option if provided
    if (options.getResume() != null) {
      request = handleResumeOption(request, options);
    }

    while (turn < maxTurns) {
      // Create span metadata for the model call
      SpanMetadata modelSpanMetadata = SpanMetadata.builder().name(options.getModel())
          .type(ActionType.MODEL.getValue()).subtype("model").build();

      String flowName = ctx.getFlowName();
      if (flowName != null) {
        modelSpanMetadata.getAttributes().put("genkit:metadata:flow:name", flowName);
      }

      final ModelRequest currentRequest = request;
      ModelResponse response = Tracer.runInNewSpan(ctx, modelSpanMetadata, request, (spanCtx, req) -> {
        return model.run(ctx.withSpanContext(spanCtx), currentRequest);
      });

      // Check if the model requested tool calls
      List<Part> toolRequestParts = extractToolRequestParts(response);
      if (toolRequestParts.isEmpty()) {
        // No tool calls, return the response
        return response;
      }

      // Execute tools and handle interrupts
      ToolExecutionResult toolResult = executeToolsWithInterruptHandling(ctx, toolRequestParts,
          options.getTools());

      // If there are interrupts, return immediately with interrupted response
      if (!toolResult.getInterrupts().isEmpty()) {
        return buildInterruptedResponse(response, toolResult);
      }

      // Add the assistant message with tool requests
      Message assistantMessage = response.getMessage();
      List<Message> updatedMessages = new java.util.ArrayList<>(request.getMessages());
      updatedMessages.add(assistantMessage);

      // Add tool response message
      Message toolResponseMessage = new Message();
      toolResponseMessage.setRole(Role.TOOL);
      toolResponseMessage.setContent(toolResult.getResponses());
      updatedMessages.add(toolResponseMessage);

      // Update request with new messages for next turn
      request = ModelRequest.builder().messages(updatedMessages).config(request.getConfig())
          .tools(request.getTools()).output(request.getOutput()).build();

      turn++;
    }

    throw new GenkitException("Max tool execution turns (" + maxTurns + ") exceeded");
  }

  /**
   * Handles resume options by processing respond and restart directives.
   */
  private ModelRequest handleResumeOption(ModelRequest request, GenerateOptions options) {
    ResumeOptions resume = options.getResume();
    List<Message> messages = new java.util.ArrayList<>(request.getMessages());

    if (messages.isEmpty()) {
      throw new GenkitException("Cannot resume generation with no messages");
    }

    Message lastMessage = messages.get(messages.size() - 1);
    if (lastMessage.getRole() != Role.MODEL) {
      throw new GenkitException("Cannot resume unless the last message is from the model");
    }

    // Build tool response parts from resume options
    List<Part> toolResponseParts = new java.util.ArrayList<>();

    // Handle respond directives
    if (resume.getRespond() != null) {
      for (ToolResponse toolResponse : resume.getRespond()) {
        Part responsePart = new Part();
        responsePart.setToolResponse(toolResponse);
        Map<String, Object> metadata = new java.util.HashMap<>();
        metadata.put("interruptResponse", true);
        responsePart.setMetadata(metadata);
        toolResponseParts.add(responsePart);
      }
    }

    // Handle restart directives - execute the tools
    if (resume.getRestart() != null) {
      ActionContext ctx = new ActionContext(registry);
      for (ToolRequest restartRequest : resume.getRestart()) {
        Tool<?, ?> tool = findTool(restartRequest.getName(), options.getTools());
        if (tool == null) {
          throw new GenkitException("Tool not found for restart: " + restartRequest.getName());
        }

        try {
          @SuppressWarnings("unchecked")
          Tool<Object, Object> typedTool = (Tool<Object, Object>) tool;
          Object result = typedTool.run(ctx, restartRequest.getInput());

          Part responsePart = new Part();
          ToolResponse toolResponse = new ToolResponse(restartRequest.getRef(), restartRequest.getName(),
              result);
          responsePart.setToolResponse(toolResponse);
          Map<String, Object> metadata = new java.util.HashMap<>();
          metadata.put("source", "restart");
          responsePart.setMetadata(metadata);
          toolResponseParts.add(responsePart);
        } catch (ToolInterruptException e) {
          // Tool interrupted again during restart
          throw new GenkitException(
              "Tool '" + restartRequest.getName() + "' triggered an interrupt during restart. "
                  + "Re-interrupting during restart is not supported.");
        }
      }
    }

    if (toolResponseParts.isEmpty()) {
      throw new GenkitException("Resume options must contain either respond or restart directives");
    }

    // Add tool response message
    Message toolResponseMessage = new Message();
    toolResponseMessage.setRole(Role.TOOL);
    toolResponseMessage.setContent(toolResponseParts);
    Map<String, Object> toolMsgMetadata = new java.util.HashMap<>();
    toolMsgMetadata.put("resumed", true);
    toolResponseMessage.setMetadata(toolMsgMetadata);
    messages.add(toolResponseMessage);

    return ModelRequest.builder().messages(messages).config(request.getConfig()).tools(request.getTools())
        .output(request.getOutput()).build();
  }

  /**
   * Builds an interrupted response from the model response and tool execution
   * result.
   */
  private ModelResponse buildInterruptedResponse(ModelResponse response, ToolExecutionResult toolResult) {
    // Update the model message content with interrupt metadata
    Message originalMessage = response.getMessage();
    List<Part> updatedContent = new java.util.ArrayList<>();

    for (Part part : originalMessage.getContent()) {
      if (part.getToolRequest() != null) {
        ToolRequest toolRequest = part.getToolRequest();
        String key = toolRequest.getName() + "#" + (toolRequest.getRef() != null ? toolRequest.getRef() : "");

        // Check if this tool request was interrupted
        Part interruptPart = toolResult.getInterruptMap().get(key);
        if (interruptPart != null) {
          updatedContent.add(interruptPart);
        } else {
          // Check for pending output
          Object pendingOutput = toolResult.getPendingOutputMap().get(key);
          if (pendingOutput != null) {
            Part pendingPart = new Part();
            pendingPart.setToolRequest(toolRequest);
            Map<String, Object> metadata = part.getMetadata() != null
                ? new java.util.HashMap<>(part.getMetadata())
                : new java.util.HashMap<>();
            metadata.put("pendingOutput", pendingOutput);
            pendingPart.setMetadata(metadata);
            updatedContent.add(pendingPart);
          } else {
            updatedContent.add(part);
          }
        }
      } else {
        updatedContent.add(part);
      }
    }

    Message updatedMessage = new Message();
    updatedMessage.setRole(originalMessage.getRole());
    updatedMessage.setContent(updatedContent);
    updatedMessage.setMetadata(originalMessage.getMetadata());

    // Create candidate with updated message
    Candidate updatedCandidate = new Candidate();
    updatedCandidate.setMessage(updatedMessage);
    updatedCandidate.setFinishReason(FinishReason.INTERRUPTED);

    return ModelResponse.builder().candidates(List.of(updatedCandidate)).usage(response.getUsage())
        .request(response.getRequest()).custom(response.getCustom()).latencyMs(response.getLatencyMs())
        .finishReason(FinishReason.INTERRUPTED).finishMessage("One or more tool calls resulted in interrupts.")
        .interrupts(toolResult.getInterrupts()).build();
  }

  /**
   * Extracts tool request parts from a model response.
   */
  private List<Part> extractToolRequestParts(ModelResponse response) {
    List<Part> parts = new java.util.ArrayList<>();
    if (response.getCandidates() != null) {
      for (Candidate candidate : response.getCandidates()) {
        if (candidate.getMessage() != null && candidate.getMessage().getContent() != null) {
          for (Part part : candidate.getMessage().getContent()) {
            if (part.getToolRequest() != null) {
              parts.add(part);
            }
          }
        }
      }
    }
    return parts;
  }

  /**
   * Extracts tool requests from a model response.
   */
  private List<ToolRequest> extractToolRequests(ModelResponse response) {
    List<ToolRequest> requests = new java.util.ArrayList<>();
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
   * Result of tool execution with interrupt handling.
   */
  private static class ToolExecutionResult {
    private final List<Part> responses;
    private final List<Part> interrupts;
    private final Map<String, Part> interruptMap;
    private final Map<String, Object> pendingOutputMap;

    ToolExecutionResult(List<Part> responses, List<Part> interrupts, Map<String, Part> interruptMap,
        Map<String, Object> pendingOutputMap) {
      this.responses = responses;
      this.interrupts = interrupts;
      this.interruptMap = interruptMap;
      this.pendingOutputMap = pendingOutputMap;
    }

    List<Part> getResponses() {
      return responses;
    }
    List<Part> getInterrupts() {
      return interrupts;
    }
    Map<String, Part> getInterruptMap() {
      return interruptMap;
    }
    Map<String, Object> getPendingOutputMap() {
      return pendingOutputMap;
    }
  }

  /**
   * Executes tools with interrupt handling.
   */
  private ToolExecutionResult executeToolsWithInterruptHandling(ActionContext ctx, List<Part> toolRequestParts,
      List<Tool<?, ?>> tools) {

    List<Part> responseParts = new java.util.ArrayList<>();
    List<Part> interrupts = new java.util.ArrayList<>();
    Map<String, Part> interruptMap = new java.util.HashMap<>();
    Map<String, Object> pendingOutputMap = new java.util.HashMap<>();

    for (Part toolRequestPart : toolRequestParts) {
      ToolRequest toolRequest = toolRequestPart.getToolRequest();
      String toolName = toolRequest.getName();
      String key = toolName + "#" + (toolRequest.getRef() != null ? toolRequest.getRef() : "");

      // Find the tool
      Tool<?, ?> tool = findTool(toolName, tools);
      if (tool == null) {
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Map.of("error", "Tool not found: " + toolName));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
        continue;
      }

      // Check if this is an interrupt tool (has "interrupt" metadata marker)
      boolean isInterruptTool = tool.getMetadata() != null
          && Boolean.TRUE.equals(tool.getMetadata().get("interrupt"));

      try {
        // Convert input to the expected type
        Object toolInput = toolRequest.getInput();
        Class<?> inputClass = tool.getInputClass();
        if (inputClass != null && toolInput != null && !inputClass.isInstance(toolInput)) {
          toolInput = JsonUtils.convert(toolInput, inputClass);
        }

        // Execute the tool
        @SuppressWarnings("unchecked")
        Tool<Object, Object> typedTool = (Tool<Object, Object>) tool;
        Object result = typedTool.run(ctx, toolInput);

        // Create tool response part
        Part responsePart = new Part();
        ToolResponse toolResponse = new ToolResponse(toolRequest.getRef(), toolName, result);
        responsePart.setToolResponse(toolResponse);
        responseParts.add(responsePart);

        // Store pending output in case other tools interrupt
        pendingOutputMap.put(key, result);

        logger.debug("Executed tool '{}' successfully", toolName);

      } catch (ToolInterruptException e) {
        // Tool interrupted - store the interrupt
        Map<String, Object> interruptMetadata = e.getMetadata();

        Part interruptPart = new Part();
        interruptPart.setToolRequest(toolRequest);
        Map<String, Object> metadata = toolRequestPart.getMetadata() != null
            ? new java.util.HashMap<>(toolRequestPart.getMetadata())
            : new java.util.HashMap<>();
        metadata.put("interrupt",
            interruptMetadata != null && !interruptMetadata.isEmpty() ? interruptMetadata : true);
        interruptPart.setMetadata(metadata);

        interrupts.add(interruptPart);
        interruptMap.put(key, interruptPart);

        logger.debug("Tool '{}' triggered interrupt", toolName);

      } catch (Exception e) {
        logger.error("Tool execution failed for '{}': {}", toolName, e.getMessage());
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Map.of("error", "Tool execution failed: " + e.getMessage()));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
      }
    }

    return new ToolExecutionResult(responseParts, interrupts, interruptMap, pendingOutputMap);
  }

  /**
   * Executes tools and returns the response parts.
   */
  private List<Part> executeTools(ActionContext ctx, List<ToolRequest> toolRequests, List<Tool<?, ?>> tools) {
    List<Part> responseParts = new java.util.ArrayList<>();

    for (ToolRequest toolRequest : toolRequests) {
      String toolName = toolRequest.getName();
      Object toolInput = toolRequest.getInput();

      // Find the tool
      Tool<?, ?> tool = findTool(toolName, tools);
      if (tool == null) {
        // Tool not found, create an error response
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Map.of("error", "Tool not found: " + toolName));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
        continue;
      }

      try {
        // Execute the tool
        @SuppressWarnings("unchecked")
        Tool<Object, Object> typedTool = (Tool<Object, Object>) tool;
        Object result = typedTool.run(ctx, toolInput);

        // Create tool response part
        Part responsePart = new Part();
        ToolResponse toolResponse = new ToolResponse(toolRequest.getRef(), toolName, result);
        responsePart.setToolResponse(toolResponse);
        responseParts.add(responsePart);

        logger.debug("Executed tool '{}' successfully", toolName);
      } catch (Exception e) {
        logger.error("Tool execution failed for '{}': {}", toolName, e.getMessage());
        Part errorPart = new Part();
        ToolResponse errorResponse = new ToolResponse(toolRequest.getRef(), toolName,
            Map.of("error", "Tool execution failed: " + e.getMessage()));
        errorPart.setToolResponse(errorResponse);
        responseParts.add(errorPart);
      }
    }

    return responseParts;
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

    // Also try to find in registry
    Action<?, ?, ?> action = registry.lookupAction(ActionType.TOOL, toolName);
    if (action instanceof Tool) {
      return (Tool<?, ?>) action;
    }

    return null;
  }

  /**
   * Generates a streaming model response using the specified options.
   * 
   * <p>
   * This method invokes the model with streaming enabled, calling the provided
   * callback for each chunk of the response as it arrives. This is useful for
   * displaying responses incrementally to users.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * StringBuilder result = new StringBuilder();
   * ModelResponse response = genkit.generateStream(
   * 		GenerateOptions.builder().model("openai/gpt-4o").prompt("Tell me a story").build(), chunk -> {
   * 			System.out.print(chunk.getText());
   * 			result.append(chunk.getText());
   * 		});
   * }</pre>
   *
   * @param options
   *            the generate options
   * @param streamCallback
   *            callback invoked for each response chunk
   * @return the final aggregated model response
   * @throws GenkitException
   *             if generation fails or model doesn't support streaming
   */
  public ModelResponse generateStream(GenerateOptions options,
      java.util.function.Consumer<ModelResponseChunk> streamCallback) throws GenkitException {
    Model model = getModel(options.getModel());
    if (!model.supportsStreaming()) {
      throw new GenkitException("Model " + options.getModel() + " does not support streaming");
    }
    ModelRequest request = options.toModelRequest();
    ActionContext ctx = new ActionContext(registry);

    int maxTurns = options.getMaxTurns() != null ? options.getMaxTurns() : 5;
    int turn = 0;

    while (turn < maxTurns) {
      // Create span metadata for the model call
      SpanMetadata modelSpanMetadata = SpanMetadata.builder().name(options.getModel())
          .type(ActionType.MODEL.getValue()).subtype("model").build();

      String flowName = ctx.getFlowName();
      if (flowName != null) {
        modelSpanMetadata.getAttributes().put("genkit:metadata:flow:name", flowName);
      }

      final ModelRequest currentRequest = request;
      ModelResponse response = Tracer.runInNewSpan(ctx, modelSpanMetadata, request, (spanCtx, req) -> {
        return model.run(ctx.withSpanContext(spanCtx), currentRequest, streamCallback);
      });

      // Check if the model requested tool calls
      List<ToolRequest> toolRequests = extractToolRequests(response);
      if (toolRequests.isEmpty()) {
        // No tool calls, return the response
        return response;
      }

      // Execute tools and build tool response messages
      List<Part> toolResponseParts = executeTools(ctx, toolRequests, options.getTools());

      // Add the assistant message with tool requests
      Message assistantMessage = response.getMessage();
      List<Message> updatedMessages = new java.util.ArrayList<>(request.getMessages());
      updatedMessages.add(assistantMessage);

      // Add tool response message
      Message toolResponseMessage = new Message();
      toolResponseMessage.setRole(Role.TOOL);
      toolResponseMessage.setContent(toolResponseParts);
      updatedMessages.add(toolResponseMessage);

      // Update request with new messages for next turn
      request = ModelRequest.builder().messages(updatedMessages).config(request.getConfig())
          .tools(request.getTools()).output(request.getOutput()).build();

      turn++;
    }

    throw new GenkitException("Max tool execution turns (" + maxTurns + ") exceeded");
  }

  /**
   * Generates a model response with a simple prompt.
   *
   * @param modelName
   *            the model name
   * @param prompt
   *            the prompt text
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(String modelName, String prompt) throws GenkitException {
    return generate(GenerateOptions.builder().model(modelName).prompt(prompt).build());
  }

  /**
   * Embeds documents using the specified embedder.
   *
   * @param embedderName
   *            the embedder name
   * @param documents
   *            the documents to embed
   * @return the embed response
   * @throws GenkitException
   *             if embedding fails
   */
  public EmbedResponse embed(String embedderName, List<Document> documents) throws GenkitException {
    Embedder embedder = getEmbedder(embedderName);
    EmbedRequest request = new EmbedRequest(documents);
    ActionContext ctx = new ActionContext(registry);
    return embedder.run(ctx, request);
  }

  /**
   * Retrieves documents using the specified retriever.
   * 
   * <p>
   * This is the primary method for retrieval in RAG workflows. The returned
   * documents can be passed directly to {@code generate()} via the
   * {@code .docs()} option.
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * // Retrieve relevant documents
   * List<Document> docs = genkit.retrieve("myStore/docs", "What is the capital of France?");
   * 
   * // Use documents in generation
   * ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
   * 		.prompt("Answer the question based on context").docs(docs).build());
   * }</pre>
   *
   * @param retrieverName
   *            the retriever name
   * @param query
   *            the query text
   * @return the list of retrieved documents
   * @throws GenkitException
   *             if retrieval fails
   */
  public List<Document> retrieve(String retrieverName, String query) throws GenkitException {
    Retriever retriever = getRetriever(retrieverName);
    RetrieverRequest request = RetrieverRequest.fromText(query);
    ActionContext ctx = new ActionContext(registry);
    RetrieverResponse response = retriever.run(ctx, request);
    return response.getDocuments();
  }

  /**
   * Retrieves documents using the specified retriever with options.
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * List<Document> docs = genkit.retrieve("myStore/docs", "query", RetrieverParams.builder().k(5).build());
   * }</pre>
   *
   * @param retrieverName
   *            the retriever name
   * @param query
   *            the query text
   * @param options
   *            retrieval options (e.g., k for number of results)
   * @return the list of retrieved documents
   * @throws GenkitException
   *             if retrieval fails
   */
  public List<Document> retrieve(String retrieverName, String query, RetrieverRequest.RetrieverOptions options)
      throws GenkitException {
    Retriever retriever = getRetriever(retrieverName);
    RetrieverRequest request = RetrieverRequest.fromText(query);
    request.setOptions(options);
    ActionContext ctx = new ActionContext(registry);
    RetrieverResponse response = retriever.run(ctx, request);
    return response.getDocuments();
  }

  /**
   * Retrieves documents using a Document as the query.
   *
   * @param retrieverName
   *            the retriever name
   * @param query
   *            the query document
   * @return the list of retrieved documents
   * @throws GenkitException
   *             if retrieval fails
   */
  public List<Document> retrieve(String retrieverName, Document query) throws GenkitException {
    Retriever retriever = getRetriever(retrieverName);
    RetrieverRequest request = new RetrieverRequest(query);
    ActionContext ctx = new ActionContext(registry);
    RetrieverResponse response = retriever.run(ctx, request);
    return response.getDocuments();
  }

  /**
   * Indexes documents using the specified indexer.
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * List<Document> docs = List.of(Document.fromText("Paris is the capital of France."),
   * 		Document.fromText("Berlin is the capital of Germany."));
   * genkit.index("myStore/docs", docs);
   * }</pre>
   *
   * @param indexerName
   *            the indexer name
   * @param documents
   *            the documents to index
   * @throws GenkitException
   *             if indexing fails
   */
  public void index(String indexerName, List<Document> documents) throws GenkitException {
    Indexer indexer = getIndexer(indexerName);
    IndexerRequest request = new IndexerRequest(documents);
    ActionContext ctx = new ActionContext(registry);
    indexer.run(ctx, request);
  }

  /**
   * Gets an indexer by name.
   *
   * @param name
   *            the indexer name
   * @return the indexer
   */
  public Indexer getIndexer(String name) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.INDEXER, name);
    if (action == null) {
      throw new GenkitException("Indexer not found: " + name);
    }
    return (Indexer) action;
  }

  /**
   * Runs a flow by name.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @param flowName
   *            the flow name
   * @param input
   *            the flow input
   * @return the flow output
   * @throws GenkitException
   *             if execution fails
   */
  @SuppressWarnings("unchecked")
  public <I, O> O runFlow(String flowName, I input) throws GenkitException {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.FLOW, flowName);
    if (action == null) {
      throw new GenkitException("Flow not found: " + flowName);
    }
    Flow<I, O, ?> flow = (Flow<I, O, ?>) action;
    ActionContext ctx = new ActionContext(registry);
    return flow.run(ctx, input);
  }

  /**
   * Gets the registry.
   *
   * @return the registry
   */
  public Registry getRegistry() {
    return registry;
  }

  /**
   * Gets the options.
   *
   * @return the options
   */
  public GenkitOptions getOptions() {
    return options;
  }

  /**
   * Gets the registered plugins.
   *
   * @return the plugins
   */
  public List<Plugin> getPlugins() {
    return plugins;
  }

  /**
   * Starts the reflection server for dev tools integration.
   */
  private void startReflectionServer() {
    try {
      int port = options.getReflectionPort();
      reflectionServer = new ReflectionServer(registry, port);
      reflectionServer.start();
      logger.info("Reflection server started on port {}", port);

      // Write runtime file with matching runtime ID
      RuntimeFileWriter.write(port, reflectionServer.getRuntimeId());
    } catch (Exception e) {
      logger.error("Failed to start reflection server", e);
      throw new GenkitException("Failed to start reflection server", e);
    }
  }

  /**
   * Stops the Genkit instance and cleans up resources.
   */
  public void stop() {
    if (reflectionServer != null) {
      try {
        reflectionServer.stop();
        RuntimeFileWriter.cleanup();
      } catch (Exception e) {
        logger.warn("Error stopping reflection server", e);
      }
    }
  }

  // =========================================================================
  // Session Methods
  // =========================================================================

  /**
   * Creates a new session with default options.
   *
   * <p>
   * Sessions provide stateful multi-turn conversations with automatic history
   * persistence. Each session can have multiple named conversation threads.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * Session<Void> session = genkit.createSession();
   * Chat<Void> chat = session
   * 		.chat(ChatOptions.<Void>builder().model("openai/gpt-4o").system("You are a helpful assistant.").build());
   * chat.send("Hello!");
   * }</pre>
   *
   * @param <S>
   *            the session state type
   * @return a new session
   */
  public <S> Session<S> createSession() {
    return Session.create(registry, SessionOptions.<S>builder().build(), agentRegistry);
  }

  /**
   * Creates a new session with the given options.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * // With custom state
   * Session<MyState> session = genkit
   * 		.createSession(SessionOptions.<MyState>builder().initialState(new MyState("John")).build());
   *
   * // With custom store and session ID
   * Session<MyState> session = genkit.createSession(SessionOptions.<MyState>builder()
   * 		.store(new RedisSessionStore<>()).sessionId("my-session-123").initialState(new MyState()).build());
   * }</pre>
   *
   * @param <S>
   *            the session state type
   * @param options
   *            the session options
   * @return a new session
   */
  public <S> Session<S> createSession(SessionOptions<S> options) {
    return Session.create(registry, options, agentRegistry);
  }

  /**
   * Loads an existing session from a store.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * CompletableFuture<Session<MyState>> sessionFuture = genkit.loadSession("session-123",
   * 		SessionOptions.<MyState>builder().store(mySessionStore).build());
   * Session<MyState> session = sessionFuture.get();
   * if (session != null) {
   * 	Chat<MyState> chat = session.chat();
   * 	// Continue conversation...
   * }
   * }</pre>
   *
   * @param <S>
   *            the session state type
   * @param sessionId
   *            the session ID to load
   * @param options
   *            the session options (must include store)
   * @return a CompletableFuture containing the session, or null if not found
   */
  public <S> CompletableFuture<Session<S>> loadSession(String sessionId, SessionOptions<S> options) {
    return Session.load(registry, sessionId, options, agentRegistry);
  }

  /**
   * Creates a simple chat without session persistence.
   *
   * <p>
   * This is a convenience method for quick interactions without full session
   * management. Use {@link #createSession()} for persistent multi-turn
   * conversations.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * Chat<Void> chat = genkit
   * 		.chat(ChatOptions.<Void>builder().model("openai/gpt-4o").system("You are a helpful assistant.").build());
   * ModelResponse response = chat.send("Hello!");
   * }</pre>
   *
   * @param <S>
   *            the state type (usually Void for simple chats)
   * @param options
   *            the chat options
   * @return a new chat instance
   */
  public <S> Chat<S> chat(ChatOptions<S> options) {
    Session<S> session = createSession();
    return session.chat(options);
  }

  // =========================================================================
  // Agent and Interrupt Methods
  // =========================================================================

  /**
   * Defines an agent that can be used as a tool in multi-agent systems.
   *
   * <p>
   * Agents are specialized conversational components that can be delegated to by
   * other agents. When an agent is called as a tool, it takes over the
   * conversation with its own system prompt, model, and tools.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * // Define a specialized agent
   * Agent reservationAgent = genkit.defineAgent(AgentConfig.builder().name("reservationAgent")
   * 		.description("Handles restaurant reservations").system("You are a reservation specialist...")
   * 		.model("openai/gpt-4o").tools(List.of(reservationTool, lookupTool)).build());
   *
   * // Use in a parent agent
   * Agent triageAgent = genkit.defineAgent(
   * 		AgentConfig.builder().name("triageAgent").description("Routes customer requests to specialists")
   * 				.system("You route customer requests to the appropriate specialist")
   * 				.agents(List.of(reservationAgent.getConfig())).build());
   *
   * // Start chat with triage agent
   * Chat chat = genkit.chat(ChatOptions.builder().model("openai/gpt-4o").system(triageAgent.getSystem())
   * 		.tools(triageAgent.getAllTools(agentRegistry)).build());
   * }</pre>
   *
   * @param config
   *            the agent configuration
   * @return the created agent
   */
  public Agent defineAgent(AgentConfig config) {
    Agent agent = new Agent(config);
    // Register the agent as a tool
    registry.registerAction(ActionType.TOOL, agent.asTool());
    // Register in agent registry for getAllTools lookup
    agentRegistry.put(config.getName(), agent);
    return agent;
  }

  /**
   * Gets an agent by name.
   *
   * @param name
   *            the agent name
   * @return the agent, or null if not found
   */
  public Agent getAgent(String name) {
    return agentRegistry.get(name);
  }

  /**
   * Gets the agent registry.
   *
   * <p>
   * This returns an unmodifiable view of all registered agents.
   *
   * @return the agent registry
   */
  public Map<String, Agent> getAgentRegistry() {
    return java.util.Collections.unmodifiableMap(agentRegistry);
  }

  /**
   * Gets all tools for an agent, including sub-agent tools.
   *
   * <p>
   * This is a convenience method that collects all tools from an agent, including
   * tools from any sub-agents defined in its configuration.
   *
   * @param agent
   *            the agent
   * @return the list of all tools
   */
  public List<Tool<?, ?>> getAllToolsForAgent(Agent agent) {
    return agent.getAllTools(agentRegistry);
  }

  /**
   * Defines an interrupt tool for human-in-the-loop interactions.
   *
   * <p>
   * Interrupts allow tools to pause generation and request user input. When a
   * tool throws a {@link ToolInterruptException}, the chat returns early with the
   * interrupt information, allowing the application to collect user input and
   * resume.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * // Define an interrupt for confirming actions
   * Tool<ConfirmInput, ConfirmOutput> confirmInterrupt = genkit.defineInterrupt(InterruptConfig
   * 		.<ConfirmInput, ConfirmOutput>builder().name("confirm").description("Asks user to confirm an action")
   * 		.inputType(ConfirmInput.class).outputType(ConfirmOutput.class).build());
   *
   * // Use in a chat with tools
   * Chat chat = genkit.chat(
   * 		ChatOptions.builder().model("openai/gpt-4o").tools(List.of(someActionTool, confirmInterrupt)).build());
   *
   * ModelResponse response = chat.send("Book a table for 4");
   *
   * // Check for interrupts
   * if (chat.hasPendingInterrupts()) {
   * 	List<InterruptRequest> interrupts = chat.getPendingInterrupts();
   * 	// Show UI to user, collect response
   * 	ConfirmOutput userResponse = getUserConfirmation(interrupts.get(0));
   * 
   * 	// Resume with user response
   * 	response = chat.send("",
   * 			SendOptions.builder().resumeOptions(
   * 					ResumeOptions.builder().respond(List.of(interrupts.get(0).respond(userResponse))).build())
   * 					.build());
   * }
   * }</pre>
   *
   * @param <I>
   *            the interrupt input type
   * @param <O>
   *            the interrupt output type (user response)
   * @param config
   *            the interrupt configuration
   * @return the interrupt as a tool
   */
  public <I, O> Tool<I, O> defineInterrupt(InterruptConfig<I, O> config) {
    Map<String, Object> inputSchema = config.getInputSchema();
    if (inputSchema == null) {
      inputSchema = new java.util.HashMap<>();
      inputSchema.put("type", "object");
    }

    Map<String, Object> outputSchema = config.getOutputSchema();
    if (outputSchema == null) {
      outputSchema = new java.util.HashMap<>();
      outputSchema.put("type", "object");
    }

    Tool<I, O> interruptTool = new Tool<>(config.getName(),
        config.getDescription() != null ? config.getDescription() : "Interrupt: " + config.getName(),
        inputSchema, outputSchema, config.getInputType(), (ctx, input) -> {
          // Build metadata from input - create a mutable copy since user may return
          // immutable map
          Map<String, Object> metadata = new java.util.HashMap<>();
          if (config.getRequestMetadata() != null) {
            metadata.putAll(config.getRequestMetadata().apply(input));
          }
          metadata.put("interrupt", true);
          metadata.put("interruptName", config.getName());
          metadata.put("input", input);

          // Throw interrupt exception - this never returns
          throw new ToolInterruptException(metadata);
        });

    // Register the interrupt tool
    registry.registerAction(ActionType.TOOL, interruptTool);
    return interruptTool;
  }

  /**
   * Gets the current session from the context.
   *
   * <p>
   * This method can be called from within tool execution to access the current
   * session state. It uses a thread-local context that is set during chat
   * execution.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * Tool<Input, Output> myTool = genkit.defineTool("myTool", Input.class, Output.class, (ctx, input) -> {
   * 	Session<?> session = genkit.currentSession();
   * 	if (session != null) {
   * 		Object state = session.getState();
   * 		// Use session state...
   * 	}
   * 	return new Output();
   * });
   * }</pre>
   *
   * @param <S>
   *            the session state type
   * @return the current session, or null if not in a session context
   */
  @SuppressWarnings("unchecked")
  public <S> Session<S> currentSession() {
    return (Session<S>) SessionContext.currentSession();
  }

  // =========================================================================
  // Evaluation Methods
  // =========================================================================

  /**
   * Defines a new evaluator and registers it with the registry.
   * 
   * <p>
   * Evaluators assess the quality of AI outputs. They can be used to:
   * <ul>
   * <li>Score outputs based on various criteria (accuracy, relevance, etc.)</li>
   * <li>Compare outputs against reference data</li>
   * <li>Run automated quality checks in CI/CD pipelines</li>
   * </ul>
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * genkit.defineEvaluator("myEvaluator", "My Evaluator", "Checks output quality", (dataPoint, options) -> {
   * 	// Evaluate the output
   * 	double score = calculateScore(dataPoint.getOutput());
   * 	return EvalResponse.builder().testCaseId(dataPoint.getTestCaseId())
   * 			.evaluation(Score.builder().score(score).build()).build();
   * });
   * }</pre>
   *
   * @param <O>
   *            the options type
   * @param name
   *            the evaluator name
   * @param displayName
   *            the display name shown in the UI
   * @param definition
   *            description of what the evaluator measures
   * @param evaluatorFn
   *            the evaluation function
   * @return the created evaluator
   */
  public <O> Evaluator<O> defineEvaluator(String name, String displayName, String definition,
      EvaluatorFn<O> evaluatorFn) {
    return Evaluator.define(registry, name, displayName, definition, evaluatorFn);
  }

  /**
   * Defines a new evaluator with full options.
   *
   * @param <O>
   *            the options type
   * @param name
   *            the evaluator name
   * @param displayName
   *            the display name shown in the UI
   * @param definition
   *            description of what the evaluator measures
   * @param isBilled
   *            whether using this evaluator incurs costs
   * @param optionsClass
   *            the class for evaluator-specific options
   * @param evaluatorFn
   *            the evaluation function
   * @return the created evaluator
   */
  public <O> Evaluator<O> defineEvaluator(String name, String displayName, String definition, boolean isBilled,
      Class<O> optionsClass, EvaluatorFn<O> evaluatorFn) {
    return Evaluator.define(registry, name, displayName, definition, isBilled, optionsClass, evaluatorFn);
  }

  /**
   * Gets an evaluator by name.
   *
   * @param name
   *            the evaluator name
   * @return the evaluator
   * @throws GenkitException
   *             if evaluator not found
   */
  @SuppressWarnings("unchecked")
  public Evaluator<?> getEvaluator(String name) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.EVALUATOR, name);
    if (action == null) {
      throw new GenkitException("Evaluator not found: " + name);
    }
    return (Evaluator<?>) action;
  }

  /**
   * Runs an evaluation using the specified request.
   * 
   * <p>
   * This method:
   * <ol>
   * <li>Loads the dataset</li>
   * <li>Runs inference on the target action</li>
   * <li>Executes all specified evaluators</li>
   * <li>Stores and returns the results</li>
   * </ol>
   *
   * @param request
   *            the evaluation request
   * @return the evaluation run key
   * @throws Exception
   *             if evaluation fails
   */
  public EvalRunKey evaluate(RunEvaluationRequest request) throws Exception {
    return getEvaluationManager().runEvaluation(request);
  }

  /**
   * Gets the evaluation manager.
   *
   * @return the evaluation manager
   */
  public synchronized EvaluationManager getEvaluationManager() {
    if (evaluationManager == null) {
      evaluationManager = new EvaluationManager(registry);
    }
    return evaluationManager;
  }

  /**
   * Gets the dataset store.
   *
   * @return the dataset store
   */
  public DatasetStore getDatasetStore() {
    return getEvaluationManager().getDatasetStore();
  }

  /**
   * Gets the eval store.
   *
   * @return the eval store
   */
  public EvalStore getEvalStore() {
    return getEvaluationManager().getEvalStore();
  }

  /**
   * Builder for Genkit.
   */
  public static class Builder {
    private final List<Plugin> plugins = new ArrayList<>();
    private GenkitOptions options = GenkitOptions.builder().build();

    /**
     * Sets the Genkit options.
     *
     * @param options
     *            the options
     * @return this builder
     */
    public Builder options(GenkitOptions options) {
      this.options = options;
      return this;
    }

    /**
     * Adds a plugin.
     *
     * @param plugin
     *            the plugin to add
     * @return this builder
     */
    public Builder plugin(Plugin plugin) {
      this.plugins.add(plugin);
      return this;
    }

    /**
     * Enables dev mode.
     *
     * @return this builder
     */
    public Builder devMode() {
      this.options = GenkitOptions.builder().devMode(true).build();
      return this;
    }

    /**
     * Sets the reflection port.
     *
     * @param port
     *            the port number
     * @return this builder
     */
    public Builder reflectionPort(int port) {
      this.options = GenkitOptions.builder().devMode(options.isDevMode()).reflectionPort(port).build();
      return this;
    }

    /**
     * Builds the Genkit instance.
     *
     * @return the configured Genkit instance
     */
    public Genkit build() {
      Genkit genkit = new Genkit(options);
      genkit.plugins.addAll(plugins);
      genkit.init();
      return genkit;
    }
  }
}
