# Genkit Chat

A full-stack multi-model AI chat application showcasing all Python Genkit features.

## Features

- 💬 **Multi-Model Chat**: Switch between Google AI, Anthropic, OpenAI, Ollama, and more
- 🔀 **Model Comparison**: Compare responses from multiple models side-by-side
- 🎙️ **Voice Input/Output**: Speech-to-text and text-to-speech support
- 📎 **File Upload**: Drag-and-drop images and documents
- 🔧 **Genkit DevUI**: Test all flows and prompts at localhost:4000
- 🌙 **Dark/Light Theme**: Beautiful Material Design with theme toggle
- 📦 **Containerized**: Podman/Docker compatible for Cloud Run deployment

## Genkit Features Demonstrated

This sample exercises all major Python Genkit capabilities:

| Feature | Implementation |
|---------|----------------|
| **Flows** | `chat_flow`, `compare_flow`, `describe_image_flow`, `rag_flow` |
| **Tools** | `web_search`, `get_weather`, `calculate`, `get_current_time` |
| **Prompts** | `.prompt` files in `backend/prompts/` |
| **Streaming** | `stream_chat_flow` with SSE |
| **RAG** | ChromaDB integration in `rag_flow` |
| **Multimodal** | Image description with vision models |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GENKIT CHAT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Angular Frontend (Port 4200/49230)               │   │
│   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │   │
│   │  │ ChatService │  │ ModelService │  │       Components           │  │   │
│   │  │  - messages │  │  - providers │  │  ├── ChatComponent         │  │   │
│   │  │  - send()   │  │  - models    │  │  ├── CompareComponent      │  │   │
│   │  │  - compare()│  │  - fetch()   │  │  └── SettingsComponent     │  │   │
│   │  └──────┬──────┘  └──────┬───────┘  └────────────────────────────┘  │   │
│   │         │                │                                           │   │
│   │         └────────┬───────┘                                           │   │
│   │                  │ HTTP/SSE                                          │   │
│   └──────────────────┼───────────────────────────────────────────────────┘   │
│                      │                                                       │
│                      │ Proxy (/api → :8000)                                  │
│                      ▼                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Python Backend (Port 8000)                       │   │
│   │  ┌──────────────────────────────────────────────────────────────┐   │   │
│   │  │                    HTTP Server (--framework robyn|fastapi)        │   │   │
│   │  │  POST /api/chat       →  chat_flow                            │   │   │
│   │  │  POST /api/compare    →  compare_flow                         │   │   │
│   │  │  GET  /api/models     →  get_available_models()               │   │   │
│   │  │  POST /api/stream     →  stream_chat_flow (SSE)               │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   │                              │                                       │   │
│   │  ┌──────────────────────────────────────────────────────────────┐   │   │
│   │  │                    Genkit Framework                           │   │   │
│   │  │  ┌───────────────────────────────────────────────────────┐   │   │   │
│   │  │  │ Flows                                                  │   │   │   │
│   │  │  │  ├── chat_flow         (single model chat)            │   │   │   │
│   │  │  │  ├── compare_flow      (multi-model comparison)       │   │   │   │
│   │  │  │  ├── stream_chat_flow  (streaming responses)          │   │   │   │
│   │  │  │  ├── describe_image    (vision/multimodal)            │   │   │   │
│   │  │  │  └── rag_flow          (retrieval-augmented gen)      │   │   │   │
│   │  │  └───────────────────────────────────────────────────────┘   │   │   │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │   │   │
│   │  │  │   Tools     │  │  Prompts    │  │    Plugins          │   │   │   │
│   │  │  │ ├─ search   │  │ ├─ chat     │  │ ├─ google_genai     │   │   │   │
│   │  │  │ ├─ weather  │  │ ├─ rag      │  │ ├─ anthropic        │   │   │   │
│   │  │  │ ├─ calculate│  │ ├─ compare  │  │ ├─ openai           │   │   │   │
│   │  │  │ └─ time     │  │ └─ describe │  │ ├─ ollama           │   │   │   │
│   │  │  └─────────────┘  └─────────────┘  │ └─ chroma (RAG)     │   │   │   │
│   │  │                                     └─────────────────────┘   │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
├──────────────────────────────┼───────────────────────────────────────────────┤
│                              ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                       Model Providers                               │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│   │  │ Google AI│ │ Anthropic│ │  OpenAI  │ │  Ollama  │ │ Vertex AI│  │   │
│   │  │  Gemini  │ │  Claude  │ │   GPT    │ │  Llama   │ │  Gemini  │  │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Chat Message Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │     │   Frontend  │     │   Backend   │     │    Model    │
│             │     │  (Angular)  │     │  (Python)   │     │  Provider   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │  Type message     │                   │                   │
       ├──────────────────>│                   │                   │
       │                   │                   │                   │
       │                   │  POST /api/chat   │                   │
       │                   │  {message, model, │                   │
       │                   │   history}        │                   │
       │                   ├──────────────────>│                   │
       │                   │                   │                   │
       │                   │                   │  g.generate()     │
       │                   │                   ├──────────────────>│
       │                   │                   │                   │
       │                   │                   │<──────────────────┤
       │                   │                   │  LLM response     │
       │                   │                   │                   │
       │                   │<──────────────────┤                   │
       │                   │  {response, model,│                   │
       │                   │   latency_ms}     │                   │
       │                   │                   │                   │
       │<──────────────────┤                   │                   │
       │  Display response │                   │                   │
       │                   │                   │                   │
