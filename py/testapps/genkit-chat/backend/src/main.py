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
    │              HTTP Server (--framework robyn|fastapi)                │
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

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from robyn import Request, Response, Robyn
from robyn.robyn import Headers

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




def load_plugins() -> list[Any]:
    """Load plugins based on available API keys."""
    plugins = []

    # Google AI (check both GEMINI_API_KEY and legacy GOOGLE_GENAI_API_KEY)
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
    if gemini_api_key:
        try:
            from genkit.plugins.google_genai import GoogleAI  # type: ignore[import-not-found]

            plugins.append(GoogleAI())
            logger.info("✓ Loaded Google AI plugin")
        except ImportError:
            logger.warning("Google AI plugin not installed")

    # Ollama (local models)
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        from genkit.plugins.ollama import Ollama  # type: ignore[import-not-found]

        plugins.append(Ollama(server_address=ollama_host))
        logger.info(f"✓ Loaded Ollama plugin ({ollama_host})")
    except ImportError:
        logger.debug("Ollama plugin not installed")

    # Dev Local VectorStore
    try:
        from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore  # type: ignore[import-not-found]

        plugins.append(DevLocalVectorStore())
        logger.info("✓ Loaded DevLocalVectorStore plugin")
    except ImportError:
        logger.debug("DevLocalVectorStore plugin not installed")

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from genkit.plugins.anthropic import Anthropic  # type: ignore[import-not-found]

            plugins.append(Anthropic())
            logger.info("✓ Loaded Anthropic plugin")
        except ImportError:
            pass

    # OpenAI (via compat-oai)
    if os.getenv("OPENAI_API_KEY"):
        try:
            from genkit.plugins.compat_oai import OpenAICompat  # type: ignore[import-not-found]

            plugins.append(OpenAICompat())
            logger.info("✓ Loaded OpenAI-compatible plugin")
        except ImportError:
            pass

    return plugins



async def get_available_models() -> list[dict[str, Any]]:
    """Get available models grouped by provider.

    Returns:
        List of provider info with their available models.
    """
    providers = []

    # Google AI models
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY"):
        providers.append({
            "id": "google-genai",
            "name": "Google AI",
            "available": True,
            "models": [
                {
                    "id": "googleai/gemini-3-flash-preview",
                    "name": "Gemini 3 Flash Preview",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 1000000,
                },
                {
                    "id": "googleai/gemini-3-pro-preview",
                    "name": "Gemini 3 Pro Preview",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 2000000,
                },
                {
                    "id": "googleai/gemini-3-flash-preview",
                    "name": "Gemini 2.0 Flash",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 1000000,
                },
            ],
        })

    # Anthropic models
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append({
            "id": "anthropic",
            "name": "Anthropic",
            "available": True,
            "models": [
                {
                    "id": "anthropic/claude-sonnet-4-20250514",
                    "name": "Claude Sonnet 4",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 200000,
                },
                {
                    "id": "anthropic/claude-opus-4-20250514",
                    "name": "Claude Opus 4",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 200000,
                },
                {
                    "id": "anthropic/claude-3-7-sonnet",
                    "name": "Claude 3.7 Sonnet",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 200000,
                },
            ],
        })

    # OpenAI models
    if os.getenv("OPENAI_API_KEY"):
        providers.append({
            "id": "openai",
            "name": "OpenAI",
            "available": True,
            "models": [
                {
                    "id": "openai/gpt-4.1",
                    "name": "GPT-4.1",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 128000,
                },
                {
                    "id": "openai/gpt-4o",
                    "name": "GPT-4o",
                    "capabilities": ["text", "vision", "streaming"],
                    "context_window": 128000,
                },
                {
                    "id": "openai/gpt-4o-mini",
                    "name": "GPT-4o Mini",
                    "capabilities": ["text", "streaming"],
                    "context_window": 128000,
                },
            ],
        })

    # Ollama models (try to detect running server)
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_host}/api/tags", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                ollama_models = [
                    {
                        "id": f"ollama/{model['name']}",
                        "name": model["name"].title(),
                        "capabilities": ["text", "streaming"],
                        "context_window": 4096,  # Default, varies by model
                    }
                    for model in data.get("models", [])
                ]
                if ollama_models:
                    providers.append({
                        "id": "ollama",
                        "name": "Ollama (Local)",
                        "available": True,
                        "models": ollama_models,
                    })
    except Exception:
        # Ollama not running, that's fine
        pass

    return providers


g = Genkit(plugins=load_plugins())

# Note: Prompts in backend/prompts/ are automatically discovered by Genkit




