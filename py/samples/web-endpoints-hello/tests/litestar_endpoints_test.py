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

"""Unit tests for the Litestar endpoint adapter.

Mirrors the FastAPI endpoint tests to ensure Litestar routes behave
identically.  Uses Litestar's built-in TestClient.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/litestar_endpoints_test.py -v
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litestar.testing import TestClient

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

            from src.frameworks.litestar_app import create_app
            from src.schemas import (
                CodeOutput,
                RpgCharacter,
                Skills,
                TranslationResult,
            )

            _app = create_app(_mock_ai)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a Litestar test client."""
    with TestClient(app=_app) as c:
        yield c


def test_health(client: TestClient) -> None:
    """GET /health returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_with_api_key(client: TestClient) -> None:
    """GET /ready returns 200 when GEMINI_API_KEY is set."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        response = client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["gemini_api_key"] == "configured"


def test_ready_without_api_key(client: TestClient) -> None:
    """GET /ready returns 503 when GEMINI_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        response = client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unavailable"


def test_tell_joke(client: TestClient) -> None:
    """POST /tell-joke returns a joke."""
    with patch("src.frameworks.litestar_app.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Why did Python cross the road?"
        response = client.post("/tell-joke", json={})

    assert response.status_code == 201
    data = response.json()
    assert data["joke"] == "Why did Python cross the road?"


def test_translate(client: TestClient) -> None:
    """POST /translate returns structured translation."""
    mock_result = TranslationResult(
        original_text="Hello",
        translated_text="Bonjour",
        target_language="French",
        confidence="high",
    )
    with patch("src.frameworks.litestar_app.translate_text", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_result
        response = client.post("/translate", json={"text": "Hello", "target_language": "French"})

    assert response.status_code == 201
    data = response.json()
    assert data["translated_text"] == "Bonjour"


def test_describe_image(client: TestClient) -> None:
    """POST /describe-image returns image description."""
    with patch("src.frameworks.litestar_app.describe_image", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A colorful image"
        response = client.post("/describe-image", json={})

    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "A colorful image"


def test_generate_character(client: TestClient) -> None:
    """POST /generate-character returns RPG character."""
    mock_char = RpgCharacter(
        name="Luna",
        backStory="A mage.",
        abilities=["Frost Bolt"],
        skills=Skills(strength=45, charisma=80, endurance=60),
    )
    with patch("src.frameworks.litestar_app.generate_character", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_char
        response = client.post("/generate-character", json={"name": "Luna"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Luna"


def test_chat(client: TestClient) -> None:
    """POST /chat returns pirate-themed response."""
    with patch("src.frameworks.litestar_app.pirate_chat", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Arrr, Python!"
        response = client.post("/chat", json={"question": "Best language?"})

    assert response.status_code == 201
    data = response.json()
    assert data["answer"] == "Arrr, Python!"


def test_generate_code(client: TestClient) -> None:
    """POST /generate-code returns structured code output."""
    mock_output = CodeOutput(
        code="print('hi')",
        language="python",
        explanation="Prints hi.",
        filename="hello.py",
    )
    with patch("src.frameworks.litestar_app.generate_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        response = client.post(
            "/generate-code",
            json={"description": "print hello", "language": "python"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "print('hi')"


def test_review_code(client: TestClient) -> None:
    """POST /review-code returns review output."""
    mock_output = {"summary": "Clean code.", "issues": [], "rating": "A"}
    with patch("src.frameworks.litestar_app.review_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        response = client.post(
            "/review-code",
            json={"code": "def add(a, b): return a + b"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "summary" in data
