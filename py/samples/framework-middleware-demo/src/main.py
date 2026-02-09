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

"""Middleware demo - Custom request/response interception in Genkit.

This sample demonstrates Genkit's middleware system, which lets you intercept
and modify requests before they reach the model, and inspect or modify
responses before they're returned to the caller.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Middleware           │ A function that sits between you and the model.    │
    │                     │ Like a security guard checking bags at the door.   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ use= Parameter      │ How you attach middleware to a generate() call.    │
    │                     │ ``ai.generate(prompt=..., use=[my_middleware])``    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ next()              │ Calls the next middleware or the model itself.      │
    │                     │ You MUST call it to continue the chain.            │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Request Modification│ Change the prompt, add system messages, etc.       │
    │                     │ before the model sees the request.                 │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Response Inspection │ Log, validate, or transform the model's response   │
    │                     │ before returning it to your code.                  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Chaining            │ Stack multiple middleware in order.                 │
    │                     │ ``use=[log, modify, validate]`` runs all three.    │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                     MIDDLEWARE PIPELINE                                  │
    │                                                                         │
    │   ai.generate(prompt=..., use=[log_mw, modify_mw])                      │
    │        │                                                                │
    │        ▼                                                                │
    │   ┌──────────────┐                                                      │
    │   │ log_mw       │  Logs request metadata                               │
    │   │ (before)     │  Then calls next(req, ctx)                           │
    │   └──────┬───────┘                                                      │
    │          │                                                              │
    │          ▼                                                              │
    │   ┌──────────────┐                                                      │
    │   │ modify_mw    │  Adds system instruction to request                  │
    │   │ (before)     │  Then calls next(modified_req, ctx)                  │
    │   └──────┬───────┘                                                      │
    │          │                                                              │
    │          ▼                                                              │
    │   ┌──────────────┐                                                      │
    │   │ Model        │  Actual API call                                     │
    │   └──────┬───────┘                                                      │
    │          │                                                              │
    │          ▼                                                              │
    │   modify_mw (after) ─── log_mw (after) ─── Response returned            │
    └─────────────────────────────────────────────────────────────────────────┘

Testing Instructions
====================
1. Set ``GEMINI_API_KEY`` environment variable.
2. Run ``./run.sh`` from this sample directory.
3. Open the DevUI at http://localhost:4000.
4. Run each flow and check the server logs for middleware output.

See README.md for more details.
"""

import asyncio
import os

from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.blocks.model import ModelMiddlewareNext
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.google_genai import GoogleAI
from genkit.types import GenerateRequest, GenerateResponse, Message, Part, Role, TextPart
from samples.shared.logging import setup_sample

setup_sample()

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

logger = get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.5-flash',
)


class LoggingInput(BaseModel):
    """Input for logging middleware demo."""

    prompt: str = Field(default='Tell me a joke about programming', description='Prompt to send through middleware')


class ModifierInput(BaseModel):
    """Input for request modifier middleware demo."""

    prompt: str = Field(default='Write a haiku', description='Prompt to send (middleware will add style instructions)')


class ChainedInput(BaseModel):
    """Input for chained middleware demo."""

    prompt: str = Field(default='Explain recursion', description='Prompt to send through multiple middleware')


async def logging_middleware(
    req: GenerateRequest,
    ctx: ActionRunContext,
    next_handler: ModelMiddlewareNext,
) -> GenerateResponse:
    """Middleware that logs request and response metadata.

    This is a pass-through middleware that doesn't modify the request
    or response -- it only observes and logs. Useful for debugging
    and monitoring.

    Args:
        req: The generation request about to be sent.
        ctx: The action execution context.
        next_handler: Calls the next middleware or the model.

    Returns:
        The generation response (unmodified).
    """
    await logger.ainfo(
        'logging_middleware: request intercepted',
        message_count=len(req.messages),
    )
    response = await next_handler(req, ctx)
    await logger.ainfo(
        'logging_middleware: response received',
        finish_reason=response.finish_reason,
    )
    return response


async def system_instruction_middleware(
    req: GenerateRequest,
    ctx: ActionRunContext,
    next_handler: ModelMiddlewareNext,
) -> GenerateResponse:
    """Middleware that prepends a system instruction to every request.

    Demonstrates modifying the request before it reaches the model.
    This pattern is useful for enforcing style guidelines, adding
    safety instructions, or injecting context.

    Args:
        req: The generation request about to be sent.
        ctx: The action execution context.
        next_handler: Calls the next middleware or the model.

    Returns:
        The generation response.
    """
    system_message = Message(
        role=Role.SYSTEM,
        content=[
            Part(root=TextPart(text='Always respond in a concise, professional tone. Keep answers under 100 words.'))
        ],
    )
    modified_messages = [system_message, *req.messages]
    modified_req = req.model_copy(update={'messages': modified_messages})

    await logger.ainfo('system_instruction_middleware: injected system message')
    return await next_handler(modified_req, ctx)


@ai.flow()
async def logging_demo(input: LoggingInput) -> str:
    """Demonstrate a simple logging middleware.

    Check the server logs to see the middleware output. The middleware
    logs request metadata before the model call and response metadata after.

    Args:
        input: Input with prompt text.

    Returns:
        The model's response text.
    """
    response = await ai.generate(
        prompt=input.prompt,
        use=[logging_middleware],
    )
    return response.text


@ai.flow()
async def request_modifier_demo(input: ModifierInput) -> str:
    """Demonstrate a middleware that modifies the request.

    The middleware injects a system instruction that tells the model to
    be concise and professional. Compare this with running the same
    prompt without middleware to see the difference.

    Args:
        input: Input with prompt text.

    Returns:
        The model's response text (influenced by injected system message).
    """
    response = await ai.generate(
        prompt=input.prompt,
        use=[system_instruction_middleware],
    )
    return response.text