```

### Model Comparison Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │     │   Frontend  │     │   Backend   │     │   Models    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │  Enter prompt,    │                   │                   │
       │  select models    │                   │                   │
       ├──────────────────>│                   │                   │
       │                   │                   │                   │
       │                   │ POST /api/compare │                   │
       │                   │ {prompt, models}  │                   │
       │                   ├──────────────────>│                   │
       │                   │                   │                   │
       │                   │                   │ ┌───────────────┐ │
       │                   │                   │ │   Parallel    │ │
       │                   │                   │ │  Generation   │ │
       │                   │                   │ ├───────────────┤ │
       │                   │                   │ │ Model A ──────┼─┤
       │                   │                   │ │ Model B ──────┼─┤
       │                   │                   │ │ Model C ──────┼─┤
       │                   │                   │ └───────────────┘ │
       │                   │                   │<──────────────────┤
       │                   │<──────────────────┤                   │
       │                   │  {responses: [...]}│                  │
       │                   │                   │                   │
       │<──────────────────┤                   │                   │
       │  Side-by-side     │                   │                   │
       │  comparison       │                   │                   │
```

### Streaming Response Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │     │   Frontend  │     │   Backend   │     │    Model    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │  Send message     │                   │                   │
       ├──────────────────>│                   │                   │
       │                   │                   │                   │
       │                   │ POST /api/stream  │                   │
       │                   │ (SSE connection)  │                   │
       │                   ├──────────────────>│                   │
       │                   │                   │                   │
       │                   │                   │  stream_generate()│
       │                   │                   ├──────────────────>│
       │                   │                   │                   │
       │                   │  data: chunk1     │<──────────────────┤
       │<──────────────────┼<──────────────────┤                   │
       │                   │                   │                   │
       │                   │  data: chunk2     │<──────────────────┤
       │<──────────────────┼<──────────────────┤                   │
       │                   │                   │                   │
       │                   │  data: chunk3     │<──────────────────┤
       │<──────────────────┼<──────────────────┤                   │
       │                   │                   │                   │
       │  Real-time typing │  data: [DONE]     │                   │
       │  effect!          │                   │                   │
```



### Prerequisites

- Python 3.10+
- Node.js 24+ (use [fnm](https://github.com/Schniz/fnm) for version management)
- `GEMINI_API_KEY` (or other model provider API key)

### Run with DevUI (Recommended)

```bash
# Set your API key
export GEMINI_API_KEY="your-api-key"

# Run with Genkit DevUI
./run.sh dev
```

This starts:
- **DevUI**: http://localhost:4000 (test flows and prompts)
- **API**: http://localhost:8080

### Run Backend Only

```bash
# Default: Robyn (fast Rust-based server)
./run.sh backend

