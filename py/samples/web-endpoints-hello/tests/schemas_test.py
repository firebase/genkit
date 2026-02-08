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

"""Tests for Pydantic schema input validation and constraints.

Covers the ``Field`` constraints added for input hardening:
``max_length``, ``min_length``, ``ge``/``le``, ``pattern``, and
``max_length`` on list fields.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/schemas_test.py -v
"""

import pytest
from pydantic import ValidationError

from src.schemas import (
    CharacterInput,
    ChatInput,
    CodeInput,
    CodeReviewInput,
    ImageInput,
    JokeInput,
    RpgCharacter,
    Skills,
    StoryInput,
    TranslateInput,
)


def test_joke_input_defaults() -> None:
    """JokeInput has sensible defaults."""
    inp = JokeInput()
    assert inp.name == "Mittens"
    assert inp.username is None


def test_joke_input_name_max_length() -> None:
    """JokeInput rejects names exceeding max_length."""
    with pytest.raises(ValidationError):
        JokeInput(name="x" * 201)


def test_joke_input_username_max_length() -> None:
    """JokeInput rejects usernames exceeding max_length."""
    with pytest.raises(ValidationError):
        JokeInput(username="u" * 201)


def test_joke_input_accepts_valid_name() -> None:
    """JokeInput accepts names within limits."""
    inp = JokeInput(name="Waffles", username="alice")
    assert inp.name == "Waffles"
    assert inp.username == "alice"


def test_translate_input_defaults() -> None:
    """TranslateInput has default text and default language."""
    inp = TranslateInput()
    assert "Northern Lights" in inp.text
    assert inp.target_language == "French"


def test_translate_input_text_min_length() -> None:
    """TranslateInput rejects empty text."""
    with pytest.raises(ValidationError):
        TranslateInput(text="")


def test_translate_input_text_max_length() -> None:
    """TranslateInput rejects text exceeding max_length."""
    with pytest.raises(ValidationError):
        TranslateInput(text="x" * 10_001)


def test_translate_input_language_max_length() -> None:
    """TranslateInput rejects languages exceeding max_length."""
    with pytest.raises(ValidationError):
        TranslateInput(text="Hello", target_language="x" * 101)


def test_image_input_defaults() -> None:
    """ImageInput has a valid default URL."""
    inp = ImageInput()
    assert inp.image_url.startswith("https://")


def test_image_input_url_max_length() -> None:
    """ImageInput rejects URLs exceeding max_length."""
    with pytest.raises(ValidationError):
        ImageInput(image_url="https://example.com/" + "x" * 2048)


def test_character_input_defaults() -> None:
    """CharacterInput has a default name."""
    inp = CharacterInput()
    assert inp.name == "Luna"


def test_character_input_name_min_length() -> None:
    """CharacterInput rejects empty names."""
    with pytest.raises(ValidationError):
        CharacterInput(name="")


def test_character_input_name_max_length() -> None:
    """CharacterInput rejects names exceeding max_length."""
    with pytest.raises(ValidationError):
        CharacterInput(name="x" * 201)


def test_skills_valid_range() -> None:
    """Skills accepts values within 0-100."""
    s = Skills(strength=0, charisma=50, endurance=100)
    assert s.strength == 0
    assert s.charisma == 50
    assert s.endurance == 100


def test_skills_rejects_negative() -> None:
    """Skills rejects negative values."""
    with pytest.raises(ValidationError):
        Skills(
            strength=-1,  # pyrefly: ignore[bad-argument-type] — intentional violation to test Pydantic validation
            charisma=50,
            endurance=50,
        )


def test_skills_rejects_over_100() -> None:
    """Skills rejects values over 100."""
    with pytest.raises(ValidationError):
        Skills(
            strength=50,
            charisma=101,  # pyrefly: ignore[bad-argument-type] — intentional violation to test Pydantic validation
            endurance=50,
        )


def test_rpg_character_abilities_max_length() -> None:
    """RpgCharacter rejects more than 10 abilities."""
    with pytest.raises(ValidationError):
        RpgCharacter(
            name="Luna",
            backStory="A mage",
            abilities=["ability"] * 11,
            skills=Skills(strength=50, charisma=50, endurance=50),
        )


def test_rpg_character_accepts_valid() -> None:
    """RpgCharacter accepts valid data."""
    char = RpgCharacter(
        name="Luna",
        backStory="A mysterious mage.",
        abilities=["Frost Bolt", "Teleport"],
        skills=Skills(strength=45, charisma=80, endurance=60),
    )
    assert char.name == "Luna"
    assert len(char.abilities) == 2


def test_chat_input_defaults() -> None:
    """ChatInput has a default question."""
    inp = ChatInput()
    assert inp.question == "What is the best programming language?"


def test_chat_input_question_min_length() -> None:
    """ChatInput rejects empty questions."""
    with pytest.raises(ValidationError):
        ChatInput(question="")


def test_chat_input_question_max_length() -> None:
    """ChatInput rejects questions exceeding max_length."""
    with pytest.raises(ValidationError):
        ChatInput(question="x" * 5_001)


def test_story_input_defaults() -> None:
    """StoryInput has a default topic."""
    inp = StoryInput()
    assert inp.topic == "a brave cat"


def test_story_input_topic_min_length() -> None:
    """StoryInput rejects empty topics."""
    with pytest.raises(ValidationError):
        StoryInput(topic="")


def test_story_input_topic_max_length() -> None:
    """StoryInput rejects topics exceeding max_length."""
    with pytest.raises(ValidationError):
        StoryInput(topic="x" * 1_001)


def test_code_input_defaults() -> None:
    """CodeInput has defaults for both fields."""
    inp = CodeInput()
    assert inp.language == "python"
    assert inp.description


def test_code_input_description_min_length() -> None:
    """CodeInput rejects empty descriptions."""
    with pytest.raises(ValidationError):
        CodeInput(description="")


def test_code_input_description_max_length() -> None:
    """CodeInput rejects descriptions exceeding max_length."""
    with pytest.raises(ValidationError):
        CodeInput(description="x" * 10_001)


def test_code_input_language_pattern() -> None:
    """CodeInput language accepts valid patterns (letters, #, +)."""
    for lang in ["python", "javascript", "go", "rust", "csharp", "cpp"]:
        inp = CodeInput(language=lang)
        assert inp.language == lang


def test_code_input_language_rejects_injection() -> None:
    """CodeInput language rejects strings with special characters."""
    for bad in ["python; rm -rf /", "go && echo hi", "python\n", "py thon"]:
        with pytest.raises(ValidationError):
            CodeInput(language=bad)


def test_code_input_language_max_length() -> None:
    """CodeInput rejects languages exceeding max_length."""
    with pytest.raises(ValidationError):
        CodeInput(language="x" * 51)


def test_code_review_input_defaults() -> None:
    """CodeReviewInput has a default code snippet."""
    inp = CodeReviewInput()
    assert "def add" in inp.code
    assert inp.language is None


def test_code_review_input_code_min_length() -> None:
    """CodeReviewInput rejects empty code."""
    with pytest.raises(ValidationError):
        CodeReviewInput(code="")


def test_code_review_input_code_max_length() -> None:
    """CodeReviewInput rejects code exceeding max_length."""
    with pytest.raises(ValidationError):
        CodeReviewInput(code="x" * 50_001)


def test_code_review_input_language_max_length() -> None:
    """CodeReviewInput rejects languages exceeding max_length."""
    with pytest.raises(ValidationError):
        CodeReviewInput(language="x" * 51)
