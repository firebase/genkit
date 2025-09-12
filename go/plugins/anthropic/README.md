# Anthropic Plugin for Firebase Genkit

This plugin provides a comprehensive interface for using Anthropic's Claude models with Firebase Genkit, featuring dynamic model discovery, multi-modal support, streaming, and tool calling.

## Features

- 🤖 **Dynamic Model Discovery** - Automatically discovers available Claude models from the Anthropic API
- 🧪 **Beta API Support** - Access to Anthropic's experimental features and capabilities
- 🖼️ **Multi-Modal Support** - Process text and images with Claude's vision capabilities
- 🔄 **Streaming Responses** - Real-time response streaming for better user experience
- 🛠️ **Tool Calling** - Function calling capabilities for complex workflows
- 🎯 **Type Safety** - Full TypeScript-style type safety with Go generics
- 📊 **Usage Tracking** - Detailed token usage and cost tracking
- 🔧 **Flexible Configuration** - Comprehensive model configuration options

## Prerequisites

- Go 1.21 or later
- An Anthropic API key

## Installation

```bash
go get github.com/firebase/genkit/go/plugins/anthropic
```

## Setup

Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY=<your-api-key>
```

Get an API key at [https://console.anthropic.com/](https://console.anthropic.com/).

## Usage

### Basic Usage

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/firebase/genkit/go/ai"
    "github.com/firebase/genkit/go/genkit"
    "github.com/firebase/genkit/go/plugins/anthropic"
)

func main() {
    ctx := context.Background()

    // Initialize Genkit with Anthropic plugin
    g := genkit.Init(ctx, genkit.WithPlugins(&anthropic.Anthropic{}))

    // Generate text using Claude
    resp, err := genkit.Generate(ctx, g,
        ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
        ai.WithPrompt("Tell me a joke about programming"))
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(resp.Text())
}
```

### Streaming

```go
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithPrompt("Count from 1 to 10"),
    ai.WithStreaming(func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
        fmt.Print(chunk.Text())
        return nil
    }))
```

### Using Tools

```go
// Define a tool
weatherTool := &ai.ToolDefinition{
    Name:        "get_weather",
    Description: "Get the current weather for a location",
    InputSchema: map[string]any{
        "type": "object",
        "properties": map[string]any{
            "location": map[string]any{
                "type":        "string",
                "description": "The city and state, e.g. San Francisco, CA",
            },
        },
        "required": []string{"location"},
    },
}

// Generate with tools
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithPrompt("What's the weather like in San Francisco?"),
    ai.WithTools(weatherTool))
```

### Configuration

The Anthropic plugin exposes **all 14 configuration parameters** from the underlying Anthropic SDK, providing comprehensive control over model behavior with user-friendly parameter names in the Developer UI.

#### Core Configuration Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `maxTokens` | `int` | Maximum number of tokens to generate | `4096` |
| `temperature` | `float32` | Controls randomness (0.0 to 1.0) | `0.7` |
| `topK` | `int` | Top-K sampling parameter | `40` |
| `topP` | `float32` | Top-P (nucleus) sampling parameter | `0.9` |
| `stopSequences` | `[]string` | Array of sequences that will stop generation | `["Human:", "Assistant:"]` |
| `model` | `string` | Specific model to use | `"claude-3-5-sonnet-20241022"` |

#### Anthropic-Specific Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `metadata` | `map[string]any` | Custom metadata for the request | `{"user_id": "123"}` |
| `system` | `[]TextBlock` | System instructions | `[{"text": "You are helpful"}]` |
| `messages` | `[]MessageParam` | Conversation messages | `[{"role": "user", "content": "Hi"}]` |
| `tools` | `[]ToolParam` | Available tools for the model | Tool definitions |
| `toolChoice` | `ToolChoice` | How the model should use tools | `"auto"`, `"any"`, `"none"` |
| `thinking` | `ThinkingConfig` | Configuration for reasoning mode | Thinking parameters |
| `serviceTier` | `string` | Service tier for the request | `"default"` |

