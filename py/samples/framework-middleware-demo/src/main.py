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

"""Built-in middleware examples - retry, fallback, and more.

Run: GEMINI_API_KEY=... uv run python src/main.py
"""

import asyncio

from genkit import Genkit, fallback, retry
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(model='googleai/gemini-2.0-flash')


# -----------------------------------------------------------------------------
# Example 1: Retry with exponential backoff
# -----------------------------------------------------------------------------
async def retry_example() -> None:
    """Retry failed requests automatically."""
    response = await ai.generate(
        prompt='Say hello',
        use=[
            retry(
                max_retries=3,
                initial_delay_ms=1000,
                backoff_factor=2.0,
            )
        ],
    )
    print(f'Retry example: {response.text}')  # noqa: T201


# -----------------------------------------------------------------------------
# Example 2: Fallback to another model
# -----------------------------------------------------------------------------
async def fallback_example() -> None:
    """Fall back to a different model if primary fails."""
    response = await ai.generate(
        prompt='Say hello',
        use=[
            fallback(
                ai,
                models=['googleai/gemini-2.0-flash'],  # fallback model(s)
            )
        ],
    )
    print(f'Fallback example: {response.text}')  # noqa: T201


# -----------------------------------------------------------------------------
# Example 3: Combine retry + fallback
# -----------------------------------------------------------------------------
async def combined_example() -> None:
    """Retry first, then fallback if all retries fail."""
    response = await ai.generate(
        prompt='Say hello',
        use=[
            retry(max_retries=2, initial_delay_ms=500),
            fallback(ai, models=['googleai/gemini-2.0-flash']),
        ],
    )
    print(f'Combined example: {response.text}')  # noqa: T201


# -----------------------------------------------------------------------------
# Example 4: Custom middleware (for reference)
# -----------------------------------------------------------------------------
async def custom_middleware(req: object, ctx: object, next_fn: object) -> object:
    """Custom middleware - add timing."""
    import time

    start = time.time()
    response = await next_fn(req, ctx)
    print(f'Request took {time.time() - start:.2f}s')  # noqa: T201
    return response


async def custom_example() -> None:
    """Use custom middleware alongside built-ins."""
    response = await ai.generate(
        prompt='Say hello',
        use=[custom_middleware, retry(max_retries=2)],
    )
    print(f'Custom example: {response.text}')  # noqa: T201


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
async def main() -> None:
    """Run all middleware examples."""
    await retry_example()
    await fallback_example()
    await combined_example()
    await custom_example()


if __name__ == '__main__':
    ai.registry.register_plugin(GoogleAI())
    asyncio.run(main())