@ai.flow()
async def chained_middleware_demo(input: ChainedInput) -> str:
    """Demonstrate multiple middleware chained together.

    The pipeline runs: logging -> system instruction -> model.
    Both middleware functions execute in order, and the logging middleware
    sees the request both before and after the system instruction is added.

    Args:
        input: Input with prompt text.

    Returns:
        The model's response text.
    """
    response = await ai.generate(
        prompt=input.prompt,
        use=[logging_middleware, system_instruction_middleware],
    )
    return response.text


# ============================================================================
# PART 2: Model-Level Middleware via define_model(use=[...])
# ============================================================================
# Model-level middleware is baked into a model at registration time.
# Every caller of this model gets the middleware automatically, without
# needing to pass use=[...] in generate().
#
# This is how plugin authors add cross-cutting concerns like safety
# checks, rate limiting, or request augmentation to their models.
# ============================================================================


class ModelLevelInput(BaseModel):
    """Input for model-level middleware demo."""

    prompt: str = Field(
        default='Tell me something interesting about Python',
        description='Prompt to send to the model with baked-in middleware',
    )


class CombinedInput(BaseModel):
    """Input for combined call-time + model-level middleware demo."""

    prompt: str = Field(
        default='Write a limerick about coding',
        description='Prompt to send through both call-time and model-level middleware',
    )


async def safety_prefix_middleware(
    req: GenerateRequest,
    ctx: ActionRunContext,
    next_handler: ModelMiddlewareNext,
) -> GenerateResponse:
    """Model-level middleware that prepends a safety instruction.

    This middleware is baked into the model via define_model(use=[...]).
    Every generate() call using this model will automatically get
    the safety instruction injected, even without passing use=[...].

    Args:
        req: The generation request about to be sent.
        ctx: The action execution context.
        next_handler: Calls the next middleware or the model.

    Returns:
        The generation response.
    """
    safety_text = (
        'You are a helpful, harmless, and honest assistant. '
        'Never produce harmful content.'
    )
    safety_message = Message(
        role=Role.SYSTEM,
        content=[Part(root=TextPart(text=safety_text))],
    )
    modified_messages = [safety_message, *req.messages]
    modified_req = req.model_copy(update={'messages': modified_messages})
    await logger.ainfo('safety_prefix_middleware (model-level): injected safety system message')
    return await next_handler(modified_req, ctx)


# Register a custom model that wraps Gemini and adds safety middleware.
# The actual model function delegates to the real Gemini model, but
# the safety middleware runs before every request.
def custom_model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
    """Custom model runner that delegates to the real Gemini model.

    This function demonstrates how define_model() works: you implement
    the model runner function, and Genkit handles all the middleware
    chaining, tracing, and registry management.

    Args:
        request: The generation request (possibly modified by middleware).
        ctx: The action execution context.

    Returns:
        The generation response from the underlying model.
    """
    # Build a response echoing the request for demonstration purposes.
    # In a real plugin, you'd call an API here.
    merged = ' '.join(
        p.root.text for m in request.messages for p in m.content if p.root.text
    )
    echo_text = (
        f'[custom-model] Processed request with '
        f'{len(request.messages)} messages. '
        f'Content: {merged[:100]}...'
    )
    return GenerateResponse(
        message=Message(
            role=Role.MODEL,
            content=[Part(root=TextPart(text=echo_text))],
        ),
    )


# Register the custom model WITH model-level middleware.
# Every call to generate(model='custom/safe-model') will run
# safety_prefix_middleware automatically.
ai.define_model(
    name='custom/safe-model',
    fn=custom_model_fn,
    use=[safety_prefix_middleware],
)


@ai.flow()
async def model_level_middleware_demo(input: ModelLevelInput) -> str:
    """Demonstrate model-level middleware set via define_model(use=[...]).

    No call-time middleware is passed -- the safety middleware is baked
    into the 'custom/safe-model' model definition. Every caller gets
    the middleware automatically.

    Args:
        input: Input with prompt text.

    Returns:
        The model's response text (with safety middleware applied).
    """
    response = await ai.generate(
        model='custom/safe-model',
        prompt=input.prompt,
    )
    return response.text


@ai.flow()
async def combined_middleware_demo(input: CombinedInput) -> str:
    """Demonstrate call-time + model-level middleware running together.

    The execution order is:
      1. logging_middleware      (call-time, from generate(use=[...]))
      2. safety_prefix_middleware (model-level, from define_model(use=[...]))
      3. custom_model_fn         (the actual model runner)

    This matches the JS SDK execution order:
      call-time[0..N] -> model-level[0..M] -> runner

    Args:
        input: Input with prompt text.

    Returns:
        The model's response text.
    """
    response = await ai.generate(
        model='custom/safe-model',
        prompt=input.prompt,
        use=[logging_middleware],
    )
    return response.text


async def main() -> None:
    """Main function -- keep alive for Dev UI."""
    await logger.ainfo('Middleware demo started. Open http://localhost:4000 to test flows.')
    await logger.ainfo('Flows available:')
    await logger.ainfo('  - logging_demo: call-time logging middleware')
    await logger.ainfo('  - request_modifier_demo: call-time request modification')
    await logger.ainfo('  - chained_middleware_demo: multiple call-time middleware')
    await logger.ainfo('  - model_level_middleware_demo: model-level middleware via define_model(use=[...])')
    await logger.ainfo('  - combined_middleware_demo: call-time + model-level middleware together')
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    ai.run_main(main())