#### Beta API Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `useBetaAPI` | `bool` | Enable Beta API for this request | `true` |
| `betaFeatures` | `[]string` | List of beta features to enable | `["token-efficient-tools-2025-02-19"]` |
| `thinkingEnabled` | `bool` | Enable Claude's extended thinking process | `true` |
| `thinkingBudgetTokens` | `int64` | Token budget for thinking (minimum 1024) | `2048` |

#### Basic Configuration

```go
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithConfig(&ai.GenerationCommonConfig{
        Temperature:      0.7,
        MaxOutputTokens:  1000,
        TopP:            0.9,
        StopSequences:   []string{"END"},
    }),
    ai.WithPrompt("Write a creative story"))
```

#### Map-based Configuration

```go
resp, err := genkit.Generate(ctx, g,
    ai.WithModel(anthropic.AnthropicModel(g, "claude-sonnet-4-20250514")),
    ai.WithConfig(map[string]any{
        "maxTokens":     1024,
        "temperature":   0.5,
        "topK":         20,
        "topP":         0.8,
        "stopSequences": []string{"END"},
    }),
    ai.WithMessages(ai.NewUserMessage(ai.NewTextPart("Hello!"))),
)
```

#### Pass-through Parameters

The plugin supports **pass-through parameters** for Anthropic-specific options:

```go
import "github.com/firebase/genkit/go/plugins/anthropic"

resp, err := genkit.Generate(ctx, g,
    ai.WithModel(anthropic.AnthropicModel(g, "claude-sonnet-4-20250514")),
    ai.WithConfig(&anthropic.AnthropicConfig{
        GenerationCommonConfig: ai.GenerationCommonConfig{
            MaxOutputTokens: 1024,
            Temperature:     0.7,
            TopP:           0.9,
        },
        Metadata: map[string]any{
            "user_id": "user123",
            "session": "session456",
        },
    }),
    ai.WithMessages(ai.NewUserMessage(ai.NewTextPart("Hello!"))),
)
```

#### Map-based Pass-through Configuration

```go
resp, err := genkit.Generate(ctx, g,
    ai.WithModel(anthropic.AnthropicModel(g, "claude-sonnet-4-20250514")),
    ai.WithConfig(map[string]any{
        // Standard Genkit parameters
        "maxTokens":   1024,
        "temperature": 0.7,
        "topP":       0.9,
        
        // Anthropic-specific pass-through parameters
        "metadata": map[string]any{
            "user_id": "user123",
            "custom_field": "custom_value",
        },
    }),
    ai.WithMessages(ai.NewUserMessage(ai.NewTextPart("Hello!"))),
)
```

## Supported Models

The plugin **dynamically discovers** available Claude models from the Anthropic API. Currently supported models include:

- **claude-opus-4-1-20250805** - Claude Opus 4.1 (latest flagship)
- **claude-opus-4-20250514** - Claude Opus 4
- **claude-sonnet-4-20250514** - Claude Sonnet 4
- **claude-3-7-sonnet-20250219** - Claude Sonnet 3.7
- **claude-3-5-haiku-20241022** - Claude Haiku 3.5
- **claude-3-haiku-20240307** - Claude Haiku 3

### Model Capabilities

All Claude models support:
- ✅ **Multi-turn conversations** - Maintain context across multiple exchanges
- ✅ **Tool calling** - Execute functions and integrate with external systems
- ✅ **System prompts** - Set behavior and personality
- ✅ **Multi-modal input** - Process text and images simultaneously
- ✅ **Streaming responses** - Real-time response generation
- ✅ **Constrained output** - JSON schema validation (when not using tools)
- ✅ **Usage tracking** - Detailed token consumption metrics

## Model Capabilities

### Text Generation
All Claude models excel at various text generation tasks including:
- Creative writing
- Code generation and debugging
- Analysis and reasoning
- Question answering
- Summarization

### Multi-Modal Support

Claude models can process both text and images with advanced vision capabilities:

