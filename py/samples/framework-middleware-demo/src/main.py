# Copyright 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0

"""Middleware demo: make your agent production-ready—turn limits, resilient tools, retries.

Run: GEMINI_API_KEY=... uv run python src/main.py
"""

import asyncio
import random
from datetime import datetime

from genkit import Genkit
from genkit.middleware import BaseMiddleware, GenerateParams, ModelParams, ToolParams, retry
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(model='googleai/gemini-2.0-flash')


# -----------------------------------------------------------------------------
# BrevityNudge: on follow-up turns, inject "be brief" to cut output tokens
# -----------------------------------------------------------------------------
class BrevityNudge(BaseMiddleware):
    """On turn 1+, nudge the model to stay concise—saves tokens and latency."""

    async def wrap_generate(self, params: GenerateParams, next_fn):
        if params.iteration >= 1:
            from genkit import Message, ModelRequest, Part, Role, TextPart

            nudge = Message(role=Role.USER, content=[Part(TextPart(text='[Keep your answer to 1–2 sentences.]'))])
            req = ModelRequest(messages=[*params.request.messages, nudge])
            return await next_fn(GenerateParams(options=params.options, request=req, iteration=params.iteration))
        return await next_fn(params)


# -----------------------------------------------------------------------------
# ResilientTools: catch failures, return fallback so the agent keeps going
# -----------------------------------------------------------------------------
class ResilientTools(BaseMiddleware):
    """On tool error, return a fallback instead of failing the whole run."""

    async def wrap_tool(self, params: ToolParams, next_fn):
        try:
            return await next_fn(params)
        except Exception as e:
            name = params.tool_request_part.tool_request.name
            fallback = f'[{name} unavailable: {type(e).__name__}]'
            from genkit import Part, ToolResponse, ToolResponsePart

            return (
                Part(ToolResponsePart(tool_response=ToolResponse(name=name, output=fallback))),
                None,
            )


# -----------------------------------------------------------------------------
# Tools: one reliable, one that simulates flakiness
# -----------------------------------------------------------------------------
@ai.tool()
async def get_time() -> str:
    """Return the current time."""
    return datetime.now().strftime('%H:%M')


@ai.tool()
async def get_weather(city: str = 'NYC') -> str:
    """Return weather for a city. Simulates occasional failure."""
    if random.random() < 0.4:  # 40% chance to "fail"
        raise ConnectionError('Weather API timeout')
    return f'72°F, partly cloudy in {city}'


async def demo() -> None:
    """Agent with turn budget + resilient tools + retry. Stays cheap and reliable."""
    ai.registry.register_plugin(GoogleAI())

    optimizer = [BrevityNudge(), ResilientTools(), retry(max_retries=2)]

    r = await ai.generate(
        prompt='What time is it in NYC and how is the weather? Use tools. One sentence.',
        tools=['get_time', 'get_weather'],
        use=optimizer,
        max_turns=2,
    )

    print('Optimized agent output:')
    print(f'  {r.text}\n')
    print('Middleware: BrevityNudge, ResilientTools, retry(2) | max_turns=2')


if __name__ == '__main__':
    asyncio.run(demo())
