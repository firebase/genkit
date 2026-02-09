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

"""Tests for Genkit flows with mocked AI.

Each flow is tested by mocking ai.generate / ai.run so no real
LLM calls are made.  The resilience singletons (cache, breaker) are
set to None so flows call the LLM directly.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/flows_test.py -v
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Flows depend on app_init which triggers Genkit init.  Mock before import.
with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "GENKIT_ENV": "test"}):
    with patch("genkit.plugins.google_genai.GoogleAI", return_value=MagicMock()):
        with patch("genkit.ai.Genkit") as _MockGenkit:
            _mock_ai = MagicMock()
            _mock_ai.flow.return_value = lambda fn: fn
            _mock_ai.tool.return_value = lambda fn: fn
            _mock_ai.prompt.return_value = AsyncMock(
                return_value=MagicMock(output={"summary": "Good", "issues": [], "rating": "A"})
            )
            _MockGenkit.return_value = _mock_ai

            from src import resilience
            from src.app_init import ai as _actual_ai
            from src.flows import (
                _cached_call,  # noqa: PLC2701 - testing private function
                _with_breaker,  # noqa: PLC2701 - testing private function
                describe_image,
                generate_character,
                generate_code,
                pirate_chat,
                review_code,
                tell_joke,
                tell_story,
                translate_text,
            )
            from src.schemas import (
                CharacterInput,
                ChatInput,
                CodeInput,
                CodeOutput,
                CodeReviewInput,
                ImageInput,
                JokeInput,
                RpgCharacter,
                Skills,
                StoryInput,
                TranslateInput,
                TranslationResult,
            )


@pytest.fixture(autouse=True)
def _clear_resilience() -> None:
    """Ensure resilience singletons are None so flows call LLM directly."""
    resilience.flow_cache = None
    resilience.llm_breaker = None


@pytest.mark.asyncio
async def test_with_breaker_no_breaker() -> None:
    """_with_breaker calls directly when breaker is None."""
    call = AsyncMock(return_value="result")
    result = await _with_breaker(call)
    assert result == "result"
    call.assert_awaited_once()


@pytest.mark.asyncio
async def test_with_breaker_uses_breaker() -> None:
    """_with_breaker delegates to the circuit breaker when available."""
    mock_breaker = MagicMock()
    mock_breaker.call = AsyncMock(return_value="breaker-result")
    resilience.llm_breaker = mock_breaker

    call = AsyncMock(return_value="direct")
    result = await _with_breaker(call)

    assert result == "breaker-result"
    mock_breaker.call.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_call_no_cache() -> None:
    """_cached_call calls directly when cache is None."""
    call = AsyncMock(return_value="result")
    result = await _cached_call("test_flow", "input", call)
    assert result == "result"
    call.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_call_uses_cache() -> None:
    """_cached_call delegates to the cache when available."""
    mock_cache = MagicMock()
    mock_cache.get_or_call = AsyncMock(return_value="cached-result")
    resilience.flow_cache = mock_cache

    call = AsyncMock(return_value="direct")
    result = await _cached_call("test_flow", "input", call)

    assert result == "cached-result"
    mock_cache.get_or_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_tell_joke() -> None:
    """tell_joke calls ai.generate and returns the text."""
    mock_response = MagicMock()
    mock_response.text = "Why did the cat sit on the computer?"

    with patch.object(_actual_ai, "generate", new_callable=AsyncMock, return_value=mock_response):
        result = await tell_joke(JokeInput(name="Mittens"))

    assert result == "Why did the cat sit on the computer?"


@pytest.mark.asyncio
async def test_pirate_chat() -> None:
    """pirate_chat calls ai.generate with a system prompt."""
    mock_response = MagicMock()
    mock_response.text = "Arrr, Python be grand!"

    with patch.object(_actual_ai, "generate", new_callable=AsyncMock, return_value=mock_response):
        result = await pirate_chat(ChatInput(question="Best language?"))

    assert result == "Arrr, Python be grand!"


@pytest.mark.asyncio
async def test_translate_text() -> None:
    """translate_text uses structured output and caching."""
    expected = TranslationResult(
        original_text="Hi",
        translated_text="Salut",
        target_language="French",
        confidence="high",
    )
    mock_response = MagicMock()
    mock_response.output = expected

    with (
        patch.object(_actual_ai, "generate", new_callable=AsyncMock, return_value=mock_response),
        patch.object(_actual_ai, "run", new_callable=AsyncMock, side_effect=lambda name, text, fn: fn(text)),
    ):
        result = await translate_text(TranslateInput(text="Hi", target_language="French"))

    assert result.translated_text == "Salut"


@pytest.mark.asyncio
async def test_describe_image() -> None:
    """describe_image uses multimodal generation."""
    mock_response = MagicMock()
    mock_response.text = "A colorful dice"

    with patch.object(_actual_ai, "generate", new_callable=AsyncMock, return_value=mock_response):
        result = await describe_image(ImageInput())

    assert result == "A colorful dice"


@pytest.mark.asyncio
async def test_generate_character() -> None:
    """generate_character returns a structured RPG character."""
    expected = RpgCharacter(
        name="Luna",
        backStory="A mage.",
        abilities=["Frost"],
        skills=Skills(strength=50, charisma=80, endurance=60),
    )
    mock_response = MagicMock()
    mock_response.output = expected

    with patch.object(_actual_ai, "generate", new_callable=AsyncMock, return_value=mock_response):
        result = await generate_character(CharacterInput(name="Luna"))

    assert result.name == "Luna"


@pytest.mark.asyncio
async def test_generate_code() -> None:
    """generate_code returns structured code output."""
    expected = CodeOutput(
        code="print('hello')",
        language="python",
        explanation="Prints hello.",
        filename="hello.py",
    )
    mock_response = MagicMock()
    mock_response.output = expected

    with patch.object(_actual_ai, "generate", new_callable=AsyncMock, return_value=mock_response):
        result = await generate_code(CodeInput(description="print hello"))

    assert result.code == "print('hello')"


@pytest.mark.asyncio
async def test_review_code() -> None:
    """review_code uses a Dotprompt and returns a dict."""
    mock_prompt = AsyncMock(return_value=MagicMock(output={"summary": "Good", "issues": [], "rating": "A"}))

    with patch.object(_actual_ai, "prompt", return_value=mock_prompt):
        result = await review_code(CodeReviewInput(code="x = 1"))

    assert result["rating"] == "A"


@pytest.mark.asyncio
async def test_tell_story() -> None:
    """tell_story streams chunks and returns the final text."""
    mock_chunk = MagicMock()
    mock_chunk.text = "Once upon a time"

    mock_result = MagicMock()
    mock_result.text = "Once upon a time, there was a cat."

    async def mock_stream() -> AsyncIterator[MagicMock]:
        """Mock async chunk stream."""
        yield mock_chunk

    async def mock_result_future() -> MagicMock:
        """Mock async result future."""
        return mock_result

    with patch.object(
        _actual_ai,
        "generate_stream",
        return_value=(mock_stream(), mock_result_future()),
    ):
        result = await tell_story(StoryInput(topic="a brave cat"))

    assert result == "Once upon a time, there was a cat."


@pytest.mark.asyncio
async def test_tell_story_sends_chunks_via_context() -> None:
    """tell_story sends chunks via ctx.send_chunk when context is provided."""
    mock_chunk1 = MagicMock()
    mock_chunk1.text = "chunk1"
    mock_chunk2 = MagicMock()
    mock_chunk2.text = "chunk2"

    mock_result = MagicMock()
    mock_result.text = "chunk1 chunk2"

    async def mock_stream() -> AsyncIterator[MagicMock]:
        """Mock async chunk stream."""
        yield mock_chunk1
        yield mock_chunk2

    async def mock_result_future() -> MagicMock:
        """Mock async result future."""
        return mock_result

    mock_ctx = MagicMock()

    with patch.object(
        _actual_ai,
        "generate_stream",
        return_value=(mock_stream(), mock_result_future()),
    ):
        result = await tell_story(StoryInput(topic="test"), ctx=mock_ctx)

    assert result == "chunk1 chunk2"
    assert mock_ctx.send_chunk.call_count == 2
