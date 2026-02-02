# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Genkit Chat Backend - Multi-model AI chat server.

A production-ready full-stack chat application demonstrating all Python Genkit
features including flows, tools, prompts, streaming, and RAG.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Flow                │ A function the AI can run. Like a recipe that      │
    │                     │ says "take this input, do AI magic, return output".│
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Tool                │ A function the AI can call. Like giving the AI     │
    │                     │ a calculator or search engine to use.              │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Prompt              │ A template for talking to the AI. Like a form      │
    │                     │ letter with blanks to fill in.                     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Model               │ The AI brain (Gemini, Claude, GPT). Each thinks    │
    │                     │ differently, like different people solving puzzles.│
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ RAG                 │ "Retrieval-Augmented Generation" - the AI first    │
    │                     │ searches your docs, then answers using what it     │
    │                     │ found. Like reading before answering questions.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Getting the response word-by-word as it's made.    │
    │                     │ Feels faster, like watching someone type.          │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    User Request (Frontend)
         │
         ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │ Robyn API   │ ──▶ │ Genkit Flow │ ──▶ │ Model       │
    │ (port 8080) │     │ (chat_flow) │     │ (Gemini/etc)│
    └─────────────┘     └─────────────┘     └─────────────┘
                              │                   │
                              ▼                   │
                        ┌─────────────┐           │
                        │   Tools     │ ◀─────────┘
                        │ (optional)  │   (model may call tools)
                        └─────────────┘
                              │
                              ▼
                        ┌─────────────┐
                        │  Response   │ ──▶ Frontend
                        └─────────────┘

Architecture::

    ┌─────────────────────────────────────────────────────────────────────┐
    │                     Genkit Reflection Server                        │
    │                     (DevUI at localhost:4000)                       │
    └───────────────────────────────┬─────────────────────────────────────┘
                                    │
    ┌───────────────────────────────▼─────────────────────────────────────┐
    │                        Robyn HTTP Server                            │
    │                        (API at localhost:8080)                      │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Flows (registered with Genkit)                                     │
    │  ├── chat_flow         - Single model chat                          │
    │  ├── compare_flow      - Multi-model comparison                     │
    │  ├── describe_image_flow - Image description with vision            │
    │  └── rag_flow          - RAG with ChromaDB                          │
    │                                                                     │
    │  Tools (callable by models)                                         │
    │  ├── web_search        - Search the web                             │
    │  ├── get_weather       - Get weather info                           │
    │  └── calculate         - Math calculations                          │
    │                                                                     │
    │  Prompts (loaded from prompts/)                                     │
    │  ├── chat.prompt       - Main chat prompt                           │
    │  ├── compare.prompt    - Comparison prompt                          │
    │  └── describe.prompt   - Image description prompt                   │
    └─────────────────────────────────────────────────────────────────────┘

Testing with curl::

    # Test chat endpoint
    curl -X POST http://localhost:8080/api/chat \\
      -H "Content-Type: application/json" \\
      -d '{"message": "Hello!", "model": "googleai/gemini-3-flash-preview"}'

    # Test model comparison
    curl -X POST http://localhost:8080/api/compare \\
      -H "Content-Type: application/json" \\
      -d '{"prompt": "Tell me a joke", "models": ["ollama/llama3.2"]}'

Usage:
    # Run with DevUI (recommended for development)
    genkit start -- python src/main.py

    # Or run standalone
    python src/main.py