class ChatInput(BaseModel):
    """Input for chat flow."""

    message: str = Field(..., description="User's message")
    model: str = Field(
        "googleai/gemini-3-flash-preview", description="Model to use for generation"
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
            "googleai/gemini-3-flash-preview",
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
        "googleai/gemini-3-flash-preview", description="Vision model to use"
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




class WebSearchInput(BaseModel):
    """Web search input schema."""

    query: str = Field(description="Search query")


class WeatherInput(BaseModel):
    """Weather lookup input schema."""

    location: str = Field(description="City and state/country, e.g. San Francisco, CA")


class CalculateInput(BaseModel):
    """Calculator input schema."""

    expression: str = Field(description="Mathematical expression to evaluate")




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
    return datetime.now().isoformat()




@g.flow()
async def chat_flow(input: ChatInput) -> ChatOutput:
    """Main chat flow - generates a response to user message.

    This flow:
    1. Builds conversation history from input
    2. Generates response using specified model
    3. Supports tool calling if model requests it

    Test in DevUI with:
        {"message": "Hello, how are you?", "model": "googleai/gemini-3-flash-preview"}
    """
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
         "models": ["googleai/gemini-3-flash-preview", "ollama/llama3.2"]}
    """
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
        prompt=[  # type: ignore[arg-type] - multimodal content list
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

    This flow demonstrates a simple RAG pattern with in-memory documents.
    For production, integrate with a real vector store.

    Test in DevUI with:
        {"query": "What is Genkit?", "collection": "documents"}
    """
    # Sample knowledge base (in production, use a real vector store)
    knowledge_base = [
        "Genkit is an AI orchestration framework by Google.",
        "Genkit supports multiple model providers including Google AI, OpenAI, and Anthropic.",
        "Genkit provides a DevUI for testing flows and prompts.",
        "Genkit flows are the main unit of work, representing a function that can be called.",
        "Genkit tools allow models to call external functions to retrieve information.",
    ]

    # Simple keyword-based retrieval (in production, use embeddings)
    query_lower = input.query.lower()
    relevant_docs = [
        doc for doc in knowledge_base
        if any(word in doc.lower() for word in query_lower.split())
    ]

    # If no matches, return all docs as context
    sources = relevant_docs if relevant_docs else knowledge_base[:3]

    # Generate answer with context
    context = "\n".join(sources)
    response = await g.generate(
        model="googleai/gemini-3-flash-preview",
        prompt=f"""Answer the question based on the following context.

Context:
{context}

Question: {input.query}

Answer:""",
    )

    return RAGOutput(answer=response.text, sources=sources)




@g.flow()
async def stream_chat_flow(input: ChatInput) -> ChatOutput:
    """Streaming chat flow - generates response with real-time chunks.

    This demonstrates Genkit's streaming capabilities.
    Note: In the DevUI, streaming shows the final result.

    For real-time streaming, use the HTTP SSE endpoint.
    """
    start_time = time.time()
    full_response = ""

    async for chunk in g.generate_stream(  # type: ignore[union-attr] - async iterator
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




def create_fastapi_server() -> FastAPI:
    """Create the FastAPI HTTP server for the Angular frontend.
    
    This is an alternative to Robyn, demonstrating how Genkit flows
    work equally well with FastAPI.
    """
    app = FastAPI(
        title="Genkit Chat API",
        description="Multi-model AI chat server powered by Genkit",
        version="1.0.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def health():
        return {"status": "healthy", "service": "genkit-chat", "framework": "fastapi"}

    @app.get("/api/config")
    async def get_config():
        """Return configuration status (which API keys are set)."""

        def mask_key(key: str | None) -> dict:
            """Return masked key info."""
            if not key:
                return {"configured": False, "preview": None}
            if len(key) > 12:
                preview = f"{key[:4]}...{key[-4:]}"
            else:
                preview = "****"
            return {"configured": True, "preview": preview}

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
    async def list_models():
        """Return available models grouped by provider."""
        return await get_available_models()

    @app.post("/api/chat")
    async def api_chat(input: ChatInput):
        """Call the chat flow via HTTP."""
        try:
            logger.info(f"Chat request: model={input.model}, message_len={len(input.message)}")
            result = await chat_flow(input)
            return result.model_dump()
        except Exception as e:
            logger.exception(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail={"error": str(e), "type": type(e).__name__}) from e

    @app.post("/api/compare")
    async def api_compare(input: CompareInput):
        """Call the compare flow via HTTP."""
        result = await compare_flow(input)
        return result.model_dump()

    @app.post("/api/images/describe")
    async def api_describe(input: ImageDescribeInput):
        """Call the describe image flow via HTTP."""
        result = await describe_image_flow(input)
        return result.model_dump()

    @app.post("/api/rag")
    async def api_rag(input: RAGInput):
        """Call the RAG flow via HTTP."""
        result = await rag_flow(input)
        return result.model_dump()

    # Serve static files if they exist
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app




def create_http_server() -> Robyn:
    """Create the Robyn HTTP server for the Angular frontend."""
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
        response.headers.set("Access-Control-Allow-Origin", "*")  # type: ignore[attr-defined] - Robyn Headers
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
        # Return providers array directly (frontend expects this format)
        # Use Response with explicit JSON for list serialization in Robyn
        providers = await get_available_models()
        return Response(
            status_code=200,
            headers=Headers({"Content-Type": "application/json"}),
            description=json.dumps(providers),
        )

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




def main() -> None:
    """Run the Genkit chat server.
    
    Supports both Robyn (default) and FastAPI frameworks via --framework flag.
    """
    parser = argparse.ArgumentParser(description="Genkit Chat Server")
    parser.add_argument(
        "--framework",
        choices=["robyn", "fastapi"],
        default="robyn",
        help="Web framework to use (default: robyn)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port to run on (default: 8080 or PORT env var)",
    )
    args = parser.parse_args()

    port = args.port

    logger.info("=" * 60)
    logger.info(f"Genkit Chat Server ({args.framework.upper()})")
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
    logger.info("Run with: genkit start -- python src/main.py [--framework robyn|fastapi]")
    logger.info("=" * 60)

    if args.framework == "fastapi":
        app = create_fastapi_server()
        uvicorn.run(app, host="0.0.0.0", port=port, loop="uvloop")
    else:
        # Default: Robyn
        app = create_http_server()
        app.start(port=port)


if __name__ == "__main__":
    main()
