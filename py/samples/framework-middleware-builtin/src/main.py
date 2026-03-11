"""Built-in middleware examples - retry, fallback, and more.

Run: GEMINI_API_KEY=... uv run python src/main.py
"""

import asyncio

from genkit import Genkit, retry, fallback

ai = Genkit(model='googleai/gemini-2.0-flash')


# -----------------------------------------------------------------------------
# Example 1: Retry with exponential backoff
# -----------------------------------------------------------------------------
async def retry_example():
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
    print(f'Retry example: {response.text}')


# -----------------------------------------------------------------------------
# Example 2: Fallback to another model
# -----------------------------------------------------------------------------
async def fallback_example():
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
    print(f'Fallback example: {response.text}')


# -----------------------------------------------------------------------------
# Example 3: Combine retry + fallback
# -----------------------------------------------------------------------------
async def combined_example():
    """Retry first, then fallback if all retries fail."""
    response = await ai.generate(
        prompt='Say hello',
        use=[
            retry(max_retries=2, initial_delay_ms=500),
            fallback(ai, models=['googleai/gemini-2.0-flash']),
        ],
    )
    print(f'Combined example: {response.text}')


# -----------------------------------------------------------------------------
# Example 4: Custom middleware (for reference)
# -----------------------------------------------------------------------------
async def custom_middleware(req, ctx, next_fn):
    """Custom middleware - add timing."""
    import time

    start = time.time()
    response = await next_fn(req, ctx)
    print(f'Request took {time.time() - start:.2f}s')
    return response


async def custom_example():
    """Use custom middleware alongside built-ins."""
    response = await ai.generate(
        prompt='Say hello',
        use=[custom_middleware, retry(max_retries=2)],
    )
    print(f'Custom example: {response.text}')


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
async def main():
    await retry_example()
    await fallback_example()
    await combined_example()
    await custom_example()


if __name__ == '__main__':
    from genkit.plugins.google_genai import GoogleAI

    ai.registry.register_plugin(GoogleAI())
    asyncio.run(main())