"""


from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from genkit import Genkit

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
STATIC_DIR = BASE_DIR / "static"


# =============================================================================
# Plugin Loading
# =============================================================================


def load_plugins() -> list[Any]:
    """Load plugins based on available API keys."""
    plugins = []

    # Google AI (check both GEMINI_API_KEY and legacy GOOGLE_GENAI_API_KEY)
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
    if gemini_api_key:
        try:
            from genkit.plugins.google_genai import GoogleAI

            plugins.append(GoogleAI())
            logger.info("✓ Loaded Google AI plugin")
        except ImportError:
            logger.warning("Google AI plugin not installed")

    # Ollama (local models)
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        from genkit.plugins.ollama import Ollama

        plugins.append(Ollama(server_address=ollama_host))
        logger.info(f"✓ Loaded Ollama plugin ({ollama_host})")
    except ImportError:
        logger.debug("Ollama plugin not installed")

    # ChromaDB (local vector store)
    try:
        from genkit.plugins.chroma import Chroma

        plugins.append(Chroma())
        logger.info("✓ Loaded ChromaDB plugin")
    except ImportError:
        logger.debug("ChromaDB plugin not installed")

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from genkit.plugins.anthropic import Anthropic

            plugins.append(Anthropic())
            logger.info("✓ Loaded Anthropic plugin")
        except ImportError:
            pass

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            from genkit.plugins.openai import OpenAI

            plugins.append(OpenAI())
            logger.info("✓ Loaded OpenAI plugin")
        except ImportError:
            pass

    return plugins


# =============================================================================
# Initialize Genkit
# =============================================================================

g = Genkit(plugins=load_plugins())

# Note: Prompts in backend/prompts/ are automatically discovered by Genkit


# =============================================================================
# Input/Output Schemas
# =============================================================================


class ChatInput(BaseModel):
    """Input for chat flow."""

    message: str = Field(..., description="User's message")
    model: str = Field(
        "googleai/gemini-2.0-flash", description="Model to use for generation"
    )
    history: list[dict[str, str]] = Field(
        default_factory=list, description="Conversation history"
    )


class ChatOutput(BaseModel):
    """Output from chat flow."""

    response: str = Field(..., description="Model's response")
    model: str = Field(..., description="Model used")
    latency_ms: int = Field(..., description="Response time in ms")


class CompareInput(BaseModel):
    """Input for model comparison flow."""

    prompt: str = Field(..., description="Prompt to send to all models")
    models: list[str] = Field(
        default_factory=lambda: [
            "googleai/gemini-2.0-flash",
            "ollama/llama3.2",
        ],
        description="Models to compare",
    )


class CompareOutput(BaseModel):
    """Output from comparison flow."""

    prompt: str = Field(..., description="Original prompt")
    responses: list[dict[str, Any]] = Field(..., description="Model responses")


class ImageDescribeInput(BaseModel):
    """Input for image description flow."""

    image_url: str = Field(..., description="Image URL or data URL")
    question: str = Field(
        "Describe this image in detail.", description="Question about the image"
    )
    model: str = Field(
        "googleai/gemini-2.0-flash", description="Vision model to use"
    )


class ImageDescribeOutput(BaseModel):
    """Output from image description flow."""

    description: str = Field(..., description="Image description")
    model: str = Field(..., description="Model used")


class RAGInput(BaseModel):
    """Input for RAG flow."""

    query: str = Field(..., description="User's question")
    collection: str = Field("documents", description="ChromaDB collection name")


class RAGOutput(BaseModel):
    """Output from RAG flow."""

    answer: str = Field(..., description="Generated answer")
    sources: list[str] = Field(..., description="Source documents used")


# =============================================================================
# Tool Input Models
# =============================================================================


class WebSearchInput(BaseModel):
    """Web search input schema."""

    query: str = Field(description="Search query")


class WeatherInput(BaseModel):
    """Weather lookup input schema."""

    location: str = Field(description="City and state/country, e.g. San Francisco, CA")


class CalculateInput(BaseModel):
    """Calculator input schema."""

    expression: str = Field(description="Mathematical expression to evaluate")


# =============================================================================
# Tools (Callable by Models)
# =============================================================================


@g.tool(description="Search the web for current information")
async def web_search(input: WebSearchInput) -> str:
    """Simulate web search (replace with real API in production)."""
    # In production, integrate with a real search API
    return f"[Web search results for '{input.query}']: This is simulated search data."


@g.tool(description="Get current weather for a location")
async def get_weather(input: WeatherInput) -> str:
    """Simulate weather lookup (replace with real API in production)."""
    # In production, integrate with a weather API
    return f"Weather in {input.location}: Sunny, 72°F (22°C)"


@g.tool(description="Perform mathematical calculations")
async def calculate(input: CalculateInput) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        # Only allow safe math operations
        allowed_chars = set("0123456789+-*/.(). ")
        if not all(c in allowed_chars for c in input.expression):
            return "Error: Invalid characters in expression"
        result = eval(input.expression)  # noqa: S307 - controlled input
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@g.tool(description="Get the current date and time")
async def get_current_time() -> str:
    """Return the current date and time."""
    from datetime import datetime

    return datetime.now().isoformat()


# =============================================================================
# Flows (Testable in DevUI)
# =============================================================================


@g.flow()
async def chat_flow(input: ChatInput) -> ChatOutput:
    """Main chat flow - generates a response to user message.

    This flow:
    1. Builds conversation history from input
    2. Generates response using specified model
    3. Supports tool calling if model requests it

    Test in DevUI with:
        {"message": "Hello, how are you?", "model": "googleai/gemini-2.0-flash"}
    """
    import time

    start_time = time.time()

    # Build messages from history
    messages = []
    for msg in input.history:
        role = msg.get("role", "user")
        if role == "assistant":
            role = "model"
            
        messages.append({
            "role": role,
            "content": [{"text": msg.get("content", "")}],
        })

    # Generate response
    # Note: Tools are disabled for now as some models (e.g., small Ollama models)
    # send malformed tool inputs. Enable for models known to support tools well.
    response = await g.generate(
        model=input.model,
        prompt=input.message,
        messages=messages,
        # tools=['web_search', 'get_weather', 'calculate', 'get_current_time'],
    )

    latency_ms = int((time.time() - start_time) * 1000)

    return ChatOutput(
        response=response.text,
        model=input.model,
        latency_ms=latency_ms,
    )


@g.flow()
async def compare_flow(input: CompareInput) -> CompareOutput:
    """Compare responses from multiple models side-by-side.

    This flow runs the same prompt against multiple models in parallel
    and returns all responses for comparison.

    Test in DevUI with:
        {"prompt": "Explain quantum computing in one sentence",
         "models": ["googleai/gemini-2.0-flash", "ollama/llama3.2"]}
    """
    import time

    async def generate_for_model(model_id: str) -> dict[str, Any]:
        try:
            start_time = time.time()
            response = await g.generate(model=model_id, prompt=input.prompt)
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "model": model_id,
                "response": response.text,
                "latency_ms": latency_ms,
                "error": None,
            }
        except Exception as e:
            return {
                "model": model_id,
                "response": None,
                "latency_ms": 0,
                "error": str(e),
            }

    # Run all models in parallel
    responses = await asyncio.gather(
        *[generate_for_model(m) for m in input.models]
    )

    return CompareOutput(prompt=input.prompt, responses=list(responses))


@g.flow()
async def describe_image_flow(input: ImageDescribeInput) -> ImageDescribeOutput:
    """Describe an image using a vision-capable model.

    This flow demonstrates multimodal input with images.

    Test in DevUI with:
        {"image_url": "https://example.com/image.jpg",
         "question": "What's in this image?"}
    """
    response = await g.generate(
        model=input.model,
        prompt=[
            {"media": {"url": input.image_url}},
            {"text": input.question},
        ],
    )

    return ImageDescribeOutput(
        description=response.text,
        model=input.model,
    )


@g.flow()
async def rag_flow(input: RAGInput) -> RAGOutput:
    """RAG flow - Answer questions using retrieved documents.

    This flow demonstrates:
    1. Embedding the query
    2. Retrieving relevant documents from ChromaDB
    3. Generating answer with context

    Test in DevUI with:
        {"query": "What is Genkit?", "collection": "documents"}
    """
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(BASE_DIR / "chroma_data"))

        try:
            collection = client.get_collection(input.collection)
        except ValueError:
            # Collection doesn't exist, create with sample data
            collection = client.create_collection(input.collection)
            collection.add(
                documents=[
                    "Genkit is an AI orchestration framework by Google.",
                    "Genkit supports multiple model providers including Google AI, OpenAI, and Anthropic.",
                    "Genkit provides a DevUI for testing flows and prompts.",
                ],
                ids=["doc1", "doc2", "doc3"],
            )

        # Query the collection
        results = collection.query(query_texts=[input.query], n_results=3)

        sources = results["documents"][0] if results["documents"] else []

        # Generate answer with context
        context = "\n".join(sources)
        response = await g.generate(
            model="googleai/gemini-2.0-flash",
            prompt=f"""Answer the question based on the following context.
            