```go
// Example with image URL (automatically downloaded and processed)
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithMessages(
        ai.NewUserMessage(
            ai.NewTextPart("What do you see in this image?"),
            ai.NewMediaPart("image/jpeg", "https://example.com/image.jpg"),
        ),
    ))

// Example with base64 encoded image
imageData := []byte{...} // Your image data
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithMessages(
        ai.NewUserMessage(
            ai.NewTextPart("Analyze this image"),
            ai.NewMediaPart("image/jpeg", "data:image/jpeg;base64,"+base64.StdEncoding.EncodeToString(imageData)),
        ),
    ))
```

**Supported Image Formats:**
- JPEG (`image/jpeg`)
- PNG (`image/png`)
- GIF (`image/gif`)
- WebP (`image/webp`)

**Image Sources:**
- HTTP/HTTPS URLs (automatically downloaded)
- Base64 data URLs
- Local file paths

### Tool Calling
Claude models can use tools to perform actions or retrieve information:

```go
// The model can call tools and you can provide responses
if resp.Message.Content[0].IsToolRequest() {
    toolReq := resp.Message.Content[0].ToolRequest
    // Handle tool call and provide response
    toolResp := &ai.ToolResponse{
        Name:   toolReq.Name,
        Output: map[string]any{"result": "Tool execution result"},
    }
    // Continue conversation with tool response...
}
```

## Beta API Support

The Anthropic plugin supports Anthropic's Beta API, providing access to experimental features and capabilities. Beta API support can be configured at both the plugin level (global) and per-request level.

### Beta API Features

- **Plugin-level Beta API configuration**: Enable Beta API globally for all requests
- **Request-level Beta API configuration**: Override plugin settings per request
- **Automatic Beta API detection**: Auto-enable Beta API when beta features are specified
- **Beta feature specification**: Support for specific beta features like token-efficient tools and prompt caching
- **Beta model discovery**: Model discovery respects Beta API configuration to discover beta-specific models
- **Full backward compatibility**: Existing functionality remains unchanged

### Plugin-Level Beta API Configuration

Configure Beta API support when initializing the Anthropic plugin:

```go
plugin := &anthropic.Anthropic{
    APIKey:     "your-api-key",
    UseBetaAPI: true,
    BetaFeatures: []string{
        "token-efficient-tools-2025-02-19",
        "prompt-caching-2024-07-31",
    },
}

g := genkit.Init(ctx, genkit.WithPlugins(plugin))
```

### Request-Level Beta API Configuration

Override plugin settings for individual requests:

```go
// Enable Beta API for this request
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithPrompt("Your prompt here"),
    ai.WithConfig(map[string]any{
        "useBetaAPI": true,
        "betaFeatures": []string{
            "token-efficient-tools-2025-02-19",
        },
    }))
```

### Auto-Enable Beta API

Beta API is automatically enabled when beta features are specified:

```go
// Beta API is auto-enabled because betaFeatures are specified
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithPrompt("Your prompt here"),
    ai.WithConfig(map[string]any{
        "betaFeatures": []string{
            "interleaved-thinking-2025-05-14",
        },
    }))
```

### Supported Beta Features

The following beta features are supported:

- `token-efficient-tools-2025-02-19`: More efficient tool usage
- `prompt-caching-2024-07-31`: Prompt caching for improved performance
- `interleaved-thinking-2025-05-14`: Enhanced reasoning capabilities
- `max-tokens-3-5-sonnet-2024-07-15`: Extended token limits for Claude 3.5 Sonnet

### Beta API with Thinking Mode

```go
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithPrompt("Solve this step by step: What is 15% of 240?"),
    ai.WithConfig(map[string]any{
        "useBetaAPI":           true,
        "thinkingEnabled":      true,
        "thinkingBudgetTokens": 2048,
        "temperature":          1.0, // Must be 1.0 when thinking is enabled
        "maxOutputTokens":      4096, // Must be greater than thinking budget tokens
    }))
```

### Beta Model Discovery

When Beta API is enabled at the plugin level, model discovery will use Beta API headers to potentially discover beta-specific models:

```go
// Plugin with Beta API enabled will discover models using Beta API
plugin := &anthropic.Anthropic{
    APIKey:     "your-api-key",
    UseBetaAPI: true,
    BetaFeatures: []string{
        "token-efficient-tools-2025-02-19",
    },
}

// Model discovery will include beta headers in the API call
g := genkit.Init(ctx, genkit.WithPlugins(plugin))
```

