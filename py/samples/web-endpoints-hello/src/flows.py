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

"""Genkit tools and flows.

Tools give LLMs access to external data. When registered with
``@ai.tool()``, the tool's name, description, and input schema are
sent to the model as part of the generation request.

Flows are the orchestration layer — they call models, tools, and
sub-flows, and their execution is fully traced in the Genkit DevUI.

Resilience:

- **Caching** — Idempotent flows (translate, describe-image,
  generate-character, generate-code, review-code) use the shared
  ``FlowCache`` to avoid redundant LLM calls for identical inputs.
- **Circuit breaker** — All ``ai.generate()`` calls route through the
  shared ``CircuitBreaker`` so that a degraded LLM API fails fast
  instead of blocking all workers.

Both are optional — when running outside ``main()`` (e.g. in tests),
the resilience singletons are ``None`` and flows call the LLM directly.
"""

from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog
from pydantic import BaseModel

from genkit.blocks.interfaces import Output
from genkit.core.action import ActionRunContext
from genkit.types import Media, MediaPart, Message, Part, Role, TextPart

from . import resilience
from .app_init import ai
from .schemas import (
    CharacterInput,
    ChatInput,
    CodeInput,
    CodeOutput,
    CodeReviewInput,
    ImageInput,
    JokeInput,
    RpgCharacter,
    StoryInput,
    TranslateInput,
    TranslationResult,
)
from .util.date import utc_now_str

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@ai.tool()
def get_current_time() -> str:
    """Get the current date and time in UTC.

    The model can call this tool to include real-time information
    in its responses — e.g. "As of 2026-02-07 22:15 UTC ...".

    This is a sync tool (no async needed) since ``datetime.now()``
    is non-blocking.  Genkit supports both sync and async tools.
    """
    return utc_now_str()


async def _with_breaker(call: Callable[[], Awaitable[T]]) -> T:
    """Call through the circuit breaker if available.

    Wraps any async callable through the shared ``CircuitBreaker``,
    preserving the callable's return type via generics.  Falls back
    to a direct call when the breaker is not initialized (e.g. during
    unit tests or when ``main()`` hasn't run).
    """
    if resilience.llm_breaker is not None:
        return await resilience.llm_breaker.call(call)
    return await call()


async def _cached_call(
    flow_name: str,
    input_data: BaseModel | dict[str, object] | str,
    call: Callable[[], Awaitable[T]],
) -> T:
    """Run ``call`` through the response cache if available.

    Falls back to a direct call when the cache is not initialized.
    """
    if resilience.flow_cache is not None:
        return await resilience.flow_cache.get_or_call(flow_name, input_data, call)
    return await call()


@ai.flow()
async def tell_joke(input: JokeInput) -> str:
    """Generate a joke about the given name using Gemini.

    The ``username`` field in the input allows personalization when
    called from a FastAPI route that forwards the Authorization header.

    Not cached — jokes should feel fresh on every call.
    """
    username = input.username or "anonymous"
    response = await _with_breaker(
        lambda: ai.generate(
            prompt=f"Tell a medium-length joke about {input.name} for user {username}.",
        )
    )
    return response.text


@ai.flow()
async def translate_text(
    input: TranslateInput,
    ctx: ActionRunContext | None = None,
) -> TranslationResult:
    """Translate text using Gemini with structured output.

    This flow demonstrates three Genkit features in one:

    1. **Structured output** — ``Output(schema=TranslationResult)`` tells
       the model to return JSON matching the Pydantic schema.
    2. **Tool use** — the ``get_current_time`` tool is available so the model
       can note *when* the translation was produced.
    3. **Traced steps** — ``ai.run()`` wraps a pre-processing step as a
       discrete sub-span visible in the Genkit DevUI traces.

    Cached — identical text + target language returns the same translation.
    """

    async def _call() -> TranslationResult:
        sanitized_text = await ai.run(
            "sanitize-input",
            input.text,
            lambda text: text.strip()[:2000],
        )
        response = await _with_breaker(
            lambda: ai.generate(
                prompt=(
                    f"Translate the following text to {input.target_language}. "
                    f"Use the get_current_time tool to note when the translation was done.\n\n"
                    f"Text: {sanitized_text}"
                ),
                tools=["get_current_time"],
                output=Output(schema=TranslationResult),
            )
        )
        return response.output

    return await _cached_call("translate_text", input, _call)


