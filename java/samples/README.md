# Genkit Java Samples

This directory contains sample applications demonstrating various features of Genkit Java SDK.

## Prerequisites

All samples require:

- **Java 17+**
- **Maven 3.6+**
- **API Key** for the model provider (OpenAI or Google GenAI)

## Quick Start

Each sample can be run with:

```bash
# 1. Set your API key (OpenAI samples)
export OPENAI_API_KEY=your-api-key-here

# Or for Google GenAI samples
export GOOGLE_GENAI_API_KEY=your-api-key-here

# 2. Navigate to the sample directory
cd java/samples/<sample-name>

# 3. Run the sample
./run.sh
# Or: mvn compile exec:java
```

## Running with Genkit Dev UI

For the best development experience, use the Genkit CLI to run samples with the Dev UI:

```bash
# Install Genkit CLI (if not already installed)
npm install -g genkit

# Run sample with Dev UI
cd java/samples/<sample-name>
genkit start -- ./run.sh
# Or: genkit start -- mvn exec:java
```

The Dev UI will be available at `http://localhost:4000` and allows you to:
- View all registered actions (flows, models, tools, prompts)
- Run flows with test inputs
- Inspect traces and execution logs
- Manage datasets and run evaluations

## Available Samples

| Sample | Description | API Key Required |
|--------|-------------|------------------|
| [openai](./openai) | Basic OpenAI integration with flows and tools | `OPENAI_API_KEY` |
| [google-genai](./google-genai) | Google Gemini integration with image generation | `GOOGLE_GENAI_API_KEY` |
| [dotprompt](./dotprompt) | DotPrompt files with complex inputs/outputs, variants, and partials | `OPENAI_API_KEY` |
| [rag](./rag) | RAG application with local vector store | `OPENAI_API_KEY` |
| [chat-session](./chat-session) | Multi-turn chat with session persistence | `OPENAI_API_KEY` |
| [evaluations](./evaluations) | Custom evaluators and evaluation workflows | `OPENAI_API_KEY` |
| [complex-io](./complex-io) | Complex nested types, arrays, maps in flow inputs/outputs | `OPENAI_API_KEY` |
| [middleware](./middleware) | Middleware patterns for logging, caching, rate limiting | `OPENAI_API_KEY` |
| [multi-agent](./multi-agent) | Multi-agent orchestration patterns | `OPENAI_API_KEY` |
| [interrupts](./interrupts) | Flow interrupts and human-in-the-loop patterns | `OPENAI_API_KEY` |
| [mcp](./mcp) | Model Context Protocol (MCP) integration | `OPENAI_API_KEY` |

## Sample Details

### OpenAI Sample

Basic integration with OpenAI models demonstrating:
- Text generation with GPT-4o
- Tool usage
- Streaming responses
- Flow definitions

```bash
cd java/samples/openai
export OPENAI_API_KEY=your-key
./run.sh
```

### Google GenAI Sample

Integration with Google Gemini models demonstrating:
- Text generation with Gemini
- Image generation with Imagen
- Multi-modal inputs

```bash
cd java/samples/google-genai
export GOOGLE_GENAI_API_KEY=your-key
./run.sh
```

### DotPrompt Sample

Template-based prompts with Handlebars demonstrating:
- Loading `.prompt` files
- Complex input/output schemas
- Prompt variants (e.g., `recipe.robot.prompt`)
- Partials for reusable templates

```bash
cd java/samples/dotprompt
export OPENAI_API_KEY=your-key
./run.sh
```

### RAG Sample

Retrieval-Augmented Generation demonstrating:
- Local vector store for development
- Document indexing and retrieval
- Semantic search with embeddings
- Context-aware generation

```bash
cd java/samples/rag
export OPENAI_API_KEY=your-key
./run.sh
```

### Chat Session Sample

Multi-turn conversations demonstrating:
- Conversation history management
- Session state persistence
- Tool integration within sessions
- Multiple chat personas

```bash
cd java/samples/chat-session
export OPENAI_API_KEY=your-key
./run.sh
```

### Evaluations Sample

AI output evaluation demonstrating:
- Custom evaluator definitions
- Dataset management
- Evaluation workflows
- Quality metrics

```bash
cd java/samples/evaluations
export OPENAI_API_KEY=your-key
./run.sh
```

### Complex I/O Sample

Complex type handling demonstrating:
- Deeply nested object types
- Arrays and collections
- Optional fields and maps
- Domain objects (e-commerce, analytics)

```bash
cd java/samples/complex-io
export OPENAI_API_KEY=your-key
./run.sh
```

### Middleware Sample

Cross-cutting concerns demonstrating:
- Logging middleware
- Caching middleware
- Rate limiting
- Request/response transformation
- Error handling

```bash
cd java/samples/middleware
export OPENAI_API_KEY=your-key
./run.sh
```

### Multi-Agent Sample

Multi-agent orchestration demonstrating:
- Agent coordination patterns
- Task delegation
- Inter-agent communication

```bash
cd java/samples/multi-agent
export OPENAI_API_KEY=your-key
./run.sh
```

### Interrupts Sample

Flow control demonstrating:
- Human-in-the-loop patterns
- Flow interrupts and resumption
- External input handling

```bash
cd java/samples/interrupts
export OPENAI_API_KEY=your-key
./run.sh
```

### MCP Sample

Model Context Protocol integration demonstrating:
- MCP server connections
- Tool discovery and usage
- Resource management
- File operations

```bash
cd java/samples/mcp
export OPENAI_API_KEY=your-key
./run.sh
```

## Building All Samples

From the Java root directory:

```bash
cd java
mvn clean install
```

## Common Issues

### API Key Not Set

```
Error: OPENAI_API_KEY environment variable is not set
```

**Solution**: Set the required API key for the sample you're running.

### Port Already in Use

```
Error: Address already in use (Bind failed)
```

**Solution**: The default port (8080 or 3100) is in use. Either stop the other process or configure a different port.

### Maven Dependencies Not Found

```
Error: Could not find artifact com.google.genkit:genkit
```

**Solution**: Build the parent project first:
```bash
cd java
mvn clean install -DskipTests
```

## Additional Resources

- [Genkit Java README](../README.md) - Main documentation
- [Genkit Documentation](https://firebase.google.com/docs/genkit) - Official docs
- [Genkit GitHub](https://github.com/firebase/genkit) - Source code
