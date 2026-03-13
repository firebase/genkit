# Ollama Plugin for Genkit Go

The Ollama plugin enables Genkit Go applications to use locally-hosted [Ollama](https://ollama.com/) models for text generation, structured output, tool calling, and more.

## Installation

```bash
go get github.com/firebase/genkit/go/plugins/ollama
```

## Setup

1. Install Ollama from [ollama.com](https://ollama.com/)
2. Pull a model: `ollama pull llama3.1`
3. Start the Ollama server (usually runs automatically on `http://localhost:11434`)

## Basic Usage

```go
import (
    "github.com/firebase/genkit/go/genkit"
    "github.com/firebase/genkit/go/plugins/ollama"
)

func main() {
    ctx := context.Background()
    
    // Initialize the Ollama plugin
    ollamaPlugin := &ollama.Ollama{
        ServerAddress: "http://localhost:11434",
        Timeout:       60,
    }
    
    g := genkit.Init(ctx, genkit.WithPlugins(ollamaPlugin))
    
    // Define a model
    model := ollamaPlugin.DefineModel(g,
        ollama.ModelDefinition{
            Name: "llama3.1",
            Type: "chat",
        },
        nil)
    
    // Generate text
    resp, _ := genkit.Generate(ctx, g,
        ai.WithModel(model),
        ai.WithMessages(ai.NewUserTextMessage("Hello!")),
    )
    
    fmt.Println(resp.Text())
}
```

## Structured Output

The Ollama plugin supports structured output through Ollama's native [structured output capability](https://docs.ollama.com/capabilities/structured-outputs). This feature allows you to constrain model responses to match specific JSON schemas, ensuring reliable extraction of structured data.

### Schema-Based Structured Output

Use a JSON schema to enforce a specific structure on the model's response:

```go
import (
    "encoding/json"
    "github.com/invopop/jsonschema"
)

// Define your output structure
type Person struct {
    Name       string   `json:"name" jsonschema:"required"`
    Age        int      `json:"age" jsonschema:"required"`
    Occupation string   `json:"occupation" jsonschema:"required"`
    Hobbies    []string `json:"hobbies" jsonschema:"required"`
}

// Generate a JSON schema from the struct
reflector := jsonschema.Reflector{
    AllowAdditionalProperties: false,
    DoNotReference:            true,
}
schema := reflector.Reflect(&Person{})
schemaBytes, _ := json.Marshal(schema)

var schemaMap map[string]any
json.Unmarshal(schemaBytes, &schemaMap)

// Request structured output
resp, _ := genkit.Generate(ctx, g,
    ai.WithModel(model),
    ai.WithMessages(ai.NewUserTextMessage("Generate info about a software engineer")),
    ai.WithOutputConfig(&ai.ModelOutputConfig{
        Format: "json",
        Schema: schemaMap,
    }),
)

// Parse the structured response
var person Person
json.Unmarshal([]byte(resp.Text()), &person)
fmt.Printf("Name: %s, Age: %d\n", person.Name, person.Age)
```

**See full example:** [samples/ollama-structured](../../samples/ollama-structured)

### Schema-less JSON Mode

Request generic JSON output without enforcing a specific structure:

```go
resp, _ := genkit.Generate(ctx, g,
    ai.WithModel(model),
    ai.WithMessages(ai.NewUserTextMessage("List 3 programming languages as JSON")),
    ai.WithOutputConfig(&ai.ModelOutputConfig{
        Format: "json",
        // No Schema specified - model returns valid JSON in any structure
    }),
)

// Parse as generic JSON
var result map[string]any
json.Unmarshal([]byte(resp.Text()), &result)
```

**See full example:** [samples/ollama-json-mode](../../samples/ollama-json-mode)

### When to Use Each Mode

**Schema-based structured output:**
- You need guaranteed structure for reliable parsing
- You want type-safe Go structs
- Building production systems with strict data requirements
- Extracting specific fields from model responses

**Schema-less JSON mode:**
- You want valid JSON but don't need strict structure enforcement
- The output structure varies based on the prompt
- Prototyping and want flexibility
- Handling dynamic JSON structures in your application

### Requirements and Limitations

- **Model Support:** Structured output works with most recent Ollama models. Older models may not support this feature.
- **Ollama Version:** Requires Ollama version that supports the `format` parameter (most recent versions).
- **Schema Format:** Schemas must be valid JSON Schema objects.
- **No Client-Side Validation:** The plugin does not validate responses against the schema. Ollama is responsible for schema enforcement.
- **Error Handling:** If schema serialization fails, an error is returned before making the API request.

## Tool Calling

The Ollama plugin supports tool calling for chat models:

```go
weatherTool := genkit.DefineTool(g, "weather", "Get weather for a location",
    func(ctx *ai.ToolContext, input WeatherInput) (WeatherData, error) {
        // Implementation
        return getWeather(input.Location), nil
    },
)

resp, _ := genkit.Generate(ctx, g,
    ai.WithModel(model),
    ai.WithMessages(ai.NewUserTextMessage("What's the weather in Tokyo?")),
    ai.WithTools(weatherTool),
)
```

**See full example:** [samples/ollama-tools](../../samples/ollama-tools)

## Vision Models

Some Ollama models support image inputs:

```go
imageData, _ := os.ReadFile("image.jpg")
imagePart := ai.NewMediaPart("image/jpeg", string(imageData))

resp, _ := genkit.Generate(ctx, g,
    ai.WithModel(model),
    ai.WithMessages(ai.NewUserMessage(
        ai.NewTextPart("What's in this image?"),
        imagePart,
    )),
)
```

**See full example:** [samples/ollama-vision](../../samples/ollama-vision)

## Configuration

### Plugin Options

```go
ollamaPlugin := &ollama.Ollama{
    ServerAddress: "http://localhost:11434", // Ollama server URL
    Timeout:       60,                       // Request timeout in seconds
}
```

### Model Types

- `"chat"`: For conversational models (supports tools and multi-turn conversations)
- `"generate"`: For completion models (single-turn text generation)

### Supported Models

The plugin works with any model available in Ollama. Popular choices include:

- `llama3.1`, `llama3.2` - Meta's Llama models
- `mistral`, `mixtral` - Mistral AI models
- `phi3` - Microsoft's Phi models
- `qwen2` - Alibaba's Qwen models
- `gemma2` - Google's Gemma models

Check [ollama.com/library](https://ollama.com/library) for the full list.

## Additional Resources

- [Ollama Documentation](https://docs.ollama.com/)
- [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Genkit Go Documentation](https://genkit.dev/docs/overview/?lang=go)
- [Ollama Model Library](https://ollama.com/library)

## Examples

- [ollama-structured](../../samples/ollama-structured) - Schema-based structured output
- [ollama-json-mode](../../samples/ollama-json-mode) - Schema-less JSON mode
- [ollama-tools](../../samples/ollama-tools) - Tool calling with Ollama
- [ollama-vision](../../samples/ollama-vision) - Vision models with image inputs