# Or use FastAPI
./run.sh backend --framework fastapi
```

### Run with Different Frameworks

The backend supports two web frameworks:

| Framework | Command | Description |
|-----------|---------|-------------|
| **Robyn** (default) | `./run.sh start` | Fast Rust-based async server |
| **FastAPI** | `./run.sh start --framework fastapi` | Industry-standard Python framework |

You can use `--framework` with any backend command:
- `./run.sh start --framework fastapi` - Full stack with FastAPI
- `./run.sh dev --framework fastapi` - DevUI mode with FastAPI
- `./run.sh backend --framework fastapi` - Backend only with FastAPI

### Run Frontend Only

```bash
./run.sh frontend
```

Frontend runs at http://localhost:4200

## Project Structure

```
genkit-chat/
├── backend/
│   ├── src/
│   │   └── main.py          # Genkit flows, tools, Robyn/FastAPI server
│   ├── prompts/             # Dotprompt files
│   │   ├── chat.prompt
│   │   ├── describe_image.prompt
│   │   ├── rag.prompt
│   │   └── compare.prompt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── features/
│   │   │   │   ├── chat/    # Main chat component
│   │   │   │   ├── compare/ # Model comparison
│   │   │   │   └── settings/
│   │   │   └── core/
│   │   │       └── services/
│   │   │           ├── chat.service.ts
│   │   │           ├── models.service.ts
│   │   │           ├── speech.service.ts
│   │   │           └── theme.service.ts
│   │   └── styles.scss
│   ├── angular.json
│   └── package.json
├── run.sh                   # Cross-platform run script
├── Containerfile            # Podman/Docker build
├── docker-compose.yml       # Local development with Ollama
└── README.md
```

## Testing in DevUI

All flows are registered with Genkit and testable in the DevUI:

### chat_flow
```json
{"message": "Hello!", "model": "googleai/gemini-3-flash-preview"}
```

### compare_flow
```json
{
  "prompt": "Explain quantum computing",
  "models": ["googleai/gemini-3-flash-preview", "ollama/llama3.2"]
}
```

### describe_image_flow
```json
{
  "image_url": "https://example.com/image.jpg",
  "question": "What's in this image?"
}
```

### rag_flow
```json
{"query": "What is Genkit?", "collection": "documents"}
```

## Container Build

### Build with Podman

```bash
./run.sh container
# or
podman build -t genkit-chat:latest -f Containerfile .
```

### Run Container

```bash
podman run -p 8080:8080 \
  -e GEMINI_API_KEY="your-key" \
  genkit-chat:latest
```

## Deploy to Cloud Run

```bash
./run.sh deploy
# or
gcloud run deploy genkit-chat \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="your-key"
```

## Local Development with Ollama

For fully offline development:

```bash
# Start Ollama
ollama serve

# Pull models
ollama pull llama3.2
ollama pull mistral

# Run with Docker Compose (includes Ollama)
docker-compose up
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Gemini API key (preferred) |
| `GOOGLE_GENAI_API_KEY` | No | Legacy fallback for Gemini API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `OLLAMA_HOST` | No | Ollama server (default: localhost:11434) |
| `PORT` | No | Server port (default: 8080) |

*At least one model provider is required.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List available models |
| POST | `/api/chat` | Send chat message |
| POST | `/api/compare` | Compare multiple models |
| POST | `/api/images/describe` | Describe an image |
| POST | `/api/rag` | RAG query with ChromaDB |

## Debugging

### Testing with curl

Test the backend API directly with curl to debug issues:

```bash
# List available models
curl -s http://localhost:8080/api/models | jq

# Check API configuration
curl -s http://localhost:8080/api/config | jq

# Test chat endpoint with Gemini
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Tell me a joke.",
    "model": "googleai/gemini-3-flash-preview",
    "history": []
  }' | jq

# Test chat with Ollama (local)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 2+2?",
    "model": "ollama/llama3.2",
    "history": []
  }' | jq

# Test model comparison
curl -X POST http://localhost:8080/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in one sentence",
    "models": ["googleai/gemini-3-flash-preview", "ollama/llama3.2"]
  }' | jq
```

### Common Issues

**429 RESOURCE_EXHAUSTED**: API quota exceeded - wait a moment or use a different model

**Model not found (404)**: Pull the Ollama model first:
```bash
ollama pull llama3.2
ollama pull gemma3
```

**Tool validation error**: Check that tools are defined with Pydantic models (not primitive types)

**Frontend not connecting**: Ensure proxy config in `angular.json` points to port 8080

### Viewing Backend Logs

Run the backend directly to see detailed error logs:

```bash
cd backend
uv run python src/main.py
```

## License

Apache 2.0 - See [LICENSE](../../../LICENSE) for details.
