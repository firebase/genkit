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

"""Unit tests for the Quart endpoint adapter.

Mirrors the FastAPI endpoint tests to ensure Quart routes behave
identically.  Uses Quart's built-in test client.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/quart_endpoints_test.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

            from src.frameworks.quart_app import create_app
            from src.schemas import (
                CodeOutput,
                RpgCharacter,
                Skills,
                TranslationResult,
            )

            _app = create_app(_mock_ai)


@pytest.fixture
def client():  # noqa: ANN201 — Quart test client type is complex
    """Create a Quart test client."""
    return _app.test_client()


@pytest.mark.asyncio
async def test_health(client) -> None:  # noqa: ANN001 — Quart test client
    """GET /health returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = await response.get_json()
    assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_with_api_key(client) -> None:  # noqa: ANN001 — Quart test client
    """GET /ready returns 200 when GEMINI_API_KEY is set."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        response = await client.get("/ready")

    assert response.status_code == 200
    data = await response.get_json()
    assert data["status"] == "ok"
    assert data["checks"]["gemini_api_key"] == "configured"


@pytest.mark.asyncio
async def test_ready_without_api_key(client) -> None:  # noqa: ANN001 — Quart test client
    """GET /ready returns 503 when GEMINI_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        response = await client.get("/ready")

    assert response.status_code == 503
    data = await response.get_json()
    assert data["status"] == "unavailable"


@pytest.mark.asyncio
async def test_tell_joke(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /tell-joke returns a joke."""
    with patch("src.frameworks.quart_app.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Why did Python cross the road?"
        response = await client.post("/tell-joke", json={})

    assert response.status_code == 200
    data = await response.get_json()
    assert data["joke"] == "Why did Python cross the road?"


@pytest.mark.asyncio
async def test_translate(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /translate returns structured translation."""
    mock_result = TranslationResult(
        original_text="Hello",
        translated_text="Bonjour",
        target_language="French",
        confidence="high",
    )
    with patch("src.frameworks.quart_app.translate_text", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_result
        response = await client.post("/translate", json={"text": "Hello", "target_language": "French"})

    assert response.status_code == 200
    data = await response.get_json()
    assert data["translated_text"] == "Bonjour"


@pytest.mark.asyncio
async def test_describe_image(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /describe-image returns image description."""
    with patch("src.frameworks.quart_app.describe_image", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A colorful image"
        response = await client.post("/describe-image", json={})

    assert response.status_code == 200
    data = await response.get_json()
    assert data["description"] == "A colorful image"


@pytest.mark.asyncio
async def test_generate_character(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /generate-character returns RPG character."""
    mock_char = RpgCharacter(
        name="Luna",
        backStory="A mage.",
        abilities=["Frost Bolt"],
        skills=Skills(strength=45, charisma=80, endurance=60),
    )
    with patch("src.frameworks.quart_app.generate_character", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_char
        response = await client.post("/generate-character", json={"name": "Luna"})

    assert response.status_code == 200
    data = await response.get_json()
    assert data["name"] == "Luna"


@pytest.mark.asyncio
async def test_chat(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /chat returns pirate-themed response."""
    with patch("src.frameworks.quart_app.pirate_chat", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Arrr, Python!"
        response = await client.post("/chat", json={"question": "Best language?"})

    assert response.status_code == 200
    data = await response.get_json()
    assert data["answer"] == "Arrr, Python!"


@pytest.mark.asyncio
async def test_generate_code(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /generate-code returns structured code output."""
    mock_output = CodeOutput(
        code="print('hi')",
        language="python",
        explanation="Prints hi.",
        filename="hello.py",
    )
    with patch("src.frameworks.quart_app.generate_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        response = await client.post(
            "/generate-code",
            json={"description": "print hello", "language": "python"},
        )

    assert response.status_code == 200
    data = await response.get_json()
    assert data["code"] == "print('hi')"


@pytest.mark.asyncio
async def test_review_code(client) -> None:  # noqa: ANN001 — Quart test client
    """POST /review-code returns review output."""
    mock_output = {"summary": "Clean code.", "issues": [], "rating": "A"}
    with patch("src.frameworks.quart_app.review_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        response = await client.post(
            "/review-code",
            json={"code": "def add(a, b): return a + b"},
        )

    assert response.status_code == 200
    data = await response.get_json()
    assert "summary" in data
