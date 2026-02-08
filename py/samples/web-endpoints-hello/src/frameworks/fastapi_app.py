# Copyright 2026 Google LLC
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

"""FastAPI framework adapter.

Creates a FastAPI application with all Genkit flow endpoints registered.
FastAPI's native ASGI support means Genkit flows can be called directly
— ``await tell_joke(input)`` — with no adapter needed.

Usage::

    from src.frameworks.fastapi_app import create_app

    app = create_app(ai)
"""

import json
import os
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse, StreamingResponse

from genkit.ai import Genkit

from ..flows import (
    describe_image,
    generate_character,
    generate_code,
    pirate_chat,
    review_code,
    tell_joke,
    tell_story,
    translate_text,
)
from ..schemas import (
    CharacterInput,
    ChatInput,
    ChatResponse,
    CodeInput,
    CodeOutput,
    CodeReviewInput,
    ImageInput,
    ImageResponse,
    JokeInput,
    JokeResponse,
    RpgCharacter,
    StoryInput,
    TranslateInput,
    TranslationResult,
)

_ready_logger = structlog.get_logger(__name__)


def create_app(ai: Genkit, *, debug: bool = False) -> FastAPI:
    """Create and configure the FastAPI application with all routes.

    Args:
        ai: The Genkit instance (used for ``generate_stream`` in SSE
            endpoints).
        debug: When ``True``, Swagger UI (``/docs``), ReDoc (``/redoc``),
            and the OpenAPI schema (``/openapi.json``) are enabled.
            Must be ``False`` in production.

    Returns:
        A fully configured FastAPI ASGI application.
    """
    app = FastAPI(
        title="Genkit + ASGI Demo",
        description=(
            "Genkit AI flows via FastAPI — tools, structured output, "
            "streaming, multimodal, system prompts, and traced steps."
        ),
        version="0.1.0",
        docs_url="/docs" if debug else None,
        redoc_url="/redoc" if debug else None,
        openapi_url="/openapi.json" if debug else None,
    )

    @app.post("/tell-joke", response_model=JokeResponse)
    async def handle_tell_joke(
        body: JokeInput,
        authorization: str | None = Header(default=None),
    ) -> JokeResponse:
        r"""Non-streaming joke endpoint.

        Test::

            curl -X POST http://localhost:8080/tell-joke \
              -H 'Content-Type: application/json' -d '{}'
        """
        result = await tell_joke(
            JokeInput(name=body.name, username=authorization),
        )
        return JokeResponse(joke=result, username=authorization)

    @app.post("/tell-joke/stream")
    async def handle_tell_joke_stream(
        body: JokeInput,
        authorization: str | None = Header(default=None),
    ) -> StreamingResponse:
        r"""Streaming joke endpoint using Server-Sent Events (SSE).

        Test::

            curl -N -X POST http://localhost:8080/tell-joke/stream \
              -H 'Content-Type: application/json' \
              -d '{"name": "Python"}'
        """

        async def event_generator() -> AsyncGenerator[str, None]:
            stream, response_future = ai.generate_stream(
                prompt=f"Tell a medium-length joke about {body.name} for user {authorization or 'anonymous'}.",
            )
            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
            final = await response_future
            yield f"data: {json.dumps({'done': True, 'joke': final.text})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/tell-story/stream")
    async def handle_tell_story_stream(body: StoryInput) -> StreamingResponse:
        r"""Streaming story endpoint using ``flow.stream()``.

        Test::

            curl -N -X POST http://localhost:8080/tell-story/stream \
              -H 'Content-Type: application/json' \
              -d '{"topic": "a robot learning to paint"}'
        """

        async def event_generator() -> AsyncGenerator[str, None]:
            stream, future = tell_story.stream(input=body)
            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            final = await future
            yield f"data: {json.dumps({'done': True, 'story': final.response})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/translate", response_model=TranslationResult)
    async def handle_translate(body: TranslateInput) -> TranslationResult:
        r"""Structured translation endpoint.

        Test::

            curl -X POST http://localhost:8080/translate \
              -H 'Content-Type: application/json' \
              -d '{"text": "Hello, how are you?", "target_language": "Japanese"}'
        """
        return await translate_text(body)

    @app.post("/describe-image", response_model=ImageResponse)
    async def handle_describe_image(body: ImageInput) -> ImageResponse:
        r"""Multimodal image description endpoint.

        Test::

            curl -X POST http://localhost:8080/describe-image \
              -H 'Content-Type: application/json' \
              -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"}'
        """
        description = await describe_image(body)
        return ImageResponse(description=description, image_url=body.image_url)

    @app.post("/generate-character", response_model=RpgCharacter)
    async def handle_generate_character(body: CharacterInput) -> RpgCharacter:
        r"""Structured RPG character generation endpoint.

        Test::

            curl -X POST http://localhost:8080/generate-character \
              -H 'Content-Type: application/json' \
              -d '{"name": "Luna"}'
        """
        return await generate_character(body)

    @app.post("/chat", response_model=ChatResponse)
    async def handle_chat(body: ChatInput) -> ChatResponse:
        r"""Chat endpoint with a pirate captain persona.

        Test::

            curl -X POST http://localhost:8080/chat \
              -H 'Content-Type: application/json' \
              -d '{"question": "What is the best programming language?"}'
        """
        answer = await pirate_chat(body)
        return ChatResponse(answer=answer)

    @app.post("/generate-code", response_model=CodeOutput)
    async def handle_generate_code(body: CodeInput) -> CodeOutput:
        r"""Code generation endpoint.

        Test::

            curl -X POST http://localhost:8080/generate-code \
              -H 'Content-Type: application/json' \
              -d '{"description": "a function that reverses a linked list", "language": "python"}'
        """
        return await generate_code(body)

    @app.post("/review-code")
    async def handle_review_code(body: CodeReviewInput) -> dict:
        r"""Code review endpoint using a Dotprompt.

        Test::

            curl -X POST http://localhost:8080/review-code \
              -H 'Content-Type: application/json' \
              -d '{"code": "def add(a, b):\\n    return a + b", "language": "python"}'
        """
        return await review_code(body)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness check — returns ok if the process is running."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Readiness check — verifies the app can serve traffic.

        Checks that essential dependencies are configured:

        - ``GEMINI_API_KEY`` is set (required for LLM flows).

        Returns 200 when ready, 503 when a dependency is missing
        or unreachable.  Kubernetes uses this to decide when to route
        traffic; Cloud Run uses ``/health``.
        """
        checks: dict[str, str] = {}

        if os.environ.get("GEMINI_API_KEY"):
            checks["gemini_api_key"] = "configured"
        else:
            checks["gemini_api_key"] = "missing"
            _ready_logger.warning("Readiness check failed: GEMINI_API_KEY not set")
            return JSONResponse(
                {"status": "unavailable", "checks": checks},
                status_code=503,
            )

        return JSONResponse({"status": "ok", "checks": checks})

    return app
