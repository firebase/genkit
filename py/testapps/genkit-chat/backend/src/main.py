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
import ast
import asyncio
import json
import logging
import operator
import os
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from robyn import Request, Response, Robyn, SSEMessage, SSEResponse
from robyn.robyn import Headers

from genkit import GenerateResponseWrapper, Genkit
from genkit.types import MediaPart

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG') else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / 'prompts'
STATIC_DIR = BASE_DIR / 'static'


# Import shared functions from genkit_setup to avoid duplication
# Add src directory to path for when running from backend directory
import sys  # noqa: E402 - must be before sys.path manipulation

SRC_DIR = BASE_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from genkit_setup import (  # noqa: E402
    _load_plugins as load_plugins,
    get_available_models,
)

g = Genkit(plugins=load_plugins())

# Note: Prompts in backend/prompts/ are automatically discovered by Genkit


def format_response_content(response: GenerateResponseWrapper[object]) -> str:
    """Format response content including text and images.

    This function extracts all parts from a model response and formats them
    appropriately for the frontend:
    - Text parts are included as-is
    - Media parts (images) are converted to markdown image syntax

    Args:
        response: The GenerateResponseWrapper from g.generate()

    Returns:
        Formatted string with text and markdown image syntax
    """
    parts = []

    # First try to get text - this works for text-only responses
    if response.text:
        parts.append(response.text)

    # Check for media parts in the message content
    if response.message and response.message.content:
        for part in response.message.content:
            if isinstance(part.root, MediaPart):
                media = part.root.media
                if media and media.url:
                    # Format as markdown image
                    alt_text = 'Generated image'
                    parts.append(f'\n\n![{alt_text}]({media.url})\n')

    # If we only have text from response.text, use that
    # Otherwise join all parts
    if len(parts) == 1:
        return parts[0]
    elif parts:
        return ''.join(parts)
    else:
        return response.text or ''


class ChatInput(BaseModel):
    """Input for chat flow."""

    message: str = Field(..., description="User's message")
    model: str = Field('googleai/gemini-3-flash-preview', description='Model to use for generation')
    history: list[dict[str, str]] = Field(default_factory=list, description='Conversation history')


class ChatOutput(BaseModel):
    """Output from chat flow."""

    response: str = Field(..., description="Model's response")
    model: str = Field(..., description='Model used')
    latency_ms: int = Field(..., description='Response time in ms')


class CompareInput(BaseModel):
    """Input for model comparison flow."""

    prompt: str = Field(..., description='Prompt to send to all models')
    models: list[str] = Field(
        default_factory=lambda: [
            'googleai/gemini-3-flash-preview',
            'ollama/llama3.2',
        ],
        description='Models to compare',
    )


class CompareOutput(BaseModel):
    """Output from comparison flow."""

    prompt: str = Field(..., description='Original prompt')
    responses: list[dict[str, Any]] = Field(..., description='Model responses')


class ImageDescribeInput(BaseModel):
    """Input for image description flow."""

    image_url: str = Field(..., description='Image URL or data URL')
    question: str = Field('Describe this image in detail.', description='Question about the image')
    model: str = Field('googleai/gemini-3-flash-preview', description='Vision model to use')


class ImageDescribeOutput(BaseModel):
    """Output from image description flow."""

    description: str = Field(..., description='Image description')
    model: str = Field(..., description='Model used')


class RAGInput(BaseModel):
    """Input for RAG flow."""

    query: str = Field(..., description="User's question")
    collection: str = Field('documents', description='ChromaDB collection name')


class RAGOutput(BaseModel):
    """Output from RAG flow."""

    answer: str = Field(..., description='Generated answer')
    sources: list[str] = Field(..., description='Source documents used')


class WebSearchInput(BaseModel):
    """Web search input schema."""

    query: str = Field(description='Search query')


class WeatherInput(BaseModel):
    """Weather lookup input schema."""

    location: str = Field(description='City and state/country, e.g. San Francisco, CA')


