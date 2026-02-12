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

"""Litestar framework adapter.

Creates a Litestar application with all Genkit flow endpoints registered.
Litestar is a high-performance ASGI framework with built-in OpenAPI docs,
data validation, and dependency injection.

Usage::

    from src.frameworks.litestar_app import create_app

    app = create_app(ai)

Litestar docs: https://docs.litestar.dev/
"""

import json
import os
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass

import structlog
from litestar import Litestar, MediaType, get, post
from litestar.openapi import OpenAPIConfig
from litestar.response import Stream

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


@dataclass
class _AppState:
    """Holds the Genkit instance for route handler access."""

    ai: Genkit


def create_app(ai: Genkit, *, debug: bool = False) -> Litestar:
    """Create and configure the Litestar application with all routes.

    Args:
        ai: The Genkit instance (used for ``generate_stream`` in SSE
            endpoints).
        debug: When ``True``, the built-in Swagger/ReDoc docs are
            served.  Must be ``False`` in production.

    Returns:
        A fully configured Litestar ASGI application.
    """
    state = _AppState(ai=ai)

    @post("/tell-joke")
    async def handle_tell_joke(data: JokeInput) -> JokeResponse:
        r"""Non-streaming joke endpoint.

        Test::

            curl -X POST http://localhost:8080/tell-joke \
              -H 'Content-Type: application/json' -d '{}'
        """
        result = await tell_joke(
            JokeInput(name=data.name, username=data.username),
        )
        return JokeResponse(joke=result, username=data.username)

    @post("/tell-joke/stream", media_type=MediaType.TEXT)
    async def handle_tell_joke_stream(data: JokeInput) -> Stream:
        r"""Streaming joke endpoint using Server-Sent Events (SSE).

        Test::

            curl -N -X POST http://localhost:8080/tell-joke/stream \
              -H 'Content-Type: application/json' \
              -d '{"name": "Python"}'
        """

        async def event_generator() -> AsyncIterator[str]:
            username = data.username or "anonymous"
            stream, response_future = state.ai.generate_stream(
                prompt=f"Tell a medium-length joke about {data.name} for user {username}.",
            )
            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
            final = await response_future
            yield f"data: {json.dumps({'done': True, 'joke': final.text})}\n\n"

        return Stream(
            content=event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @post("/tell-story/stream", media_type=MediaType.TEXT)
    async def handle_tell_story_stream(data: StoryInput) -> Stream:
        r"""Streaming story endpoint using ``flow.stream()``.

        Test::

            curl -N -X POST http://localhost:8080/tell-story/stream \
              -H 'Content-Type: application/json' \
              -d '{"topic": "a robot learning to paint"}'
        """

        async def event_generator() -> AsyncGenerator[str, None]:
            stream, future = tell_story.stream(input=data)
            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            final = await future
            yield f"data: {json.dumps({'done': True, 'story': final.response})}\n\n"

        return Stream(
            content=event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @post("/translate")
    async def handle_translate(data: TranslateInput) -> TranslationResult:
        r"""Structured translation endpoint.

        Test::

            curl -X POST http://localhost:8080/translate \
              -H 'Content-Type: application/json' \
              -d '{"text": "Hello, how are you?", "target_language": "Japanese"}'
        """
        return await translate_text(data)

    @post("/describe-image")
    async def handle_describe_image(data: ImageInput) -> ImageResponse:
        r"""Multimodal image description endpoint.

        Test::

            curl -X POST http://localhost:8080/describe-image \
              -H 'Content-Type: application/json' \
              -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"}'
        """
        description = await describe_image(data)
        return ImageResponse(description=description, image_url=data.image_url)

    @post("/generate-character")
    async def handle_generate_character(data: CharacterInput) -> RpgCharacter:
        r"""Structured RPG character generation endpoint.

        Test::

            curl -X POST http://localhost:8080/generate-character \
              -H 'Content-Type: application/json' \
              -d '{"name": "Luna"}'
        """
        return await generate_character(data)

    @post("/chat")
    async def handle_chat(data: ChatInput) -> ChatResponse:
        r"""Chat endpoint with a pirate captain persona.

        Test::

            curl -X POST http://localhost:8080/chat \
              -H 'Content-Type: application/json' \
              -d '{"question": "What is the best programming language?"}'
        """
        answer = await pirate_chat(data)
        return ChatResponse(answer=answer)

    @post("/generate-code")
    async def handle_generate_code(data: CodeInput) -> CodeOutput:
        r"""Code generation endpoint.

        Test::

            curl -X POST http://localhost:8080/generate-code \
              -H 'Content-Type: application/json' \
              -d '{"description": "a function that reverses a linked list", "language": "python"}'
        """
        return await generate_code(data)

    @post("/review-code")
    async def handle_review_code(data: CodeReviewInput) -> dict:
        r"""Code review endpoint using a Dotprompt.

        Test::

            curl -X POST http://localhost:8080/review-code \
              -H 'Content-Type: application/json' \
              -d '{"code": "def add(a, b):\\n    return a + b", "language": "python"}'
        """
        return await review_code(data)

    @get("/health")
    async def health() -> dict[str, str]:
        """Liveness check — returns ok if the process is running."""
        return {"status": "ok"}

    @get("/ready")
    async def ready() -> dict[str, object]:
        """Readiness check — verifies the app can serve traffic.

        Checks that essential dependencies are configured:

        - ``GEMINI_API_KEY`` is set (required for LLM flows).

        Returns 200 when ready, 503 when a dependency is missing.
        """
        checks: dict[str, str] = {}

        if os.environ.get("GEMINI_API_KEY"):
            checks["gemini_api_key"] = "configured"
        else:
            checks["gemini_api_key"] = "missing"
            _ready_logger.warning("Readiness check failed: GEMINI_API_KEY not set")
            from litestar.response import Response  # noqa: PLC0415 — avoid import at module level

            return Response(  # type: ignore[return-value]
                content={"status": "unavailable", "checks": checks},
                status_code=503,
                media_type=MediaType.JSON,
            )

        return {"status": "ok", "checks": checks}

    openapi_config = OpenAPIConfig(
        title="Genkit + ASGI Demo",
        version="0.1.0",
        enabled_endpoints={"swagger", "redoc", "openapi.json", "openapi.yaml"} if debug else set(),
    )

    return Litestar(
        route_handlers=[
            handle_tell_joke,
            handle_tell_joke_stream,
            handle_tell_story_stream,
            handle_translate,
            handle_describe_image,
            handle_generate_character,
            handle_chat,
            handle_generate_code,
            handle_review_code,
            health,
            ready,
        ],
        openapi_config=openapi_config,
    )
