# Genkit for Java

Genkit for Java is the Java implementation of the Genkit framework for building AI-powered applications.

See: https://firebase.google.com/docs/genkit

> **Status**: Currently in active development (1.0.0-SNAPSHOT). Requires Java 17+.

## Installation

Add the following dependencies to your Maven `pom.xml`:

```xml
<!-- Core Genkit framework -->
<dependency>
    <groupId>com.google.genkit</groupId>
    <artifactId>genkit</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</dependency>

<!-- OpenAI plugin (models and embeddings) -->
<dependency>
    <groupId>com.google.genkit</groupId>
    <artifactId>genkit-plugin-openai</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</dependency>

<!-- HTTP server plugin with Jetty -->
<dependency>
    <groupId>com.google.genkit</groupId>
    <artifactId>genkit-plugin-jetty</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</dependency>

<!-- Local vector store plugin (for RAG development) -->
<dependency>
    <groupId>com.google.genkit</groupId>
    <artifactId>genkit-plugin-localvec</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</dependency>
```

## Quick Start

```java
import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.GenerateOptions;
import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.plugins.openai.OpenAIPlugin;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;

public class Main {
    public static void main(String[] args) {
        // Create Genkit with plugins
        Genkit genkit = Genkit.builder()
            .options(GenkitOptions.builder()
                .devMode(true)
                .reflectionPort(3100)
                .build())
            .plugin(OpenAIPlugin.create())
            .plugin(new JettyPlugin(JettyPluginOptions.builder()
                .port(8080)
                .build()))
            .build();

        // Generate text
        ModelResponse response = genkit.generate(
            GenerateOptions.builder()
                .model("openai/gpt-4o-mini")
                .prompt("Tell me a fun fact!")
                .config(GenerationConfig.builder()
                    .temperature(0.9)
                    .maxOutputTokens(200)
                    .build())
                .build());

        System.out.println(response.getText());
    }
}
```

## Defining Flows

Flows are observable, traceable AI workflows that can be exposed as HTTP endpoints:

```java
// Simple flow with typed input/output
Flow<String, String, Void> greetFlow = genkit.defineFlow(
    "greeting",
    String.class,
    String.class,
    name -> "Hello, " + name + "!");

// AI-powered flow with context access
Flow<String, String, Void> jokeFlow = genkit.defineFlow(
    "tellJoke",
    String.class,
    String.class,
    (ctx, topic) -> {
        ModelResponse response = genkit.generate(
            GenerateOptions.builder()
                .model("openai/gpt-4o-mini")
                .prompt("Tell me a short, funny joke about: " + topic)
                .build());
        return response.getText();
    });

// Run a flow programmatically
String result = genkit.runFlow("greeting", "World");
```

## Using Tools

Define tools that models can call during generation:

```java
@SuppressWarnings("unchecked")
Tool<Map<String, Object>, Map<String, Object>> weatherTool = genkit.defineTool(
    "getWeather",
    "Gets the current weather for a location",
    Map.of(
        "type", "object",
        "properties", Map.of(
            "location", Map.of("type", "string", "description", "The city name")
        ),
        "required", new String[]{"location"}
    ),
    (Class<Map<String, Object>>) (Class<?>) Map.class,
    (ctx, input) -> {
        String location = (String) input.get("location");
        return Map.of(
            "location", location,
            "temperature", "72°F",
            "conditions", "sunny"
        );
    });

// Use tool in generation - tool execution is handled automatically
ModelResponse response = genkit.generate(
    GenerateOptions.builder()
        .model("openai/gpt-4o")
        .prompt("What's the weather in Paris?")
        .tools(List.of(weatherTool))
        .build());
```

## DotPrompt Support

Load and use `.prompt` files with Handlebars templating:

```java
// Load a prompt from resources/prompts/recipe.prompt
ExecutablePrompt<RecipeInput> recipePrompt = genkit.prompt("recipe", RecipeInput.class);

// Execute with typed input
ModelResponse response = recipePrompt.generate(new RecipeInput("pasta carbonara"));

// Prompts support variants (e.g., recipe.robot.prompt)
ExecutablePrompt<RecipeInput> robotPrompt = genkit.prompt("recipe", RecipeInput.class, "robot");
```

## RAG (Retrieval Augmented Generation)

Build RAG applications with retrievers and indexers:

```java
// Define a retriever
Retriever myRetriever = genkit.defineRetriever("myStore/docs", (ctx, request) -> {
    List<Document> docs = findSimilarDocs(request.getQuery());
    return new RetrieverResponse(docs);
});

// Define an indexer
Indexer myIndexer = genkit.defineIndexer("myStore/docs", (ctx, request) -> {
    indexDocuments(request.getDocuments());
    return new IndexerResponse();
});

// Index documents
List<Document> docs = List.of(
    Document.fromText("Paris is the capital of France."),
    Document.fromText("Berlin is the capital of Germany.")
);
genkit.index("myStore/docs", docs);

// Retrieve and generate
List<Document> relevantDocs = genkit.retrieve("myStore/docs", "What is the capital of France?");
ModelResponse response = genkit.generate(GenerateOptions.builder()
    .model("openai/gpt-4o-mini")
    .prompt("Answer based on context: What is the capital of France?")
    .docs(relevantDocs)
    .build());
```

## Evaluations

Define custom evaluators to assess AI output quality:

```java
genkit.defineEvaluator("accuracyCheck", "Accuracy Check", "Checks factual accuracy",
    (dataPoint, options) -> {
        double score = calculateAccuracyScore(dataPoint.getOutput());
        return EvalResponse.builder()
            .testCaseId(dataPoint.getTestCaseId())
            .evaluation(Score.builder().score(score).build())
            .build();
    });

// Run evaluation
EvalRunKey result = genkit.evaluate(RunEvaluationRequest.builder()
    .datasetId("my-dataset")
    .evaluators(List.of("accuracyCheck"))
    .actionRef("/flow/myFlow")
    .build());
```

## Streaming

Generate responses with streaming for real-time output:

```java
StringBuilder result = new StringBuilder();
ModelResponse response = genkit.generateStream(
    GenerateOptions.builder()
        .model("openai/gpt-4o")
        .prompt("Tell me a story")
        .build(),
    chunk -> {
        System.out.print(chunk.getText());
        result.append(chunk.getText());
    });
```

## Embeddings

Generate vector embeddings for semantic search:

```java
List<Document> documents = List.of(
    Document.fromText("Hello world"),
    Document.fromText("Goodbye world")
);
EmbedResponse response = genkit.embed("openai/text-embedding-3-small", documents);
```

## Modules

| Module | Description |
|--------|-------------|
| **genkit-core** | Core framework: actions, flows, registry, tracing (OpenTelemetry) |
| **genkit-ai** | AI abstractions: models, embedders, tools, prompts, retrievers, indexers, evaluators |
| **genkit** | Main entry point combining core and AI with reflection server |
| **plugins/openai** | OpenAI models (GPT-4o, GPT-4o-mini, etc.) and embeddings |
| **plugins/jetty** | HTTP server plugin using Jetty 12 |
| **plugins/localvec** | Local file-based vector store for development |

## Features

| Feature | Description |
|---------|-------------|
| **Unified Generation API** | Generate text, structured data, and handle tool calls from any model |
| **Flows** | Observable, traceable AI workflows with HTTP endpoint exposure |
| **Tools** | Define callable tools for AI models with automatic execution |
| **DotPrompt** | Template-based prompt management with Handlebars support |
| **Embeddings** | Vector embedding generation for semantic search |
| **RAG Support** | Retrievers and indexers for retrieval-augmented generation |
| **Evaluations** | Built-in evaluation framework with custom evaluator support |
| **Streaming** | Real-time response streaming with chunk callbacks |
| **Tracing** | Built-in OpenTelemetry integration |
| **Metrics** | Token usage, latency, and request metrics via OpenTelemetry |
| **Dev UI** | Full integration with Genkit CLI and developer tools |

## Observability

Genkit Java SDK provides comprehensive observability features through OpenTelemetry integration:

### Tracing

All actions (models, tools, flows) are automatically traced with rich metadata:

- **Span types**: `action`, `flow`, `flowStep`, `util`
- **Subtypes**: `model`, `tool`, `flow`, `embedder`, etc.
- **Session tracking**: `sessionId` and `threadName` for multi-turn conversations
- **Input/Output capture**: Full request/response data in span attributes

Example span attributes:
```
genkit:name = "openai/gpt-4o-mini"
genkit:type = "action"
genkit:metadata:subtype = "model"
genkit:path = "/{myFlow,t:flow}/{openai/gpt-4o-mini,t:action,s:model}"
genkit:input = {...}
genkit:output = {...}
genkit:sessionId = "user-123"
```

### Metrics

The SDK exposes OpenTelemetry metrics for monitoring:

| Metric | Description |
|--------|-------------|
| `genkit/ai/generate/requests` | Model generation request count |
| `genkit/ai/generate/latency` | Model generation latency (ms) |
| `genkit/ai/generate/input/tokens` | Input token count |
| `genkit/ai/generate/output/tokens` | Output token count |
| `genkit/ai/generate/input/characters` | Input character count |
| `genkit/ai/generate/output/characters` | Output character count |
| `genkit/ai/generate/input/images` | Input image count |
| `genkit/ai/generate/output/images` | Output image count |
| `genkit/ai/generate/thinking/tokens` | Thinking/reasoning token count |
| `genkit/tool/requests` | Tool execution request count |
| `genkit/tool/latency` | Tool execution latency (ms) |
| `genkit/feature/requests` | Feature (flow) request count |
| `genkit/feature/latency` | Feature (flow) latency (ms) |
| `genkit/action/requests` | General action request count |
| `genkit/action/latency` | General action latency (ms) |

### Usage Tracking

Model responses include detailed usage statistics:

```java
ModelResponse response = genkit.generate(options);
Usage usage = response.getUsage();

System.out.println("Input tokens: " + usage.getInputTokens());
System.out.println("Output tokens: " + usage.getOutputTokens());
System.out.println("Latency: " + response.getLatencyMs() + "ms");
```

### Session Context

Track multi-turn conversations with session and thread context:

```java
ActionContext ctx = ActionContext.builder()
    .registry(genkit.getRegistry())
    .sessionId("user-123")
    .threadName("support-chat")
    .build();
```

## Samples

The following samples are available in `java/samples/`:

| Sample | Description |
|--------|-------------|
| **openai** | Basic OpenAI integration with flows and tools |
| **dotprompt** | DotPrompt files with complex inputs/outputs, variants, and partials |
| **rag** | RAG application with local vector store |
| **evaluations** | Custom evaluators and evaluation workflows |
| **complex-io** | Complex nested types, arrays, maps in flow inputs/outputs |

## Development

### Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key (for samples)

### Building

```bash
cd java
mvn clean install
```

### Running Tests

```bash
mvn test
```

### Running Samples

```bash
export OPENAI_API_KEY=your-api-key
cd java/samples/openai
./run.sh
# Or: mvn compile exec:java
```

## CLI Integration

The Java implementation works with the Genkit CLI. Start your application with:

```bash
genkit start -- ./run.sh
# Or: genkit start -- mvn exec:java
```

The reflection server starts automatically in dev mode (`devMode(true)`).

## Dev UI

When running in dev mode, Genkit starts a reflection server on port 3100 (configurable via `reflectionPort()`).
The Dev UI connects to this server to:

- List all registered actions (flows, models, tools, prompts, retrievers, evaluators)
- Run actions with test inputs
- View traces and execution logs
- Manage datasets and run evaluations

## Architecture

```
com.google.genkit
├── core/                    # Core framework
│   ├── Action               # Base action interface
│   ├── ActionDef            # Action implementation
│   ├── ActionContext        # Execution context with registry access
│   ├── Flow                 # Flow definition
│   ├── Registry             # Action registry
│   ├── Plugin               # Plugin interface
│   └── tracing/             # OpenTelemetry integration
│       ├── Tracer           # Span management
│       └── TelemetryClient  # Telemetry export
├── ai/                      # AI features
│   ├── Model                # Model interface
│   ├── ModelRequest/Response# Model I/O types
│   ├── Tool                 # Tool definition
│   ├── Embedder             # Embedder interface
│   ├── Retriever            # Retriever interface
│   ├── Indexer              # Indexer interface
│   ├── Prompt               # Prompt templates
│   ├── telemetry/           # AI-specific metrics
│   │   ├── GenerateTelemetry# Model generation metrics
│   │   ├── ToolTelemetry    # Tool execution metrics
│   │   ├── ActionTelemetry  # Action execution metrics
│   │   ├── FeatureTelemetry # Flow/feature metrics
│   │   └── ModelTelemetryHelper # Telemetry helper
│   └── evaluation/          # Evaluation framework
│       ├── Evaluator        # Evaluator definition
│       ├── EvaluationManager# Run evaluations
│       └── DatasetStore     # Dataset management
├── genkit/                  # Main module
│   ├── Genkit               # Main entry point & builder
│   ├── GenkitOptions        # Configuration options
│   ├── ReflectionServer     # Dev UI integration
│   └── prompt/              # DotPrompt support
│       ├── DotPrompt        # Prompt file parser
│       └── ExecutablePrompt # Prompt execution
└── plugins/                 # Plugin implementations
    ├── openai/              # OpenAI models & embeddings
    ├── jetty/               # Jetty HTTP server
    └── localvec/            # Local vector store
```

## License

Apache License 2.0
