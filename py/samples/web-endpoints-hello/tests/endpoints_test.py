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

"""Unit tests for the Genkit endpoints sample (FastAPI REST).

Uses httpx.AsyncClient with FastAPI's TestClient pattern to test all
endpoints without needing a running server or real Gemini API calls.
All Genkit AI calls are mocked to return deterministic responses.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/ -v
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# The app import triggers module-level code in app_init.py (Genkit init, etc.),
# so we must mock the Google AI plugin and GEMINI_API_KEY before importing.
# By importing the module, we make sure it's available in the namespace
# for the patcher.

with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "GENKIT_ENV": "test"}):
    with patch("genkit.plugins.google_genai.GoogleAI", return_value=MagicMock()):
        with patch("genkit.ai.Genkit") as MockGenkit:
            mock_ai = MagicMock()
            mock_ai.flow.return_value = lambda fn: fn
            mock_ai.tool.return_value = lambda fn: fn
            mock_ai.prompt.return_value = AsyncMock(
                return_value=MagicMock(output={"summary": "Looks good", "issues": [], "rating": "A"})
            )
            MockGenkit.return_value = mock_ai

            from src.app_init import ai
            from src.frameworks.fastapi_app import create_app
            from src.schemas import (
                CharacterInput,
                ChatInput,
                CodeInput,
                CodeOutput,
                ImageInput,
                JokeInput,
                RpgCharacter,
                Skills,
                StoryInput,
                TranslateInput,
                TranslationResult,
            )

            app = create_app(ai)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Health endpoint returns 200 with status ok."""
    response = await client.get("/health")
    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if data != {"status": "ok"}:
        pytest.fail(f'Expected {{"status": "ok"}}, got {data}')