Context:
{context}

Question: {input.query}

Answer:""",
        )

        return RAGOutput(answer=response.text, sources=sources)

    except ImportError:
        return RAGOutput(
            answer="ChromaDB not installed. Install with: pip install chromadb",
            sources=[],
        )


# =============================================================================
# Streaming Flow
# =============================================================================


@g.flow()
async def stream_chat_flow(input: ChatInput) -> ChatOutput:
    """Streaming chat flow - generates response with real-time chunks.

    This demonstrates Genkit's streaming capabilities.
    Note: In the DevUI, streaming shows the final result.

    For real-time streaming, use the HTTP SSE endpoint.
    """
    import time

    start_time = time.time()
    full_response = ""

    async for chunk in g.generate_stream(
        model=input.model,
        prompt=input.message,
    ):
        if chunk.text:
            full_response += chunk.text

    latency_ms = int((time.time() - start_time) * 1000)

    return ChatOutput(
        response=full_response,
        model=input.model,
        latency_ms=latency_ms,
    )


# =============================================================================
# Robyn HTTP Server (for Angular frontend)
# =============================================================================


def create_http_server():
    """Create the Robyn HTTP server for the Angular frontend."""
    from robyn import Request, Response, Robyn
    from robyn.robyn import Headers

    # Disable OpenAPI by passing None to avoid schema generation issues
    app = Robyn(__file__, openapi=None)

    @app.before_request()
    async def cors_preflight(request: Request):
        if request.method == "OPTIONS":
            return Response(
                status_code=204,
                headers=Headers({
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                }),
                description="",
            )
        return request

    @app.after_request()
    async def add_cors(response: Response):
        response.headers.set("Access-Control-Allow-Origin", "*")
        return response

    @app.get("/")
    async def health(request: Request):
        return {"status": "healthy", "service": "genkit-chat"}

    @app.get("/api/config")
    async def get_config(request: Request):
        """Return configuration status (which API keys are set)."""

        def mask_key(key: str | None) -> dict:
            """Return masked key info."""
            if not key:
                return {"configured": False, "preview": None}
            # Show first 4 and last 4 chars
            if len(key) > 12:
                preview = f"{key[:4]}...{key[-4:]}"
            else:
                preview = "****"
            return {"configured": True, "preview": preview}

        # Check GEMINI_API_KEY first (preferred), then legacy GOOGLE_GENAI_API_KEY
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
        
        return {
            "api_keys": {
                "GEMINI_API_KEY": mask_key(gemini_key),
                "ANTHROPIC_API_KEY": mask_key(os.getenv("ANTHROPIC_API_KEY")),
                "OPENAI_API_KEY": mask_key(os.getenv("OPENAI_API_KEY")),
                "OLLAMA_HOST": {
                    "configured": True,
                    "preview": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                },
            },
            "features": {
                "rag_enabled": True,
                "streaming_enabled": True,
                "tools_enabled": True,
            },
        }

    @app.get("/api/models")
    async def list_models(request: Request):
        """Return available models grouped by provider."""
        from genkit_setup import get_available_models

        # Return providers array directly (frontend expects this format)
        return await get_available_models()

    @app.post("/api/chat")
    async def api_chat(request: Request):
        """Call the chat flow via HTTP."""
        try:
            body = json.loads(request.body)
            logger.info(f"Chat request: model={body.get('model')}, message_len={len(body.get('message', ''))}")
            result = await chat_flow(ChatInput(**body))
            return result.model_dump()
        except Exception as e:
            logger.exception(f"Chat error: {e}")
            return Response(
                status_code=500,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(e), "type": type(e).__name__}),
            )

    @app.post("/api/compare")
    async def api_compare(request: Request):
        """Call the compare flow via HTTP."""
        body = json.loads(request.body)
        result = await compare_flow(CompareInput(**body))
        return result.model_dump()

    @app.post("/api/images/describe")
    async def api_describe(request: Request):
        """Call the describe image flow via HTTP."""
        body = json.loads(request.body)
        result = await describe_image_flow(ImageDescribeInput(**body))
        return result.model_dump()

    @app.post("/api/rag")
    async def api_rag(request: Request):
        """Call the RAG flow via HTTP."""
        body = json.loads(request.body)
        result = await rag_flow(RAGInput(**body))
        return result.model_dump()

    # Serve static files if they exist
    if STATIC_DIR.exists():
        app.serve_directory(
            route="/",
            directory_path=str(STATIC_DIR),
            index_file="index.html",
        )

    return app


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the Genkit chat server."""
    port = int(os.getenv("PORT", "8080"))

    logger.info("=" * 60)
    logger.info("Genkit Chat Server")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Available Flows (test in DevUI at http://localhost:4000):")
    logger.info("  - chat_flow: Single model chat with tools")
    logger.info("  - compare_flow: Multi-model comparison")
    logger.info("  - describe_image_flow: Image description with vision")
    logger.info("  - rag_flow: RAG with ChromaDB")
    logger.info("  - stream_chat_flow: Streaming chat")
    logger.info("")
    logger.info(f"HTTP API: http://localhost:{port}")
    logger.info("")
    logger.info("Run with: genkit start -- python src/main.py")
    logger.info("=" * 60)

    # Create and start HTTP server (blocking)
    app = create_http_server()
    app.start(port=port)


if __name__ == "__main__":
    main()
