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

"""Tests for the gRPC server servicer methods.

Each RPC method in GenkitServiceServicer is tested by mocking the
underlying Genkit flow and asserting the protobuf response.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/grpc_server_test.py -v
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.generated import genkit_sample_pb2
from src.grpc_server import GenkitServiceServicer, GrpcLoggingInterceptor
from src.schemas import (
    CodeOutput,
    RpgCharacter,
    Skills,
    TranslationResult,
)


@pytest.fixture
def servicer() -> GenkitServiceServicer:
    """Create a fresh servicer instance for each test."""
    return GenkitServiceServicer()


@pytest.fixture
def context() -> MagicMock:
    """Create a mock gRPC context."""
    return MagicMock()


@pytest.mark.asyncio
async def test_health(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """Health RPC returns status ok."""
    request = genkit_sample_pb2.HealthRequest()
    response = await servicer.Health(request, context)
    assert response.status == "ok"


@pytest.mark.asyncio
async def test_tell_joke(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """TellJoke RPC calls the tell_joke flow and returns the joke."""
    with patch("src.grpc_server.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Why did Mittens cross the road?"
        request = genkit_sample_pb2.JokeRequest(name="Mittens")
        response = await servicer.TellJoke(request, context)

    assert response.joke == "Why did Mittens cross the road?"


@pytest.mark.asyncio
async def test_tell_joke_default_name(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """TellJoke RPC uses default name when empty."""
    with patch("src.grpc_server.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A joke"
        request = genkit_sample_pb2.JokeRequest()
        response = await servicer.TellJoke(request, context)

    assert response.joke == "A joke"
    call_args = mock_flow.call_args[0][0]
    assert call_args.name == "Mittens"


@pytest.mark.asyncio
async def test_translate_text(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """TranslateText RPC calls translate_text flow and maps the result."""
    mock_result = TranslationResult(
        original_text="Hello",
        translated_text="Bonjour",
        target_language="French",
        confidence="high",
    )
    with patch("src.grpc_server.translate_text", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_result
        request = genkit_sample_pb2.TranslateRequest(text="Hello", target_language="French")
        response = await servicer.TranslateText(request, context)

    assert response.translated_text == "Bonjour"
    assert response.original_text == "Hello"
    assert response.confidence == "high"


@pytest.mark.asyncio
async def test_describe_image(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """DescribeImage RPC calls describe_image flow."""
    with patch("src.grpc_server.describe_image", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A beautiful sunset"
        url = "https://example.com/image.jpg"
        request = genkit_sample_pb2.ImageRequest(image_url=url)
        response = await servicer.DescribeImage(request, context)

    assert response.description == "A beautiful sunset"
    assert response.image_url == url


@pytest.mark.asyncio
async def test_describe_image_default_url(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """DescribeImage RPC uses a default URL when empty."""
    with patch("src.grpc_server.describe_image", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A PNG image"
        request = genkit_sample_pb2.ImageRequest()
        response = await servicer.DescribeImage(request, context)

    assert response.description == "A PNG image"
    assert "wikipedia" in response.image_url


@pytest.mark.asyncio
async def test_generate_character(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """GenerateCharacter RPC returns a structured RPG character."""
    mock_char = RpgCharacter(
        name="Luna",
        backStory="A mysterious mage.",
        abilities=["Frost Bolt", "Teleport"],
        skills=Skills(strength=40, charisma=90, endurance=55),
    )
    with patch("src.grpc_server.generate_character", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_char
        request = genkit_sample_pb2.CharacterRequest(name="Luna")
        response = await servicer.GenerateCharacter(request, context)

    assert response.name == "Luna"
    assert response.skills.charisma == 90
    assert list(response.abilities) == ["Frost Bolt", "Teleport"]


@pytest.mark.asyncio
async def test_pirate_chat(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """PirateChat RPC returns a pirate-style answer."""
    with patch("src.grpc_server.pirate_chat", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Arrr, Python be the finest!"
        request = genkit_sample_pb2.ChatRequest(question="Best language?")
        response = await servicer.PirateChat(request, context)

    assert response.answer == "Arrr, Python be the finest!"
    assert response.persona == "pirate captain"


@pytest.mark.asyncio
async def test_generate_code(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """GenerateCode RPC returns structured code output."""
    mock_output = CodeOutput(
        code="def hello(): pass",
        language="python",
        explanation="A simple function.",
        filename="hello.py",
    )
    with patch("src.grpc_server.generate_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        request = genkit_sample_pb2.CodeRequest(description="hello function", language="python")
        response = await servicer.GenerateCode(request, context)

    assert response.code == "def hello(): pass"
    assert response.language == "python"
    assert response.filename == "hello.py"


@pytest.mark.asyncio
async def test_review_code(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """ReviewCode RPC returns a JSON-encoded review."""
    mock_output = {"summary": "Looks good", "issues": [], "rating": "A"}
    with patch("src.grpc_server.review_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        request = genkit_sample_pb2.CodeReviewRequest(code="def add(a, b): return a + b")
        response = await servicer.ReviewCode(request, context)

    assert "Looks good" in response.review


@pytest.mark.asyncio
async def test_review_code_string_result(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """ReviewCode RPC handles string results correctly."""
    with patch("src.grpc_server.review_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "This code is fine."
        request = genkit_sample_pb2.CodeReviewRequest(code="x = 1")
        response = await servicer.ReviewCode(request, context)

    assert response.review == "This code is fine."


@pytest.mark.asyncio
async def test_tell_story_stream(servicer: GenkitServiceServicer, context: MagicMock) -> None:
    """TellStory RPC yields chunks from the streaming flow."""

    async def mock_stream() -> AsyncIterator[str]:
        """Mock async chunk stream."""
        for chunk in ["Once", " upon", " a time"]:
            yield chunk

    mock_future = AsyncMock(return_value=MagicMock(response="Once upon a time"))

    mock_flow = MagicMock()
    mock_flow.stream.return_value = (mock_stream(), mock_future())

    with patch("src.grpc_server.tell_story", mock_flow):
        request = genkit_sample_pb2.StoryRequest(topic="cats")
        chunks = []
        async for chunk in servicer.TellStory(request, context):
            chunks.append(chunk.text)

    assert chunks == ["Once", " upon", " a time"]


@pytest.mark.asyncio
async def test_grpc_logging_interceptor() -> None:
    """GrpcLoggingInterceptor logs the RPC method and duration."""
    interceptor = GrpcLoggingInterceptor()
    mock_handler = MagicMock()
    mock_continuation = AsyncMock(return_value=mock_handler)
    mock_details = MagicMock()
    mock_details.method = "/GenkitService/Health"

    result = await interceptor.intercept_service(mock_continuation, mock_details)

    mock_continuation.assert_awaited_once_with(mock_details)
    assert result == mock_handler


@pytest.mark.asyncio
async def test_grpc_logging_interceptor_on_exception() -> None:
    """GrpcLoggingInterceptor re-raises exceptions from the handler."""
    interceptor = GrpcLoggingInterceptor()
    mock_continuation = AsyncMock(side_effect=RuntimeError("handler error"))
    mock_details = MagicMock()
    mock_details.method = "/GenkitService/TellJoke"

    with pytest.raises(RuntimeError, match="handler error"):
        await interceptor.intercept_service(mock_continuation, mock_details)