@pytest.mark.asyncio
async def test_tell_joke_default(client: AsyncClient) -> None:
    """POST /tell-joke with empty body uses defaults."""
    with patch("src.frameworks.fastapi_app.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Why did Mittens cross the road?"
        response = await client.post("/tell-joke", json={})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if "joke" not in data:
        pytest.fail(f'Missing "joke" key in response: {data}')
    if data["joke"] != "Why did Mittens cross the road?":
        pytest.fail(f"Unexpected joke: {data['joke']}")


@pytest.mark.asyncio
async def test_tell_joke_custom_name(client: AsyncClient) -> None:
    """POST /tell-joke with a custom name."""
    with patch("src.frameworks.fastapi_app.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Waffles walked into a bar..."
        response = await client.post("/tell-joke", json={"name": "Waffles"})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if data["joke"] != "Waffles walked into a bar...":
        pytest.fail(f"Unexpected joke: {data['joke']}")


@pytest.mark.asyncio
async def test_tell_joke_with_auth(client: AsyncClient) -> None:
    """POST /tell-joke with Authorization header passes username through."""
    with patch("src.frameworks.fastapi_app.tell_joke", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A joke for Alice"
        response = await client.post(
            "/tell-joke",
            json={"name": "Mittens"},
            headers={"Authorization": "Alice"},
        )

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if data.get("username") != "Alice":
        pytest.fail(f'Expected username "Alice", got {data.get("username")}')


@pytest.mark.asyncio
async def test_translate(client: AsyncClient) -> None:
    """POST /translate returns structured translation result."""
    mock_result = TranslationResult(
        original_text="Hello!",
        translated_text="Bonjour!",
        target_language="French",
        confidence="high",
    )
    with patch("src.frameworks.fastapi_app.translate_text", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_result
        response = await client.post("/translate", json={"text": "Hello!", "target_language": "French"})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if data["translated_text"] != "Bonjour!":
        pytest.fail(f"Unexpected translation: {data}")
    if data["confidence"] != "high":
        pytest.fail(f"Unexpected confidence: {data['confidence']}")


@pytest.mark.asyncio
async def test_describe_image(client: AsyncClient) -> None:
    """POST /describe-image returns image description."""
    with patch("src.frameworks.fastapi_app.describe_image", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "A colorful dice on a checkered background"
        response = await client.post("/describe-image", json={})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if "description" not in data:
        pytest.fail(f'Missing "description" key: {data}')
    if "image_url" not in data:
        pytest.fail(f'Missing "image_url" key: {data}')


@pytest.mark.asyncio
async def test_generate_character(client: AsyncClient) -> None:
    """POST /generate-character returns structured RPG character."""
    mock_char = RpgCharacter(
        name="Luna",
        backStory="A mysterious mage from the northern wastes.",
        abilities=["Frost Bolt", "Teleport", "Shield"],
        skills=Skills(strength=45, charisma=80, endurance=60),
    )
    with patch("src.frameworks.fastapi_app.generate_character", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_char
        response = await client.post("/generate-character", json={"name": "Luna"})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if data["name"] != "Luna":
        pytest.fail(f"Unexpected name: {data['name']}")
    if "abilities" not in data:
        pytest.fail(f'Missing "abilities" key: {data}')


@pytest.mark.asyncio
async def test_chat(client: AsyncClient) -> None:
    """POST /chat returns pirate-themed response."""
    with patch("src.frameworks.fastapi_app.pirate_chat", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = "Arrr, Python be the finest language on the seven seas!"
        response = await client.post("/chat", json={"question": "What is the best programming language?"})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if "answer" not in data:
        pytest.fail(f'Missing "answer" key: {data}')
    if data["persona"] != "pirate captain":
        pytest.fail(f"Unexpected persona: {data['persona']}")


@pytest.mark.asyncio
async def test_generate_code(client: AsyncClient) -> None:
    """POST /generate-code returns structured code output."""
    prime_code = (
        "def is_prime(n):\n"
        "    if n < 2:\n"
        "        return False\n"
        "    for i in range(2, int(n**0.5) + 1):\n"
        "        if n % i == 0:\n"
        "            return False\n"
        "    return True"
    )
    mock_output = CodeOutput(
        code=prime_code,
        language="python",
        explanation="Checks divisibility up to sqrt(n).",
        filename="prime.py",
    )
    with patch("src.frameworks.fastapi_app.generate_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        response = await client.post(
            "/generate-code",
            json={"description": "check if a number is prime", "language": "python"},
        )

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if data["language"] != "python":
        pytest.fail(f"Unexpected language: {data['language']}")
    if "code" not in data:
        pytest.fail(f'Missing "code" key: {data}')
    if data["filename"] != "prime.py":
        pytest.fail(f"Unexpected filename: {data['filename']}")


@pytest.mark.asyncio
async def test_review_code(client: AsyncClient) -> None:
    """POST /review-code returns structured review output."""
    mock_output = {"summary": "Simple addition function.", "issues": [], "rating": "A"}
    with patch("src.frameworks.fastapi_app.review_code", new_callable=AsyncMock) as mock_flow:
        mock_flow.return_value = mock_output
        response = await client.post(
            "/review-code",
            json={"code": "def add(a, b):\n    return a + b", "language": "python"},
        )

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    data = response.json()
    if "summary" not in data:
        pytest.fail(f'Missing "summary" key: {data}')


@pytest.mark.asyncio
async def test_tell_joke_stream(client: AsyncClient) -> None:
    """POST /tell-joke/stream returns SSE events."""
    mock_chunk = MagicMock()
    mock_chunk.text = "Why"

    mock_final = MagicMock()
    mock_final.text = "Why did the chicken cross the road?"

    async def mock_stream() -> AsyncGenerator[MagicMock, None]:
        yield mock_chunk

    async def mock_response_future() -> MagicMock:
        return mock_final

    with patch.object(mock_ai, "generate_stream", return_value=(mock_stream(), mock_response_future())):
        response = await client.post("/tell-joke/stream", json={"name": "Chicken"})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" not in content_type:
        pytest.fail(f"Expected text/event-stream, got {content_type}")


def test_joke_input_defaults() -> None:
    """JokeInput has sensible defaults."""
    inp = JokeInput()
    if inp.name != "Mittens":
        pytest.fail(f'Expected default name "Mittens", got {inp.name!r}')
    if inp.username is not None:
        pytest.fail(f"Expected username None, got {inp.username!r}")


def test_translate_input_defaults() -> None:
    """TranslateInput requires text, has default language."""
    inp = TranslateInput(text="Hello")
    if inp.target_language != "French":
        pytest.fail(f'Expected default language "French", got {inp.target_language!r}')


def test_chat_input_defaults() -> None:
    """ChatInput has a default question."""
    inp = ChatInput()
    if not inp.question:
        pytest.fail("Expected a non-empty default question")


def test_story_input_defaults() -> None:
    """StoryInput has a default topic."""
    inp = StoryInput()
    if inp.topic != "a brave cat":
        pytest.fail(f'Expected default topic "a brave cat", got {inp.topic!r}')


def test_code_input_defaults() -> None:
    """CodeInput has defaults for both fields."""
    inp = CodeInput()
    if inp.language != "python":
        pytest.fail(f'Expected default language "python", got {inp.language!r}')
    if not inp.description:
        pytest.fail("Expected a non-empty default description")


def test_character_input_defaults() -> None:
    """CharacterInput has a default name."""
    inp = CharacterInput()
    if inp.name != "Luna":
        pytest.fail(f'Expected default name "Luna", got {inp.name!r}')


def test_image_input_defaults() -> None:
    """ImageInput has a default image URL."""
    inp = ImageInput()
    if not inp.image_url.startswith("https://"):
        pytest.fail(f"Expected a valid HTTPS URL, got {inp.image_url!r}")


@pytest.mark.asyncio
async def test_ready_with_api_key(client: AsyncClient) -> None:
    """GET /ready returns 200 when GEMINI_API_KEY is set."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        response = await client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["gemini_api_key"] == "configured"


@pytest.mark.asyncio
async def test_ready_without_api_key(client: AsyncClient) -> None:
    """GET /ready returns 503 when GEMINI_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["checks"]["gemini_api_key"] == "missing"