This ensures that if Anthropic exposes different models through their Beta endpoints, they will be discovered and made available.

### Beta API Notes

- Beta API features may change or be removed without notice
- Not all models may support all beta features
- Beta API usage may have different rate limits or pricing
- Model discovery with Beta API may return different models than standard API
- Always test beta features thoroughly before production use

## Advanced Usage

### Genkit Flows

Create reusable flows with the plugin:

```go
// Define a multi-modal analysis flow
multiModalFlow := genkit.DefineFlow(g, "analyzeImage",
    func(ctx context.Context, req struct {
        Text     string `json:"text"`
        ImageURL string `json:"imageUrl"`
    }) (struct {
        Analysis string `json:"analysis"`
    }, error) {
        resp, err := genkit.Generate(ctx, g,
            ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
            ai.WithMessages(
                ai.NewUserMessage(
                    ai.NewTextPart(req.Text),
                    ai.NewMediaPart("image/jpeg", req.ImageURL),
                ),
            ),
        )
        if err != nil {
            return struct{ Analysis string }{}, err
        }
        return struct{ Analysis string }{Analysis: resp.Text()}, nil
    })
```

### Dynamic Model Selection

```go
// List available models
actions := plugin.ListActions(ctx)
for _, action := range actions {
    if action.Type == api.ActionTypeModel {
        fmt.Printf("Available model: %s\n", action.Name)
    }
}

// Use the latest Claude model dynamically
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-opus-4-1-20250805"),
    ai.WithPrompt("Hello, Claude!"))
```

## Error Handling

The plugin provides detailed error messages for common issues:

```go
resp, err := genkit.Generate(ctx, g,
    ai.WithModelName("anthropic/claude-sonnet-4-20250514"),
    ai.WithPrompt("Hello"))
if err != nil {
    switch {
    case strings.Contains(err.Error(), "API key"):
        log.Fatal("Invalid or missing API key")
    case strings.Contains(err.Error(), "rate limit"):
        log.Fatal("Rate limit exceeded")
    case strings.Contains(err.Error(), "Could not process image"):
        log.Fatal("Image processing failed - check image format and URL")
    default:
        log.Fatalf("Generation failed: %v", err)
    }
}
```

## Testing

Run the comprehensive test suite:

```bash
# Unit tests
cd go/plugins/anthropic
go test -v

# Integration tests (requires API key)
export ANTHROPIC_API_KEY=your_api_key_here
go test -v

# Example application with all features
cd scratch/go-anthropic-plugin-test
go run .                    # Run all tests including Beta API
go run . beta               # Run only Beta API tests
go run . beta-discovery     # Run only Beta API model discovery tests
go run . help               # Show available test options
```

### Available Test Categories

The test suite includes comprehensive testing for:

- **Basic Generation**: Text generation with various models
- **Multi-Modal**: Image analysis and vision capabilities
- **Tool Calling**: Function calling and tool integration
- **Streaming**: Real-time response streaming
- **Beta API**: Experimental features and capabilities
- **Model Discovery**: Dynamic model discovery with Beta API support
- **Configuration**: All configuration options and parameters

## Performance Considerations

- **Model Selection**: Claude Haiku is fastest for simple tasks, Sonnet for balanced performance, Opus for complex reasoning
- **Streaming**: Use streaming for long responses to improve perceived performance
- **Image Processing**: Large images are automatically optimized for processing
- **Caching**: Consider implementing response caching for repeated queries

## Troubleshooting

### Common Issues

1. **"Could not process image"**: Ensure image URLs are accessible and in supported formats
2. **Rate limiting**: Implement exponential backoff for production applications
3. **Token limits**: Monitor usage and adjust `MaxOutputTokens` as needed

### Debug Mode

Enable detailed logging:

```go
// Set environment variable for debug output
os.Setenv("GENKIT_LOG_LEVEL", "debug")
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This plugin is licensed under the Apache License 2.0. See the LICENSE file for details.