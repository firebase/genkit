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

"""Multipart tool support sample — regular vs multipart tools.

This sample demonstrates the difference between regular tools and multipart
tools (``tool.v2``). Regular tools return a single output value while multipart
tools return a dict with optional ``output`` and ``content`` fields, allowing
rich content alongside structured data.

How It Works
============
| Tool Type      | Decorator                        | Return Type           |
|----------------|----------------------------------|-----------------------|
| Regular        | ``@ai.tool()``                   | Any single value      |
| Multipart      | ``@ai.tool(multipart=True)``     | ``{output?, content?}`` |

Under the Hood
==============
- Regular tools register under both ``tool`` and ``tool.v2`` action kinds.
  The ``tool.v2`` wrapper wraps the output in ``{output: result}``.
- Multipart tools register under ``tool.v2`` only, with metadata
  ``type='tool.v2'`` and ``tool.multipart=True``.
- ``resolve_tool()`` checks both ``tool`` and ``tool.v2`` kinds, so either
  type of tool can be resolved by name.

Testing
=======
Run ``genkit start -- uv run src/main.py`` to launch the Dev UI, then invoke
the ``multipart_search`` or ``regular_search`` flows.
"""

from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.google_genai.models import gemini
from samples.shared.logging import setup_sample

setup_sample()

ai = Genkit(
    plugins=[GoogleAI()],
    model=f'googleai/{gemini.GoogleAIGeminiVersion.GEMINI_3_FLASH_PREVIEW}',
)


class SearchQuery(BaseModel):
    """Search query input."""

    query: str = Field(description='The search query string')


class SearchResult(BaseModel):
    """A single search result."""

    title: str = Field(description='Title of the result')
    url: str = Field(description='URL of the result')
    snippet: str = Field(description='Brief snippet from the result')


# A regular tool — returns a single string.
@ai.tool()
def get_summary(query: str) -> str:
    """Get a brief summary for a topic. Returns a concise one-line answer."""
    return f'Summary for "{query}": This is a simulated summary of the topic.'


# A multipart tool — returns both structured output AND rich content parts.
# The model sees this as a tool.v2 action with {output, content}.
@ai.tool(multipart=True)
def search_with_sources(query: SearchQuery) -> dict:
    """Search for information and return results with source citations.

    Returns both a structured summary (output) and detailed source
    citations (content parts) that the model can reference.
    """
    results = [
        SearchResult(
            title=f'Result 1: {query.query}',
            url=f'https://example.com/1?q={query.query}',
            snippet=f'First result about {query.query} with detailed information.',
        ),
        SearchResult(
            title=f'Result 2: {query.query}',
            url=f'https://example.com/2?q={query.query}',
            snippet=f'Second result covering {query.query} from another perspective.',
        ),
    ]

    return {
        'output': f'Found {len(results)} results for "{query.query}"',
        'content': [{'text': f'Source: {r.title}\nURL: {r.url}\n{r.snippet}\n'} for r in results],
    }


@ai.flow()
async def multipart_search(topic: str) -> str:
    """Search using the multipart tool and summarize with sources."""
    response = await ai.generate(
        prompt=f'Search for information about "{topic}" using the search_with_sources '
        'tool, then provide a comprehensive answer citing the sources.',
        tools=['search_with_sources'],
    )
    return response.text


@ai.flow()
async def regular_search(topic: str) -> str:
    """Search using the regular tool for comparison."""
    response = await ai.generate(
        prompt=f'Get a summary about "{topic}" using the get_summary tool.',
        tools=['get_summary'],
    )
    return response.text


async def main() -> None:
    """Run both flows to compare regular vs multipart tools."""
    result = await multipart_search('python async programming')
    print(f'Multipart result:\n{result}\n')  # noqa: T201 - sample CLI output

    result = await regular_search('python async programming')
    print(f'Regular result:\n{result}')  # noqa: T201 - sample CLI output


if __name__ == '__main__':
    ai.run_main(main())
