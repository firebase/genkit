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

"""Sample that demonstrates caching of generation context in Genkit

In this sample user actor supplies "Tom Sawyer" book content from Gutenberg library archive
and model caches this context.
As a result, model is capable to quickly relate to the book's content and answer the follow-up questions.
"""

import base64
import mimetypes

import httpx
import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI, googleai_name
from genkit.plugins.google_genai.models.gemini import GoogleAIGeminiVersion
from genkit.types import GenerationCommonConfig, Media, MediaPart, Message, Role, TextPart

logger = structlog.getLogger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model=googleai_name(GoogleAIGeminiVersion.GEMINI_3_FLASH_PREVIEW),
)


# Tom Sawyer is taken as a sample book here
DEFAULT_TEXT_FILE = 'https://www.gutenberg.org/cache/epub/74/pg74.txt'
DEFAULT_QUERY = "What are Huck Finn's views on society, and how do they contrast with Tom’s"


class BookContextInputSchema(BaseModel):
    query: str = Field(default=DEFAULT_QUERY, description='A question about the supplied text file')
    text_file_path: str = Field(
        default=DEFAULT_TEXT_FILE, description='Incoming reference to the text file (local or web)'
    )


@ai.flow(name='text_context_flow')
async def text_context_flow(_input: BookContextInputSchema) -> str:
    print(f'Starting flow with file: {_input.text_file_path}')
    mime_type, _ = mimetypes.guess_type(_input.text_file_path)
    if not mime_type:
        mime_type = 'text/plain'
    print(f'Detected MIME type: {mime_type}')
    if _input.text_file_path.startswith('http'):
        async with httpx.AsyncClient() as client:
            res = await client.get(_input.text_file_path)
            res.raise_for_status()
            content_part = TextPart(text=res.text)
            print(f'Fetched content from URL. Length: {len(res.text)} chars')
    else:
        # Fallback for local text files
        with open(_input.text_file_path, 'r', encoding='utf-8') as text_file:
            content_part = TextPart(text=text_file.read())

    print('Generating first response (with cache)...')
    llm_response = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[content_part],
            ),
            Message(
                role=Role.MODEL,
                content=[TextPart(text=f'Here is some analysis based on the text provided.')],
                metadata={
                    'cache': {
                        'ttl_seconds': 300,
                    }
                },
            ),
        ],
        config=GenerationCommonConfig(
            version='gemini-3-flash-preview',
            temperature=0.7,
            maxOutputTokens=1000,
            topK=50,
            topP=0.9,
            stopSequences=['END'],
        ),
        prompt=_input.query,
        return_tool_requests=False,
    )
    print('First response received.')

    messages_history = llm_response.messages

    print(f'First turn response: {llm_response.text}')

    print('Generating second response (pirate)...')
    llm_response2 = await ai.generate(
        messages=messages_history,
        prompt=(
            'Rewrite the previous summary as if a pirate wrote it. '
            'Structure it exactly like this:\n'
            '### 1. Section Name\n'
            '*   **Key Concept:** Description...\n'
            'Keep it concise, use pirate slang, but maintain the helpful advice.'
        ),
        config=GenerationCommonConfig(
            version='gemini-3-flash-preview',
            temperature=0.7,
            maxOutputTokens=1000,
            topK=50,
            topP=0.9,
            stopSequences=['END'],
        ),
    )
    print('Second response received.')

    separator = '-' * 80
    return (
        f'{separator}\n'
        f'### Standard Analysis\n\n{llm_response.text}\n\n'
        f'{separator}\n'
        f'### Pirate Version\n\n{llm_response2.text}\n'
        f'{separator}'
    )


async def main() -> None:
    """Main entry point for the context caching sample.

    This function demonstrates how to use context caching in Genkit for
    improved performance.
    """
    res = await text_context_flow(BookContextInputSchema())
    await logger.ainfo('foo', result=res)


if __name__ == '__main__':
    ai.run_main(main())
