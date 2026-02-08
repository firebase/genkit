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

"""Quart framework adapter.

Creates a Quart application with all Genkit flow endpoints registered.
Quart is the async-native successor to Flask — same API, but runs on
ASGI instead of WSGI.  Flask developers can migrate with minimal code
changes.

Usage::

    from src.frameworks.quart_app import create_app

    app = create_app(ai)
"""

import json
import os
from collections.abc import AsyncGenerator

import structlog
from quart import Quart, Response, jsonify, request

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
    CodeReviewInput,
    ImageInput,
    ImageResponse,
    JokeInput,
    JokeResponse,
    StoryInput,
    TranslateInput,
)

_ready_logger = structlog.get_logger(__name__)


def create_app(ai: Genkit, *, debug: bool = False) -> Quart:
    """Create and configure the Quart application with all routes.

    Quart uses the same decorator API as Flask (``@app.route``,
    ``@app.post``), so Flask developers will feel right at home.
    The key difference is that route handlers are ``async def``
    and can ``await`` Genkit flows directly.

    Args:
        ai: The Genkit instance (used for ``generate_stream`` in SSE
            endpoints).
        debug: Accepted for API consistency with FastAPI/Litestar
            adapters.  Quart does not ship built-in API docs.

    Returns:
        A fully configured Quart ASGI application.
    """
    _ = debug  # Quart has no built-in Swagger UI to toggle.
    app = Quart(__name__)

    @app.post("/tell-joke")
    async def handle_tell_joke() -> dict:
        r"""Non-streaming joke endpoint.

        Test::

            curl -X POST http://localhost:8080/tell-joke \
              -H 'Content-Type: application/json' -d '{}'
        """
        body = JokeInput(**(await request.get_json(silent=True) or {}))
        authorization = request.headers.get("Authorization")
        result = await tell_joke(
            JokeInput(name=body.name, username=authorization),
        )
        return JokeResponse(joke=result, username=authorization).model_dump()

    @app.post("/tell-joke/stream")
    async def handle_tell_joke_stream() -> Response:
        r"""Streaming joke endpoint using Server-Sent Events (SSE).

        Test::

            curl -N -X POST http://localhost:8080/tell-joke/stream \
              -H 'Content-Type: application/json' \
              -d '{"name": "Python"}'
        """
        body = JokeInput(**(await request.get_json(silent=True) or {}))
        authorization = request.headers.get("Authorization")

        async def event_generator() -> AsyncGenerator[str, None]:
            stream, response_future = ai.generate_stream(
                prompt=f"Tell a medium-length joke about {body.name} for user {authorization or 'anonymous'}.",
            )
            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
            final = await response_future
            yield f"data: {json.dumps({'done': True, 'joke': final.text})}\n\n"

        return Response(
            event_generator(),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/tell-story/stream")
    async def handle_tell_story_stream() -> Response:
        r"""Streaming story endpoint using ``flow.stream()``.

        Test::

            curl -N -X POST http://localhost:8080/tell-story/stream \
              -H 'Content-Type: application/json' \
              -d '{"topic": "a robot learning to paint"}'
        """
        body = StoryInput(**(await request.get_json(silent=True) or {}))

        async def event_generator() -> AsyncGenerator[str, None]:
            stream, future = tell_story.stream(input=body)
            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            final = await future
            yield f"data: {json.dumps({'done': True, 'story': final.response})}\n\n"

        return Response(
            event_generator(),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/translate")
    async def handle_translate() -> dict:
        r"""Structured translation endpoint.

        Test::

            curl -X POST http://localhost:8080/translate \
              -H 'Content-Type: application/json' \
              -d '{"text": "Hello, how are you?", "target_language": "Japanese"}'
        """
        body = TranslateInput(**(await request.get_json(silent=True) or {}))
        result = await translate_text(body)
        return result.model_dump()

    @app.post("/describe-image")
    async def handle_describe_image() -> dict:
        r"""Multimodal image description endpoint.

        Test::

            curl -X POST http://localhost:8080/describe-image \
              -H 'Content-Type: application/json' \
              -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"}'
        """
        body = ImageInput(**(await request.get_json(silent=True) or {}))
        description = await describe_image(body)
        return ImageResponse(description=description, image_url=body.image_url).model_dump()

    @app.post("/generate-character")
    async def handle_generate_character() -> dict:
        r"""Structured RPG character generation endpoint.

        Test::

            curl -X POST http://localhost:8080/generate-character \
              -H 'Content-Type: application/json' \
              -d '{"name": "Luna"}'
        """
        body = CharacterInput(**(await request.get_json(silent=True) or {}))
        result = await generate_character(body)
        return result.model_dump()

    @app.post("/chat")
    async def handle_chat() -> dict:
        r"""Chat endpoint with a pirate captain persona.

        Test::

            curl -X POST http://localhost:8080/chat \
              -H 'Content-Type: application/json' \
              -d '{"question": "What is the best programming language?"}'
        """
        body = ChatInput(**(await request.get_json(silent=True) or {}))
        answer = await pirate_chat(body)
        return ChatResponse(answer=answer).model_dump()

    @app.post("/generate-code")
    async def handle_generate_code() -> dict:
        r"""Code generation endpoint.

        Test::

            curl -X POST http://localhost:8080/generate-code \
              -H 'Content-Type: application/json' \
              -d '{"description": "a function that reverses a linked list", "language": "python"}'
        """
        body = CodeInput(**(await request.get_json(silent=True) or {}))
        result = await generate_code(body)
        return result.model_dump()

    @app.post("/review-code")
    async def handle_review_code() -> dict:
        r"""Code review endpoint using a Dotprompt.

        Test::

            curl -X POST http://localhost:8080/review-code \
              -H 'Content-Type: application/json' \
              -d '{"code": "def add(a, b):\\n    return a + b", "language": "python"}'
        """
        body = CodeReviewInput(**(await request.get_json(silent=True) or {}))
        return await review_code(body)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness check — returns ok if the process is running."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Response:
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
            return jsonify({"status": "unavailable", "checks": checks}), 503  # type: ignore[return-value]

        return jsonify({"status": "ok", "checks": checks})

    return app
