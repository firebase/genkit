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

"""Context caching - reuse a large source document across follow-up prompts."""

import asyncio
import os
import pathlib

import httpx
from pydantic import BaseModel, Field

from genkit import Genkit, Message, Part, Role, TextPart
from genkit.plugins.google_genai import GoogleAI

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-3-pro-preview')

DEFAULT_TEXT_FILE = 'https://www.gutenberg.org/cache/epub/74/pg74.txt'


class CachedTextInput(BaseModel):
    """Input for the context caching flow."""

    query: str = Field(
        default='What do Tom Sawyer and Huck Finn value differently?',
        description='Question to ask about the cached text',
    )
    text_file_path: str = Field(default=DEFAULT_TEXT_FILE, description='Local path or URL for the source text')


async def _load_text(path: str) -> str:
    """Load text from either a URL or a local file."""

    if path.startswith('http'):
        async with httpx.AsyncClient() as client:
            response = await client.get(path)
            response.raise_for_status()
            return response.text
    return pathlib.Path(path).read_text(encoding='utf-8')


@ai.flow(name='text_context_flow')
async def text_context_flow(input: CachedTextInput) -> str:
    """Cache a large text once, then ask a follow-up question against the same history."""

    source_text = await _load_text(input.text_file_path)
    cached_history = [
        Message(role=Role.USER, content=[Part(root=TextPart(text=source_text))]),
        Message(
            role=Role.MODEL,
            content=[Part(root=TextPart(text='Source document cached for follow-up questions.'))],
            metadata={'cache': {'ttl_seconds': 300}},
        ),
    ]

    answer = await ai.generate(messages=cached_history, prompt=input.query)
    short_answer = await ai.generate(messages=answer.messages, prompt='Now answer again in one sentence.')

    return f'Answer:\n{answer.text}\n\nOne sentence version:\n{short_answer.text}'


async def main() -> None:
    """Keep the sample process alive for Dev UI."""

    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
