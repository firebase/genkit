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

"""gRPC server that delegates every RPC to a Genkit flow.

Each method is a thin async wrapper: it converts the protobuf request
into the corresponding Pydantic model, calls the flow, and maps the
result back to a protobuf response.

The server enables **gRPC reflection** so tools like ``grpcui`` and
``grpcurl`` can introspect the service without a ``.proto`` file.

Interceptors applied to the server:

- **GrpcLoggingInterceptor** — logs every RPC call with method name,
  duration, and status code via structlog.
- **GrpcRateLimitInterceptor** — token-bucket rate limiting that
  returns ``RESOURCE_EXHAUSTED`` when the bucket is empty.
- **Max message size** — ``grpc.max_receive_message_length`` caps
  inbound messages (default: 1 MB, matching the REST body limit).

Usage::

    from src.grpc_server import serve_grpc

    # In an asyncio context (run alongside the ASGI server):
    await serve_grpc(port=50051)
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import grpc
import structlog
from grpc_reflection.v1alpha import reflection
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer

from .flows import (
    describe_image,
    generate_character,
    generate_code,
    pirate_chat,
    review_code,
    tell_joke,
    tell_story,
    translate_text,
)
from .generated import genkit_sample_pb2, genkit_sample_pb2_grpc
from .rate_limit import GrpcRateLimitInterceptor
from .schemas import (
    CharacterInput,
    ChatInput,
    CodeInput,
    CodeReviewInput,
    ImageInput,
    JokeInput,
    StoryInput,
    TranslateInput,
)

logger = structlog.get_logger(__name__)

DEFAULT_MAX_RECEIVE_MESSAGE_LENGTH = 1_048_576
"""Default maximum inbound gRPC message size in bytes (1 MB)."""


class GrpcLoggingInterceptor(grpc.aio.ServerInterceptor):  # ty: ignore[possibly-missing-attribute] — incomplete stubs
    """gRPC server interceptor that logs every RPC call.

    Captures method name, duration, and whether the call succeeded
    or failed. Uses structlog for structured log output.
    """

    async def intercept_service(
        self,
        continuation: Callable[..., Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:  # noqa: ANN401 - return type is dictated by grpc.aio.ServerInterceptor
        """Log the RPC method and delegate to the next handler."""
        method = handler_call_details.method  # ty: ignore[unresolved-attribute] - grpc stubs lack .method
        start = time.monotonic()
        logger.info("gRPC call started", method=method)
        try:
            handler = await continuation(handler_call_details)
            elapsed = time.monotonic() - start
            logger.info("gRPC call completed", method=method, duration_ms=round(elapsed * 1000, 1))
            return handler
        except Exception:
            elapsed = time.monotonic() - start
            logger.exception("gRPC call failed", method=method, duration_ms=round(elapsed * 1000, 1))
            raise


class GenkitServiceServicer(genkit_sample_pb2_grpc.GenkitServiceServicer):
    """Implements the GenkitService gRPC interface.

    Every RPC delegates to the same Genkit flow used by the REST endpoints,
    so traces, metrics, and the DevUI work identically regardless of protocol.
    """

    async def Health(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.HealthResponse:
        """Health check — always returns ``ok``."""
        return genkit_sample_pb2.HealthResponse(status="ok")

    async def TellJoke(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.JokeRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.JokeResponse:
        """Generate a joke by calling the ``tell_joke`` flow."""
        result = await tell_joke(
            JokeInput(name=request.name or "Mittens", username=request.username or None),
        )
        return genkit_sample_pb2.JokeResponse(
            joke=result,
            username=request.username,
        )

    async def TranslateText(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.TranslateRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.TranslationResponse:
        """Translate text by calling the ``translate_text`` flow."""
        result = await translate_text(
            TranslateInput(
                text=request.text,
                target_language=request.target_language or "French",
            ),
        )
        return genkit_sample_pb2.TranslationResponse(
            original_text=result.original_text,
            translated_text=result.translated_text,
            target_language=result.target_language,
            confidence=result.confidence,
        )

    async def DescribeImage(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.ImageRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.ImageResponse:
        """Describe an image by calling the ``describe_image`` flow."""
        image_url = (
            request.image_url
            or "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"
        )
        description = await describe_image(ImageInput(image_url=image_url))
        return genkit_sample_pb2.ImageResponse(
            description=description,
            image_url=image_url,
        )

    async def GenerateCharacter(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.CharacterRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.RpgCharacter:
        """Generate an RPG character by calling the ``generate_character`` flow."""
        result = await generate_character(
            CharacterInput(name=request.name or "Luna"),
        )
        return genkit_sample_pb2.RpgCharacter(
            name=result.name,
            back_story=result.back_story,
            abilities=list(result.abilities),
            skills=genkit_sample_pb2.Skills(
                strength=result.skills.strength,
                charisma=result.skills.charisma,
                endurance=result.skills.endurance,
            ),
        )

    async def PirateChat(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.ChatRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.ChatResponse:
        """Chat with a pirate captain by calling the ``pirate_chat`` flow."""
        answer = await pirate_chat(
            ChatInput(question=request.question or "What is the best programming language?"),
        )
        return genkit_sample_pb2.ChatResponse(
            answer=answer,
            persona="pirate captain",
        )

    async def TellStory(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.StoryRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> AsyncIterator[genkit_sample_pb2.StoryChunk]:
        """Stream a story by calling the ``tell_story`` flow with server-side streaming."""
        stream, future = tell_story.stream(
            input=StoryInput(topic=request.topic or "a brave cat"),
        )
        async for chunk in stream:
            yield genkit_sample_pb2.StoryChunk(text=chunk)
        # Await the future to ensure the flow completes cleanly.
        await future

    async def GenerateCode(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.CodeRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.CodeResponse:
        """Generate code by calling the ``generate_code`` flow."""
        result = await generate_code(
            CodeInput(
                description=request.description or "a Python function that checks if a number is prime",
                language=request.language or "python",
            ),
        )
        return genkit_sample_pb2.CodeResponse(
            code=result.code,
            language=result.language,
            explanation=result.explanation,
            filename=result.filename,
        )

    async def ReviewCode(  # noqa: N802 — method names match the generated protobuf stub (PascalCase)  # pyrefly: ignore[bad-override] — generated stub types (request: Unknown, context: Unknown) -> Never
        self,
        request: genkit_sample_pb2.CodeReviewRequest,
        context: grpc.aio.ServicerContext,  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
    ) -> genkit_sample_pb2.CodeReviewResponse:
        """Review code by calling the ``review_code`` flow."""
        result = await review_code(
            CodeReviewInput(
                code=request.code or "def add(a, b):\n    return a + b",
                language=request.language or None,
            ),
        )
        return genkit_sample_pb2.CodeReviewResponse(
            review=json.dumps(result) if isinstance(result, dict) else str(result),
        )


async def serve_grpc(
    port: int = 50051,
    *,
    rate_limit: str = "60/minute",
    shutdown_grace: float = 10.0,
    max_message_size: int = DEFAULT_MAX_RECEIVE_MESSAGE_LENGTH,
    debug: bool = False,
) -> None:
    """Start the async gRPC server with interceptors.

    The server runs until cancelled (e.g. via ``asyncio.CancelledError``
    or a keyboard interrupt).

    Args:
        port: TCP port to listen on (default: 50051).
        rate_limit: Rate limit string for the gRPC rate limiter
            (default: ``60/minute``).
        shutdown_grace: Seconds to wait for in-flight RPCs to complete
            during graceful shutdown (default: 10). Cloud Run sends
            SIGTERM and gives 10s by default.
        max_message_size: Maximum inbound gRPC message size in bytes
            (default: 1 MB).  Should match the REST ``max_body_size``
            to provide consistent limits across protocols.
        debug: When ``True``, enable gRPC reflection (for grpcui /
            grpcurl).  Must be ``False`` in production — reflection
            exposes the full API schema to unauthenticated clients.
    """
    # Auto-instrument gRPC with OpenTelemetry semantic conventions.
    # Adds rpc.system, rpc.service, rpc.method span attributes so gRPC
    # traces are clearly distinguishable from REST traces in Jaeger.
    GrpcAioInstrumentorServer().instrument()  # pyrefly: ignore[missing-attribute] — incomplete type stubs

    interceptors = [
        GrpcLoggingInterceptor(),
        GrpcRateLimitInterceptor(rate=rate_limit),
    ]

    server = grpc.aio.server(  # ty: ignore[possibly-missing-attribute] — grpc.aio stubs are incomplete
        interceptors=interceptors,
        options=[
            ("grpc.max_receive_message_length", max_message_size),
        ],
    )
    genkit_sample_pb2_grpc.add_GenkitServiceServicer_to_server(
        GenkitServiceServicer(),
        server,
    )

    # gRPC reflection lets grpcui / grpcurl introspect the service without
    # a .proto file.  Useful during development but exposes the full API
    # schema, so it is gated behind the debug flag.
    if debug:
        service_names = (
            genkit_sample_pb2.DESCRIPTOR.services_by_name["GenkitService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)

    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    await server.start()

    logger.info(
        "gRPC server started",
        port=port,
        reflection=debug,
        rate_limit=rate_limit,
        max_message_bytes=max_message_size,
    )
    if debug:
        logger.info(
            "Test with grpcui",
            command=f"grpcui -plaintext localhost:{port}",
        )

    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        logger.info("gRPC server shutting down...", grace_seconds=shutdown_grace)
        await server.stop(grace=shutdown_grace)