@ai.flow()
async def describe_image(input: ImageInput) -> str:
    """Describe an image using multimodal generation.

    Sends both a text prompt and an image URL to Gemini in a single
    message, demonstrating multimodal input via ``MediaPart``.

    Cached — identical image URLs return the same description.
    """

    async def _call() -> str:
        response = await _with_breaker(
            lambda: ai.generate(
                messages=[
                    Message(
                        role=Role.USER,
                        content=[
                            Part(root=TextPart(text="Describe this image in detail.")),
                            Part(root=MediaPart(media=Media(url=input.image_url, content_type="image/jpeg"))),
                        ],
                    )
                ],
            )
        )
        return response.text

    return await _cached_call("describe_image", input, _call)


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character with structured output.

    Uses ``Output(schema=RpgCharacter)`` to get the model to return
    a fully-typed Pydantic object with name, backstory, abilities,
    and skill stats — no manual JSON parsing needed.

    Cached — identical character names return the same character.
    """

    async def _call() -> RpgCharacter:
        result = await _with_breaker(
            lambda: ai.generate(
                prompt=f"Generate a creative RPG character named {input.name}. Output ONLY the JSON object.",
                output=Output(schema=RpgCharacter),
            )
        )
        return result.output

    return await _cached_call("generate_character", input, _call)


@ai.flow()
async def pirate_chat(input: ChatInput) -> str:
    """Answer a question as a pirate captain using a system prompt.

    The ``system=`` parameter sets the model's persona before
    generation. This is how you control tone, style, and behavior
    without modifying the user's prompt.

    Not cached — chat should feel conversational.
    """
    response = await _with_breaker(
        lambda: ai.generate(
            prompt=input.question,
            system=(
                "You are a pirate captain from the 18th century. "
                "Always respond in character, using pirate slang and nautical terminology."
            ),
        )
    )
    return response.text


@ai.flow()
async def tell_story(
    input: StoryInput,
    ctx: ActionRunContext | None = None,
) -> str:
    """Generate a short story with Genkit-native streaming.

    Uses ``on_chunk`` + ``ctx.send_chunk()`` so callers can invoke
    this flow via ``tell_story.stream()`` and receive chunks through
    Genkit's action streaming infrastructure.

    Not cached — streaming flows are not cacheable.
    Circuit breaker is not applied to streaming (generate_stream).
    """
    stream, result = ai.generate_stream(
        prompt=f"Write a short story (3-4 paragraphs) about {input.topic}.",
    )
    async for chunk in stream:
        if ctx is not None:
            ctx.send_chunk(chunk.text)
    return (await result).text


@ai.flow()
async def generate_code(input: CodeInput) -> CodeOutput:
    """Generate code from a natural language description.

    Uses structured output to return the code, language, explanation,
    and a suggested filename — all enforced by a Pydantic schema.

    Cached — identical descriptions + language return the same code.
    """

    async def _call() -> CodeOutput:
        result = await _with_breaker(
            lambda: ai.generate(
                prompt=(
                    f"Generate {input.language} code for: {input.description}\n\n"
                    "Requirements:\n"
                    "- Write clean, idiomatic, production-quality code\n"
                    "- Include docstrings/comments where helpful\n"
                    "- Follow language conventions and best practices\n"
                    "- Suggest an appropriate filename\n"
                    "- Explain what the code does briefly"
                ),
                output=Output(schema=CodeOutput),
            )
        )
        return result.output

    return await _cached_call("generate_code", input, _call)


@ai.flow()
async def review_code(input: CodeReviewInput) -> dict:
    """Review code using a Dotprompt loaded from prompts/code_review.prompt.

    This demonstrates the prompt management system:
    1. Genkit auto-loads .prompt files from the ``prompts/`` directory
    2. ``ai.prompt('code_review')`` retrieves the loaded prompt by name
    3. The prompt template, model config, and output schema are all
       defined in the .prompt file — not in Python code
    4. Calling the prompt executes it and returns structured output

    Cached — identical code + language returns the same review.
    """

    async def _call() -> dict:
        code_review_prompt = ai.prompt("code_review")
        response = await code_review_prompt(
            input={"code": input.code, "language": input.language or ""},
        )
        return response.output

    return await _cached_call("review_code", input, _call)