class CalculateInput(BaseModel):
    """Calculator input schema."""

    expression: str = Field(description='Mathematical expression to evaluate')


@g.tool(description='Search the web for current information')
async def web_search(input: WebSearchInput) -> str:
    """Simulate web search (replace with real API in production)."""
    # In production, integrate with a real search API
    return f"[Web search results for '{input.query}']: This is simulated search data."


@g.tool(description='Get current weather for a location')
async def get_weather(input: WeatherInput) -> str:
    """Simulate weather lookup (replace with real API in production)."""
    # In production, integrate with a weather API
    return f'Weather in {input.location}: Sunny, 72°F (22°C)'


@g.tool(description='Perform mathematical calculations')
async def calculate(input: CalculateInput) -> str:
    """Evaluate a mathematical expression safely using an AST walker.

    This implementation avoids eval() by parsing the expression into an AST
    and evaluating only supported mathematical operations.
    """
    # Binary operators (two operands)
    binary_ops: dict[type, Callable[[Any, Any], Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }
    # Unary operators (one operand)
    unary_ops: dict[type, Callable[[Any], Any]] = {
        ast.USub: operator.neg,
    }

    def eval_expr(node: ast.expr) -> float | int:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int | float):
                return node.value
            raise TypeError(f'Unsupported constant type: {type(node.value).__name__}')
        elif isinstance(node, ast.BinOp):
            left = eval_expr(node.left)
            right = eval_expr(node.right)
            return binary_ops[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = eval_expr(node.operand)
            return unary_ops[type(node.op)](operand)
        else:
            raise TypeError(f'Unsupported node type: {type(node).__name__}')

    try:
        tree = ast.parse(input.expression, mode='eval')
        result = eval_expr(tree.body)
        return f'Result: {result}'
    except (TypeError, SyntaxError, KeyError, ZeroDivisionError) as e:
        return f'Error: Invalid or unsupported expression. {e}'


@g.tool(description='Get the current date and time')
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
        role = msg.get('role', 'user')
        if role == 'assistant':
            role = 'model'

        messages.append({
            'role': role,
            'content': [{'text': msg.get('content', '')}],
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
        response=format_response_content(response),
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
                'model': model_id,
                'response': format_response_content(response),
                'latency_ms': latency_ms,
                'error': None,
            }
        except Exception as e:
            return {
                'model': model_id,
                'response': None,
                'latency_ms': 0,
                'error': str(e),
            }

    # Run all models in parallel
    responses = await asyncio.gather(*[generate_for_model(m) for m in input.models])

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
            {'media': {'url': input.image_url}},
            {'text': input.question},
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
        'Genkit is an AI orchestration framework by Google.',
        'Genkit supports multiple model providers including Google AI, OpenAI, and Anthropic.',
        'Genkit provides a DevUI for testing flows and prompts.',
        'Genkit flows are the main unit of work, representing a function that can be called.',
        'Genkit tools allow models to call external functions to retrieve information.',
    ]

    # Simple keyword-based retrieval (in production, use embeddings)
    query_lower = input.query.lower()
    relevant_docs = [doc for doc in knowledge_base if any(word in doc.lower() for word in query_lower.split())]

    # If no matches, return all docs as context
    sources = relevant_docs if relevant_docs else knowledge_base[:3]

    # Generate answer with context
    context = '\n'.join(sources)
    response = await g.generate(
        model='googleai/gemini-3-flash-preview',
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
    full_response = ''

    # Build messages from history
    messages = []
    for msg in input.history:
        role = msg.get('role', 'user')
        if role == 'assistant':
            role = 'model'
        messages.append({
            'role': role,
            'content': [{'text': msg.get('content', '')}],
        })

    # generate_stream returns (stream, future) tuple
    stream, _ = g.generate_stream(
        model=input.model,
        prompt=input.message,
        messages=messages,
    )
    async for chunk in stream:
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
        title='Genkit Chat API',
        description='Multi-model AI chat server powered by Genkit',
        version='1.0.0',
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type] - FastAPI accepts class not factory
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.get('/')
    async def health():
        return {'status': 'healthy', 'service': 'genkit-chat', 'framework': 'fastapi'}

    @app.get('/api/config')
    async def get_config():
        """Return configuration status (which API keys are set)."""

        def mask_key(key: str | None) -> dict:
            """Return masked key info."""
            if not key:
                return {'configured': False, 'preview': None}
            if len(key) > 12:
                preview = f'{key[:4]}...{key[-4:]}'
            else:
                preview = '****'
            return {'configured': True, 'preview': preview}

        gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_GENAI_API_KEY')

        return {
            'api_keys': {
                'GEMINI_API_KEY': mask_key(gemini_key),
                'ANTHROPIC_API_KEY': mask_key(os.getenv('ANTHROPIC_API_KEY')),
                'OPENAI_API_KEY': mask_key(os.getenv('OPENAI_API_KEY')),
                'OLLAMA_HOST': {
                    'configured': True,
                    'preview': os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
                },
            },
            'features': {
                'rag_enabled': True,
                'streaming_enabled': True,
                'tools_enabled': True,
            },
        }

    @app.get('/api/models')
    async def list_models():
        """Return available models grouped by provider."""
        return await get_available_models()

    @app.post('/api/chat')
    async def api_chat(input: ChatInput):
        """Call the chat flow via HTTP."""
        try:
            logger.info(f'Chat request: model={input.model}, message_len={len(input.message)}')
            result = await chat_flow(input)
            return result.model_dump()
        except Exception as e:
            logger.exception(f'Chat error: {e}')
            raise HTTPException(status_code=500, detail={'error': str(e), 'type': type(e).__name__}) from e

    @app.post('/api/compare')
    async def api_compare(input: CompareInput):
        """Call the compare flow via HTTP."""
        result = await compare_flow(input)
        return result.model_dump()

    @app.post('/api/images/describe')
    async def api_describe(input: ImageDescribeInput):
        """Call the describe image flow via HTTP."""
        result = await describe_image_flow(input)
        return result.model_dump()

    @app.post('/api/rag')
    async def api_rag(input: RAGInput):
        """Call the RAG flow via HTTP."""
        result = await rag_flow(input)
        return result.model_dump()

    @app.get('/api/stream')
    async def api_stream_chat(message: str, model: str, history: str = '[]'):
        """Stream chat response using Server-Sent Events (SSE).

        Uses Genkit's generate_stream for real-time token streaming.
        """

        async def generate():
            try:
                # Parse history and build messages
                messages = []
                if history and history.strip() and history.strip() != '[]':
                    try:
                        history_data = json.loads(history)
                        for msg in history_data:
                            role = msg.get('role', 'user')
                            if role == 'assistant':
                                role = 'model'
                            messages.append({
                                'role': role,
                                'content': [{'text': msg.get('content', '')}],
                            })
                    except json.JSONDecodeError:
                        logger.warning('Failed to parse history JSON')

                # FastAPI automatically handles URL decoding for query parameters
                logger.info(f'Stream request: model={model}, message_len={len(message)}')

                # generate_stream returns (stream, future) tuple
                stream, _ = g.generate_stream(
                    model=model,
                    prompt=message,
                    messages=messages,
                )
                async for chunk in stream:
                    if chunk.text:
                        # Send each chunk as SSE event
                        data = json.dumps({'chunk': chunk.text})
                        yield f'data: {data}\n\n'

                # Signal completion
                yield 'data: [DONE]\n\n'

            except Exception as e:
                logger.exception(f'Stream error: {e}')
                error_data = json.dumps({'error': str(e), 'type': type(e).__name__})
                yield f'data: {error_data}\n\n'
                yield 'data: [DONE]\n\n'

        return StreamingResponse(
            generate(),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    # Serve static files if they exist
    if STATIC_DIR.exists():
        app.mount('/', StaticFiles(directory=str(STATIC_DIR), html=True), name='static')

    return app


def create_http_server() -> Robyn:
    """Create the Robyn HTTP server for the Angular frontend."""
    # Disable OpenAPI by passing None to avoid schema generation issues
    app = Robyn(__file__, openapi=None)

    @app.before_request()
    async def cors_preflight(request: Request):
        if request.method == 'OPTIONS':
            return Response(
                status_code=204,
                headers=Headers({
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                }),
                description='',
            )
        return request

    @app.after_request()
    async def add_cors(response: Response):
        if hasattr(response.headers, 'set'):
            response.headers.set('Access-Control-Allow-Origin', '*')  # type: ignore[misc]
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    @app.get('/')
    async def health(request: Request):
        return {'status': 'healthy', 'service': 'genkit-chat', 'framework': 'robyn'}

    @app.get('/api/config')
    async def get_config(request: Request):
        """Return configuration status (which API keys are set)."""

        def mask_key(key: str | None) -> dict:
            """Return masked key info."""
            if not key:
                return {'configured': False, 'preview': None}
            # Show first 4 and last 4 chars
            if len(key) > 12:
                preview = f'{key[:4]}...{key[-4:]}'
            else:
                preview = '****'
            return {'configured': True, 'preview': preview}

        # Check GEMINI_API_KEY first (preferred), then legacy GOOGLE_GENAI_API_KEY
        gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_GENAI_API_KEY')

        return {
            'api_keys': {
                'GEMINI_API_KEY': mask_key(gemini_key),
                'ANTHROPIC_API_KEY': mask_key(os.getenv('ANTHROPIC_API_KEY')),
                'OPENAI_API_KEY': mask_key(os.getenv('OPENAI_API_KEY')),
                'OLLAMA_HOST': {
                    'configured': True,
                    'preview': os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
                },
            },
            'features': {
                'rag_enabled': True,
                'streaming_enabled': True,
                'tools_enabled': True,
            },
        }

    @app.get('/api/models')
    async def list_models(request: Request):
        """Return available models grouped by provider."""
        # Return providers array directly (frontend expects this format)
        # Use Response with explicit JSON for list serialization in Robyn
        providers = await get_available_models()
        return Response(
            status_code=200,
            headers=Headers({'Content-Type': 'application/json'}),
            description=json.dumps(providers),
        )

    @app.post('/api/chat')
    async def api_chat(request: Request):
        """Call the chat flow via HTTP."""
        try:
            body = json.loads(request.body)
            logger.info(f'Chat request: model={body.get("model")}, message_len={len(body.get("message", ""))}')
            result = await chat_flow(ChatInput(**body))
            return result.model_dump()
        except Exception as e:
            logger.exception(f'Chat error: {e}')
            return Response(
                status_code=500,
                headers={'Content-Type': 'application/json'},
                description=json.dumps({'error': str(e), 'type': type(e).__name__}),
            )

    @app.post('/api/compare')
    async def api_compare(request: Request):
        """Call the compare flow via HTTP."""
        body = json.loads(request.body)
        result = await compare_flow(CompareInput(**body))
        return result.model_dump()

    @app.post('/api/images/describe')
    async def api_describe(request: Request):
        """Call the describe image flow via HTTP."""
        body = json.loads(request.body)
        result = await describe_image_flow(ImageDescribeInput(**body))
        return result.model_dump()

    @app.post('/api/rag')
    async def api_rag(request: Request):
        """Call the RAG flow via HTTP."""
        body = json.loads(request.body)
        result = await rag_flow(RAGInput(**body))
        return result.model_dump()

    @app.get('/api/stream')
    async def api_stream_chat(request: Request):
        """Stream chat response using Server-Sent Events (SSE).

        Uses Robyn's native SSEResponse with async generators for real-time
        token-by-token streaming. Each chunk from the model is sent immediately
        as it's generated.

        SSE Data Flow::

            Frontend Request
                 │
                 ▼
            ┌─────────────────┐
            │  GET /api/stream│ (with message, model params)
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐     ┌─────────────────┐
            │  Robyn SSE      │────▶│  Genkit         │
            │  Endpoint       │     │  generate_stream│
            └────────┬────────┘     └────────┬────────┘
                     │                       │
                     │◀──────────────────────┘
                     │  (async generator yields chunks)
                     ▼
            ┌─────────────────┐
            │  SSEResponse    │
            │  yields SSEMsg  │──────▶ Frontend EventSource
            └─────────────────┘         (receives data: {...})
        """
        # Parse query parameters
        query_params = request.query_params
        message = query_params.get('message', '')
        model = query_params.get('model', 'ollama/llama3.2')
        history = query_params.get('history', '[]')

        async def sse_generator():
            """Async generator that yields SSE messages for each token chunk."""
            try:
                # Parse history and build messages
                messages = []
                if history and history.strip() and history.strip() != '[]':
                    try:
                        history_data = json.loads(history)
                        for msg in history_data:
                            role = msg.get('role', 'user')
                            if role == 'assistant':
                                role = 'model'
                            messages.append({
                                'role': role,
                                'content': [{'text': msg.get('content', '')}],
                            })
                    except json.JSONDecodeError:
                        logger.warning('Failed to parse history JSON')

                # Web frameworks like Robyn already decode URL-encoded query parameters,
                # so we don't need to call unquote() again (double decoding can corrupt
                # special characters like % in the input).
                decoded_message = message or ''
                decoded_model = model or 'ollama/llama3.2'
                logger.info(f'Stream request (Robyn SSE): model={decoded_model}, message_len={len(decoded_message)}')

                # generate_stream returns (stream, future) tuple
                stream, _ = g.generate_stream(
                    model=decoded_model,
                    prompt=decoded_message,
                    messages=messages,
                )

                # Yield each chunk as it arrives from the model
                async for chunk in stream:
                    if chunk.text:
                        # Use "message" event type - EventSource.onmessage handles these
                        yield SSEMessage(
                            data=json.dumps({'chunk': chunk.text}),
                            event='message',
                        )

                # Signal completion - use "message" event so onmessage handler receives it
                yield SSEMessage(data='[DONE]', event='message')

            except Exception as e:
                logger.exception(f'Stream error: {e}')
                yield SSEMessage(
                    data=json.dumps({'error': str(e), 'type': type(e).__name__}),
                    event='message',
                )
                yield SSEMessage(data='[DONE]', event='message')

        return SSEResponse(sse_generator())

    # Serve static files if they exist
    if STATIC_DIR.exists():
        app.serve_directory(
            route='/',
            directory_path=str(STATIC_DIR),
            index_file='index.html',
        )

    return app


def main() -> None:
    """Run the Genkit chat server.

    Supports both Robyn (default) and FastAPI frameworks via --framework flag.
    """
    parser = argparse.ArgumentParser(description='Genkit Chat Server')
    parser.add_argument(
        '--framework',
        choices=['robyn', 'fastapi'],
        default='robyn',
        help='Web framework to use (default: robyn)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('PORT', '8080')),
        help='Port to run on (default: 8080 or PORT env var)',
    )
    args = parser.parse_args()

    port = args.port

    logger.info('=' * 60)
    logger.info(f'Genkit Chat Server ({args.framework.upper()})')
    logger.info('=' * 60)
    logger.info('')
    logger.info('Available Flows (test in DevUI at http://localhost:4000):')
    logger.info('  - chat_flow: Single model chat with tools')
    logger.info('  - compare_flow: Multi-model comparison')
    logger.info('  - describe_image_flow: Image description with vision')
    logger.info('  - rag_flow: RAG with ChromaDB')
    logger.info('  - stream_chat_flow: Streaming chat')
    logger.info('')
    logger.info(f'HTTP API: http://localhost:{port}')
    logger.info('')
    logger.info('Run with: genkit start -- python src/main.py [--framework robyn|fastapi]')
    logger.info('=' * 60)

    if args.framework == 'fastapi':
        app = create_fastapi_server()
        uvicorn.run(app, host='0.0.0.0', port=port, loop='uvloop')
    else:
        # Default: Robyn
        app = create_http_server()
        app.start(port=port)


if __name__ == '__main__':
    main()
