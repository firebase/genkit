# Genkit Google GenAI Sample

This sample demonstrates integration with Google GenAI (Gemini) models using Genkit Java, including text generation, image generation with Imagen, and text-to-speech.

## Features Demonstrated

- **Google GenAI Plugin Setup** - Configure Genkit with Gemini models
- **Text Generation** - Generate text with Gemini 2.0 Flash
- **Tool Calling** - Function calling with Gemini
- **Embeddings** - Generate text embeddings
- **Image Generation** - Generate images with Imagen 3
- **Text-to-Speech** - Generate audio with Google TTS
- **Video Generation** - Generate videos with Veo

## Prerequisites

- Java 17+
- Maven 3.6+
- Google GenAI API key (get one at https://aistudio.google.com/)

## Running the Sample

### Option 1: Direct Run

```bash
# Set your Google GenAI API key
export GOOGLE_GENAI_API_KEY=your-api-key-here
# Or use the alternative environment variable
export GOOGLE_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/google-genai

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your API key
export GOOGLE_GENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/google-genai

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

## Available Flows

| Flow | Input | Output | Description |
|------|-------|--------|-------------|
| `textGeneration` | String (prompt) | String | Generate text with Gemini |
| `toolCalling` | String (query) | String | Demonstrate tool/function calling |
| `embeddings` | String (text) | String | Generate text embeddings |
| `imageGeneration` | String (prompt) | String | Generate images with Imagen |
| `textToSpeech` | String (text) | String | Generate audio with TTS |
| `videoGeneration` | String (prompt) | String | Generate videos with Veo |

## Example API Calls

Once the server is running on port 8080:

### Text Generation
```bash
curl -X POST http://localhost:8080/textGeneration \
  -H 'Content-Type: application/json' \
  -d '"Explain quantum computing in simple terms"'
```

### Tool Calling
```bash
curl -X POST http://localhost:8080/toolCalling \
  -H 'Content-Type: application/json' \
  -d '"What is the weather in Tokyo?"'
```

### Embeddings
```bash
curl -X POST http://localhost:8080/embeddings \
  -H 'Content-Type: application/json' \
  -d '"Hello, world!"'
```

### Image Generation
```bash
curl -X POST http://localhost:8080/imageGeneration \
  -H 'Content-Type: application/json' \
  -d '"A serene Japanese garden with cherry blossoms"'
```

### Text-to-Speech
```bash
curl -X POST http://localhost:8080/textToSpeech \
  -H 'Content-Type: application/json' \
  -d '"Welcome to Genkit for Java!"'
```

### Video Generation
```bash
curl -X POST http://localhost:8080/videoGeneration \
  -H 'Content-Type: application/json' \
  -d '"A cat playing with a ball of yarn"'
```

## Generated Media Files

Media files (images, audio, video) are saved to the `generated_media/` directory in the sample folder.

## Available Models

The Google GenAI plugin provides access to:

| Model | Description |
|-------|-------------|
| `googleai/gemini-2.0-flash` | Fast, efficient Gemini model |
| `googleai/gemini-1.5-pro` | Advanced reasoning capabilities |
| `googleai/gemini-1.5-flash` | Balanced speed and capability |
| `googleai/imagen-3.0-generate-002` | Image generation |
| `googleai/text-embedding-004` | Text embeddings |

## Code Highlights

### Setting Up Genkit with Google GenAI

```java
Genkit genkit = Genkit.builder()
    .options(GenkitOptions.builder()
        .devMode(true)
        .reflectionPort(3100)
        .build())
    .plugin(GoogleGenAIPlugin.create())
    .plugin(new JettyPlugin(JettyPluginOptions.builder()
        .port(8080)
        .build()))
    .build();
```

### Text Generation with Gemini

```java
genkit.defineFlow("textGeneration", String.class, String.class, 
    (ctx, prompt) -> {
        ModelResponse response = genkit.generate(
            GenerateOptions.builder()
                .model("googleai/gemini-2.0-flash")
                .prompt(prompt)
                .config(GenerationConfig.builder()
                    .temperature(0.7)
                    .maxOutputTokens(500)
                    .build())
                .build());
        return response.getText();
    });
```

### Image Generation with Imagen

```java
genkit.defineFlow("imageGeneration", String.class, String.class,
    (ctx, prompt) -> {
        ModelResponse response = genkit.generate(
            GenerateOptions.builder()
                .model("googleai/imagen-3.0-generate-002")
                .prompt(prompt)
                .build());
        // Save generated image to file
        // ...
        return "Image saved to: " + filePath;
    });
```

## Development UI

When running with `genkit start`, access the Dev UI at http://localhost:4000 to:

- Browse all registered flows and models
- Run flows with test inputs
- View execution traces and logs
- Preview generated content

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_GENAI_API_KEY` | Google GenAI API key |
| `GOOGLE_API_KEY` | Alternative API key variable |

## See Also

- [Genkit Java README](../../README.md)
- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API Documentation](https://ai.google.dev/docs)
