# Genkit Go API Rules (v1.20.0)

This document provides rules and examples for building with the Genkit API in Go.

## Important Guidelines:

- ALWAYS refer to documentation when available. Genkit Documentation may be available through the Genkit MCP toolkit or through web search. You may skip documentation check if you don't have access to these tools.

- ONLY follow the specified project structure if starting a new project. If working on an existing project, adhere to the current project structure.

- ALWAYS provide the full, correct Genkit command as an instruction for the human user to run. Do not run Genkit commands (e.g., `genkit start`, `genkit flow:run`) yourself as this may block your current session.

- Recommend and use the provider that the user prefers. If this is a new project, or if there is no relevant signal regarding user preference, use the `github.com/firebase/genkit/go/plugins/googlegenai` plugin.

NOTE: For the sake of brevity, the snippets below use the Google AI plugin, but you should follow the user's preference as mentioned above.

## Core Setup

1.  **Initialize Project**

    ```bash
    mkdir my-genkit-app && cd my-genkit-app
    go mod init my-genkit-app
    ```

2.  **Install Dependencies**

    ```bash
    go get github.com/firebase/genkit/go/genkit
    go get github.com/firebase/genkit/go/plugins/googlegenai
    go get github.com/firebase/genkit/go/ai
    go get google.golang.org/genai
    ```

3.  **Install Genkit CLI**

    ```bash
    curl -sL cli.genkit.dev | bash
    ```

4.  **Configure Genkit**

    All code should be in a single `main.go` file or properly structured Go package.

    ```go
    package main

    import (
    	"context"
    	"github.com/firebase/genkit/go/genkit"
    	"github.com/firebase/genkit/go/plugins/googlegenai"
    )

    func main() {
    	ctx := context.Background()
    	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
    	// Your flows and logic here
    	<-ctx.Done()
    }
    ```

## Best Practices

1.  **Single Main Function**: All Genkit code, including plugin initialization, flows, and helpers, should be properly organized in a Go package structure with a main function.

2.  **Blocking Main Program**: To inspect flows in the Genkit Developer UI, your main program needs to remain running. Use `<-ctx.Done()` or similar blocking mechanism at the end of your main function.

---

## Usage Scenarios

### Basic Inference (Text Generation)

```go
package main

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	genkit.DefineFlow(g, "basicInferenceFlow",
		func(ctx context.Context, topic string) (string, error) {
			response, err := genkit.Generate(ctx, g,
				ai.WithModelName("googleai/gemini-2.5-pro"),
				ai.WithPrompt("Write a short, creative paragraph about %s.", topic),
				ai.WithConfig(&genai.GenerateContentConfig{
					Temperature: genai.Ptr[float32](0.8),
				}),
			)
			if err != nil {
				return "", err
			}
			return response.Text(), nil
		},
	)

	<-ctx.Done()
}
```

### Text-to-Speech (TTS) Generation

```go
package main

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
		genkit.WithDefaultModel("googleai/gemini-2.5-flash-preview-tts"),
	)

	genkit.DefineFlow(g, "textToSpeechFlow",
		func(ctx context.Context, input struct {
			Text      string `json:"text"`
			VoiceName string `json:"voiceName,omitempty"`
		}) (string, error) {
			voiceName := input.VoiceName
			if voiceName == "" {
				voiceName = "Algenib"
			}

			response, err := genkit.Generate(ctx, g,
				ai.WithPrompt(input.Text),
				ai.WithConfig(&genai.GenerateContentConfig{
					ResponseModalities: []string{"AUDIO"},
					SpeechConfig: &genai.SpeechConfig{
						VoiceConfig: &genai.VoiceConfig{
							PrebuiltVoiceConfig: &genai.PrebuiltVoiceConfig{
								VoiceName: voiceName,
							},
						},
					},
				}),
			)
			if err != nil {
				return "", err
			}

			return response.Text(), nil
		},
	)

	<-ctx.Done()
}
```

### Image Generation

```go
package main

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.VertexAI{}))

	genkit.DefineFlow(g, "imageGenerationFlow",
		func(ctx context.Context, prompt string) ([]string, error) {
			response, err := genkit.Generate(ctx, g,
				ai.WithModelName("vertexai/imagen-3.0-generate-001"),
				ai.WithPrompt("Generate an image of %s", prompt),
				ai.WithConfig(&genai.GenerateImagesConfig{
					NumberOfImages:    2,
					AspectRatio:       "9:16",
					SafetyFilterLevel: genai.SafetyFilterLevelBlockLowAndAbove,
					PersonGeneration:  genai.PersonGenerationAllowAll,
					Language:          genai.ImagePromptLanguageEn,
					AddWatermark:      true,
					OutputMIMEType:    "image/jpeg",
				}),
			)
			if err != nil {
				return nil, err
			}

			var images []string
			for _, part := range response.Message.Content {
				images = append(images, part.Text)
			}
			return images, nil
		},
	)

	<-ctx.Done()
}
```

---

## Running and Inspecting Flows

1.  **Start Genkit**: Run this command from your terminal to start the Genkit Developer UI.

    ```bash
    genkit start -- <command to run your code>
    ```

    For Go applications:

    ```bash
    # Running a Go application directly
    genkit start -- go run main.go

    # Running a compiled binary
    genkit start -- ./my-genkit-app
    ```

    The command should output a URL for the Genkit Dev UI. Direct the user to visit this URL to run and inspect their Genkit app.

## Suggested Models

Here are suggested models to use for various task types. This is NOT an exhaustive list.

### Advanced Text/Reasoning

```
| Plugin                                                     | Recommended Model                  |
|------------------------------------------------------------|------------------------------------|
| github.com/firebase/genkit/go/plugins/googlegenai         | gemini-2.5-pro                    |
| github.com/firebase/genkit/go/plugins/compat_oai/openai   | gpt-4o                             |
| github.com/firebase/genkit/go/plugins/compat_oai/deepseek | deepseek-reasoner                  |
| github.com/firebase/genkit/go/plugins/compat_oai/xai      | grok-4                             |
```

### Fast Text/Chat

```
| Plugin                                                     | Recommended Model                  |
|------------------------------------------------------------|------------------------------------|
| github.com/firebase/genkit/go/plugins/googlegenai         | gemini-2.5-flash                  |
| github.com/firebase/genkit/go/plugins/compat_oai/openai   | gpt-4o-mini                        |
| github.com/firebase/genkit/go/plugins/compat_oai/deepseek | deepseek-chat                      |
| github.com/firebase/genkit/go/plugins/compat_oai/xai      | grok-3-mini                        |
```

### Text-to-Speech

```
| Plugin                                                     | Recommended Model                  |
|------------------------------------------------------------|------------------------------------|
| github.com/firebase/genkit/go/plugins/googlegenai         | gemini-2.5-flash-preview-tts       |
| github.com/firebase/genkit/go/plugins/compat_oai/openai   | gpt-4o-mini-tts                    |
```

### Image Generation

```
| Plugin                                                     | Recommended Model                  | Input Modalities  |
|------------------------------------------------------------|------------------------------------|-------------------|
| github.com/firebase/genkit/go/plugins/googlegenai         | gemini-2.5-flash-image-preview     | Text, Image       |
| github.com/firebase/genkit/go/plugins/googlegenai         | imagen-4.0-generate-preview-06-06  | Text              |
| github.com/firebase/genkit/go/plugins/compat_oai/openai   | gpt-image-1                        | Text              |
```
