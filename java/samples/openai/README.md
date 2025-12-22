# Genkit OpenAI Sample

This sample demonstrates basic integration with OpenAI models using Genkit Java.

## Features Demonstrated

- **OpenAI Plugin Setup** - Configure Genkit with OpenAI models
- **Flow Definitions** - Create observable, traceable AI workflows
- **Tool Usage** - Define and use tools with automatic execution
- **Text Generation** - Generate text with GPT-4o and GPT-4o-mini
- **Streaming** - Real-time response streaming
- **Vision Models** - Process images with vision capabilities
- **Image Generation** - Generate images with DALL-E

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/openai

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/openai

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

## Available Flows

| Flow | Input | Output | Description |
|------|-------|--------|-------------|
| `greeting` | String (name) | String | Simple greeting flow |
| `tellJoke` | String (topic) | String | Generate a joke about a topic |
| `chat` | String (message) | String | Chat with GPT-4o |
| `weatherAssistant` | String (query) | String | Weather assistant using tools |

## Example API Calls

Once the server is running on port 8080:

### Simple Greeting
```bash
curl -X POST http://localhost:8080/greeting \
  -H 'Content-Type: application/json' \
  -d '"World"'
```

### Generate a Joke
```bash
curl -X POST http://localhost:8080/tellJoke \
  -H 'Content-Type: application/json' \
  -d '"programming"'
```

### Chat
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '"What is the capital of France?"'
```

### Weather Assistant (with Tool)
```bash
curl -X POST http://localhost:8080/weatherAssistant \
  -H 'Content-Type: application/json' \
  -d '"What is the weather in Paris?"'
```

## Available Models

The OpenAI plugin provides access to:

| Model | Description |
|-------|-------------|
| `openai/gpt-4o` | Most capable model, best for complex tasks |
| `openai/gpt-4o-mini` | Faster and more cost-effective |
| `openai/gpt-4-turbo` | Previous generation GPT-4 |
| `openai/gpt-3.5-turbo` | Fast and economical |
| `openai/dall-e-3` | Image generation |
| `openai/text-embedding-3-small` | Text embeddings |
| `openai/text-embedding-3-large` | High-dimension text embeddings |

## Code Highlights

### Setting Up Genkit with OpenAI

```java
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
```

### Defining a Flow

```java
Flow<String, String, Void> jokeFlow = genkit.defineFlow(
    "tellJoke", String.class, String.class,
    (ctx, topic) -> {
        ModelResponse response = genkit.generate(
            GenerateOptions.builder()
                .model("openai/gpt-4o-mini")
                .prompt("Tell me a short, funny joke about: " + topic)
                .config(GenerationConfig.builder()
                    .temperature(0.9)
                    .maxOutputTokens(200)
                    .build())
                .build());
        return response.getText();
    });
```

### Defining and Using Tools

```java
Tool<Map<String, Object>, Map<String, Object>> weatherTool = genkit.defineTool(
    "getWeather",
    "Gets the current weather for a location",
    Map.of("type", "object", "properties",
        Map.of("location", Map.of("type", "string")),
        "required", new String[]{"location"}),
    (Class<Map<String, Object>>) (Class<?>) Map.class,
    (ctx, input) -> {
        String location = (String) input.get("location");
        return Map.of("location", location, "temperature", "72°F");
    });

// Use tool in generation
ModelResponse response = genkit.generate(
    GenerateOptions.builder()
        .model("openai/gpt-4o")
        .prompt("What's the weather in Paris?")
        .tools(List.of(weatherTool))
        .build());
```

## Development UI

When running with `genkit start`, access the Dev UI at http://localhost:4000 to:

- Browse all registered flows, tools, and models
- Run flows with test inputs
- View execution traces and logs
- Inspect tool calls and responses

## See Also

- [Genkit Java README](../../README.md)
- [OpenAI API Documentation](https://platform.openai.com/docs)
