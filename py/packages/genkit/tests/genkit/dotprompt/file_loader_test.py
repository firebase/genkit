# Copyright 2025 Google LLC
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

"""Tests for standalone dotprompt file loading utilities."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from genkit.ai import Genkit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _simple_prompt_frontmatter(model: str = 'echoModel') -> str:
    return (
        "---\n"
        f"model: {model}\n"
        "input:\n"
        "  schema:\n"
        "    type: object\n"
        "---\n\n"
    )


def test_load_prompt_dir_parses_files_and_variants(tmp_path: Path) -> None:
    prompts_dir = tmp_path / 'prompts'

    # Partial
    _write(
        prompts_dir / '_personality.prompt',
        _simple_prompt_frontmatter() + "Talk like a {{#if style}}{{style}}{{else}}helpful assistant{{/if}}.\n",
    )

    # Regular prompt
    _write(
        prompts_dir / 'hello.prompt',
        _simple_prompt_frontmatter() + "Hello {{name}}!\n",
    )

    # Variant prompt
    _write(
        prompts_dir / 'my.formal.prompt',
        _simple_prompt_frontmatter() + "Good day, {{name}}.\n",
    )

    # Subdirectory prompt
    _write(
        prompts_dir / 'sub' / 'bye.prompt',
        _simple_prompt_frontmatter() + "Bye {{name}}.\n",
    )

    ai = Genkit(model='echoModel')

    loaded = ai.load_prompt_dir(str(prompts_dir))

    # Keys should mirror JS: name.variant with subdir prefix in name
    assert set(loaded.keys()) == {"hello", "my.formal", "sub/bye"}

    assert loaded["hello"].id.name == "hello"
    assert loaded["hello"].id.variant is None
    assert loaded["hello"].id.ns is None

    assert loaded["my.formal"].id.name == "my"
    assert loaded["my.formal"].id.variant == "formal"

    assert loaded["sub/bye"].id.name == "sub/bye"
    assert loaded["sub/bye"].id.variant is None


@pytest.mark.asyncio
async def test_aload_prompt_dir_renders_metadata(tmp_path: Path) -> None:
    prompts_dir = tmp_path / 'prompts'

    _write(
        prompts_dir / 'info.prompt',
        _simple_prompt_frontmatter() + "This is a prompt that renders metadata.\n",
    )

    ai = Genkit(model='echoModel')

    loaded = await ai.aload_prompt_dir(str(prompts_dir), with_metadata=True)

    assert "info" in loaded
    assert loaded["info"].metadata is not None
    assert isinstance(loaded["info"].metadata, dict)


def test_name_and_variant_parsing_with_multiple_dots(tmp_path: Path) -> None:
    prompts_dir = tmp_path / 'prompts'

    _write(
        prompts_dir / 'a.b.c.prompt',
        _simple_prompt_frontmatter() + "Testing names with multiple dots.\n",
    )

    ai = Genkit(model='echoModel')
    loaded = ai.load_prompt_dir(str(prompts_dir))

    # Current behavior matches JS-like split: name=a, variant=b; the rest is ignored.
    assert set(loaded.keys()) == {"a.b"}
    assert loaded["a.b"].id.name == "a"
    assert loaded["a.b"].id.variant == "b"


