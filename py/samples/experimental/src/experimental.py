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

"""Experimental Genkit API in both synchronous and asynchronous contexts."""

import asyncio
import inspect

from genkit.ai import GenkitExperimental
from genkit.aio import GenkitAsync
from genkit.sync import GenkitSync

genkit = GenkitExperimental()


@genkit.flow('async_flow')
async def async_flow(ai: GenkitAsync, query: str) -> dict[str, str]:
    """Asynchronous flow."""
    response = await ai.generate(f'Answer this: {query}')
    return {'answer': response['text']}


@genkit.flow('sync_flow')
def sync_flow(ai: GenkitSync, query: str) -> dict[str, str]:
    """Generate a response to a question using the sync flow."""
    print(f'Generating response to: {query}')
    result = ai.generate(query)
    if isinstance(result, dict) and 'text' in result:
        return {'answer': result['text']}
    return {'answer': f'Sync response to: {query}'}


@genkit.flow()
async def another_async_flow(ai: GenkitAsync, query: str) -> dict[str, str]:
    """Generate a response to a question using the async flow."""
    print(f'Generating response to: {query}')
    result = await ai.generate(query)
    if isinstance(result, dict) and 'text' in result:
        return {'answer': result['text']}
    return {'answer': f'Async response to: {query}'}


@genkit.flow()
def another_sync_flow(ai: GenkitSync, query: str) -> dict[str, str]:
    """Generate a response to a question using the sync flow."""
    print(f'Generating response to: {query}')
    result = ai.generate(query)
    if isinstance(result, dict) and 'text' in result:
        return {'answer': result['text']}
    return {'answer': f'Sync response to: {query}'}


async def main() -> None:
    """Entrypoint for the example usage."""
    async_result = await async_flow('What is the capital of the United States?')
    print(f'Async flow result: {async_result}')

    sync_result = sync_flow('What is the capital of the United States?')
    print(f'Sync flow result: {sync_result}')


def test_direct_sync() -> dict[str, str]:
    """Test direct sync API usage in a non-async context."""
    result = genkit.sync.generate('Direct sync call')
    if inspect.iscoroutine(result):
        try:
            result = asyncio.run(result)
        except Exception as e:
            print(f'Error in direct sync call: {e}')
            result = {'text': 'Direct sync call fallback response'}
    if isinstance(result, dict) and 'text' in result:
        return {'answer': result['text']}
    return {'answer': 'Direct sync fallback response'}


if __name__ == '__main__':
    asyncio.run(main())

    direct_sync_result = test_direct_sync()
    print(f'Direct sync result: {direct_sync_result}')
