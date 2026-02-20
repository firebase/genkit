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

"""Pydantic models shared between REST request validation and Genkit flow schemas.

All input models include ``Field`` constraints (``max_length``,
``min_length``, ``ge``/``le``, ``pattern``) so that Pydantic rejects
malformed input before it reaches any flow or LLM call. This is a
defense-in-depth layer on top of the ``MaxBodySizeMiddleware``.
"""

from pydantic import BaseModel, Field


class JokeInput(BaseModel):
    """Input for the joke endpoint."""

    name: str = Field(
        default="Mittens",
        description="Subject of the joke",
        max_length=200,
    )
    username: str | None = Field(
        default=None,
        description="Username for personalization",
        max_length=200,
    )


class JokeResponse(BaseModel):
    """Response from the joke endpoint."""

    joke: str = Field(description="AI-generated joke")
    username: str | None = Field(default=None, description="Username from Authorization header")


class TranslateInput(BaseModel):
    """Input for the translation endpoint."""

    text: str = Field(
        default=(
            "The Northern Lights, or Aurora Borealis, are one of nature's most "
            "spectacular displays. Charged particles from the Sun collide with "
            "gases in Earth's atmosphere, creating shimmering curtains of green, "
            "pink, and violet light that dance across the polar sky. For centuries, "
            "cultures around the world have woven myths and legends around these "
            "ethereal lights — the Vikings believed they were reflections of the "
            "Valkyries' armor, while the Sámi people considered them the energies "
            "of departed souls."
        ),
        description="Text to translate",
        min_length=1,
        max_length=10_000,
    )
    target_language: str = Field(
        default="French",
        description="Target language",
        max_length=100,
    )


class TranslationResult(BaseModel):
    """Structured translation output — the model returns this directly."""

    original_text: str = Field(description="Original input text")
    translated_text: str = Field(description="Translated text")
    target_language: str = Field(description="Language translated into")
    confidence: str = Field(description="Confidence level: high, medium, or low")


class ImageInput(BaseModel):
    """Input for the image description endpoint."""

    image_url: str = Field(
        default="https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png",
        description="URL of the image to describe",
        max_length=2048,
    )


class ImageResponse(BaseModel):
    """Response from the image description endpoint."""

    description: str = Field(description="Textual description of the image")
    image_url: str = Field(description="URL of the image that was described")


class CharacterInput(BaseModel):
    """Input for RPG character generation."""

    name: str = Field(
        default="Luna",
        description="Character name",
        min_length=1,
        max_length=200,
    )


class Skills(BaseModel):
    """Core character stats for an RPG character."""

    strength: int = Field(description="Strength (0-100)", ge=0, le=100)
    charisma: int = Field(description="Charisma (0-100)", ge=0, le=100)
    endurance: int = Field(description="Endurance (0-100)", ge=0, le=100)


class RpgCharacter(BaseModel):
    """Structured RPG character — returned directly by the model."""

    name: str = Field(description="Name of the character")
    back_story: str = Field(description="Character backstory", alias="backStory")
    abilities: list[str] = Field(description="List of abilities (3-4)", max_length=10)
    skills: Skills


class ChatInput(BaseModel):
    """Input for the chat endpoint."""

    question: str = Field(
        default="What is the best programming language?",
        description="Question to ask the AI",
        min_length=1,
        max_length=5_000,
    )


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    answer: str = Field(description="AI-generated answer")
    persona: str = Field(default="pirate captain", description="Active persona")


class StoryInput(BaseModel):
    """Input for the streaming story endpoint."""

    topic: str = Field(
        default="a brave cat",
        description="Topic for the story",
        min_length=1,
        max_length=1_000,
    )


class CodeInput(BaseModel):
    """Input for the code generation endpoint."""

    description: str = Field(
        default="a Python function that checks if a number is prime",
        description="Natural language description of the code to generate",
        min_length=1,
        max_length=10_000,
    )
    language: str = Field(
        default="python",
        description="Programming language (e.g. python, javascript, go, rust)",
        max_length=50,
        pattern=r"^[a-zA-Z#+]+$",
    )


class CodeOutput(BaseModel):
    """Structured output from code generation."""

    code: str = Field(description="The generated source code")
    language: str = Field(description="Programming language used")
    explanation: str = Field(description="Brief explanation of the code")
    filename: str = Field(description="Suggested filename (e.g. prime.py)")


class CodeReviewInput(BaseModel):
    """Input for the code review endpoint."""

    code: str = Field(
        default="def add(a, b):\n    return a + b",
        description="Source code to review",
        min_length=1,
        max_length=50_000,
    )
    language: str | None = Field(
        default=None,
        description="Programming language (auto-detected if omitted)",
        max_length=50,
    )
