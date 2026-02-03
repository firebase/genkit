# Genkit Chat Roadmap

This document tracks implemented and planned features for the Genkit Chat testapp.

## Overview

Genkit Chat is a full-stack AI chat application that demonstrates the capabilities
of the Genkit Python SDK. It serves as both a reference implementation and a
testing ground for Genkit features.

## Current Status: v0.1.0 (Alpha)

### Implemented Features

#### Backend (Python)

| Feature | Status | Description |
|---------|--------|-------------|
| Multi-Framework Support | ✅ Done | Supports both Robyn and FastAPI |
| Google AI Integration | ✅ Done | Gemini 3 models via genkit-plugin-google-genai |
| Anthropic Integration | ✅ Done | Claude models via genkit-plugin-anthropic |
| OpenAI Integration | ✅ Done | GPT models via genkit-plugin-compat-oai |
| Ollama Integration | ✅ Done | Local models via genkit-plugin-ollama |
| Chat Flow | ✅ Done | Single model chat with streaming |
| Compare Flow | ✅ Done | Multi-model comparison |
| Image Description Flow | ✅ Done | Vision model support |
| RAG Flow | ✅ Done | Basic in-memory retrieval |
| Tool Integration | ✅ Done | Web search, weather, calculator tools |
| Streaming Response | ✅ Done | Server-Sent Events (SSE) |
| CORS Support | ✅ Done | Cross-origin requests enabled |
| Health Check API | ✅ Done | `/` endpoint |
| Config API | ✅ Done | `/api/config` - masked API key status |
| Models API | ✅ Done | `/api/models` - available providers |
| Integration Tests | ✅ Done | Tests for both frameworks |
| Type Checking | ✅ Done | Pyright configuration |
| Linting | ✅ Done | Ruff configuration |

#### Frontend (Angular)

| Feature | Status | Description |
|---------|--------|-------------|
| Angular 19 | ✅ Done | Latest Angular version |
| Material Design | ✅ Done | Angular Material components |
| Chat Interface | ✅ Done | Message display with markdown |
| Model Selection | ✅ Done | Dynamic model dropdown |
| Multi-Model Compare | ✅ Done | Side-by-side comparison |
| Dark/Light Theme | ✅ Done | Theme toggle |
| Responsive Layout | ✅ Done | Mobile-friendly |
| Session Management | ✅ Done | Chat history |

#### DevOps

| Feature | Status | Description |
|---------|--------|-------------|
| run.sh | ✅ Done | Unix/macOS runner script |
| run.bat | ✅ Done | Windows runner script |
| Lint/Test Commands | ✅ Done | `./run.sh lint` and `./run.sh test` |
| Podman Support | ✅ Done | Container build support |
| Cloud Run Deploy | ✅ Done | GCP deployment |
| Genkit DevUI | ✅ Done | Development UI integration |

### Recently Completed

| Feature | Description |
|---------|-------------|
| Auto-Focus Chat Input | Focus on welcome screen and after new chat |
| run.bat | Windows equivalent of run.sh |
| Lint Commands | `./run.sh lint` runs ruff + pyright |
| Test Commands | `./run.sh test` runs pytest |
| Markdown Rendering | Safe markdown with DOMPurify, toggle in toolbar |
| Mermaid Diagrams | Render diagrams in chat responses |
| Math Equations | LaTeX-style math rendering |
| Content Safety | TensorFlow.js toxicity detection (client-side) |
| Strict CSP | Angular autoCsp for production builds |
| Prompt Queue | Queue prompts while model is busy |
| Drag & Drop Queue | Reorder queued prompts |
| Playwright E2E Tests | Browser automation testing |

### Known Issues / Incomplete Features

| Issue | Priority | Description |
|-------|----------|-------------|
| **File Attachments Not Sent** | 🔴 High | UI allows attaching files (stored in `attachedFiles` signal) but `sendMessage()` does not include them in the payload. Backend API needs to be updated to handle multimodal input. See `chat.component.ts` TODO comment. |

### Planned Features

#### Backend Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Multimodal Chat API** | 🔴 High | Update `/api/chat` to accept text + image attachments |
| **Shareable Chats** | 🔴 High | Share conversations via URL |
| **libSQL Integration** | 🔴 High | SQLite-compatible Rust DB for persistence |
| Vector Store Integration | 🟡 Medium | ChromaDB or Pinecone for real RAG |
| Conversation History | 🟡 Medium | Persistent chat context |
| Rate Limiting | 🟡 Medium | API request throttling |
| Authentication | 🟡 Medium | Optional API key auth |
| WebSocket Support | 🟢 Low | Alternative to SSE streaming |
| Metrics/Telemetry | 🟢 Low | OpenTelemetry integration |
| Session Persistence | 🟢 Low | Database-backed sessions |

#### Frontend Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| **Complete File Attachment Flow** | 🔴 High | Send attachedFiles with messages, display in history, clear after send |
| **Image Recognition** | 🔴 High | Google Lens-like image analysis |
| **Drag & Drop Attachments** | 🔴 High | Drop zone in chatbox for files |
| **IndexedDB Persistence** | 🔴 High | Dexie.js for frontend chat storage |
| File Upload | 🟡 Medium | Image/document upload for vision |
| Code Highlighting | 🟡 Medium | Syntax highlighting in responses |
| Export Chat | 🟡 Medium | Download conversation as JSON/MD |
| Voice Input | 🟢 Low | Speech-to-text |
| Voice Output | 🟢 Low | Text-to-speech |
| Prompt Templates | 🟢 Low | Pre-defined prompts |
| Token Counter | 🟢 Low | Usage tracking |

#### DevOps Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| Docker Support | 🟡 Medium | Docker Compose setup |
| CI/CD Pipeline | 🟡 Medium | GitHub Actions workflow |
| Kubernetes Manifests | 🟢 Low | K8s deployment configs |
| AWS Deploy | 🟢 Low | Lambda/ECS deployment |
| Azure Deploy | 🟢 Low | Azure deployment |

## Version History

### v0.1.0 (Current)

* Initial release
* Multi-framework backend (Robyn + FastAPI)
* Multi-provider support (Google AI, Anthropic, OpenAI, Ollama)
* Angular 19 frontend with Material Design
* Basic chat, compare, and RAG flows
* Integration tests for both frameworks

## Contributing

When adding new features:

1. Update this roadmap with the feature status
2. Add integration tests if applicable
3. Update the README with usage instructions
4. Ensure lint/type checks pass

## Testing the Roadmap Features

```bash
# Run backend tests
cd backend && uv run --group test pytest tests/ -v

# Run lint checks
./run.sh lint

# Start with DevUI for testing
./run.sh dev --framework fastapi
```
