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

"""Middleware demo - Intercept requests/responses with use=[...] on ai.generate()."""

import os
from collections.abc import Awaitable, Callable

import structlog
from pydantic import BaseModel, Field

from genkit import Genkit, Message, ModelRequest, ModelResponse, Part, Role, TextPart
from genkit._core._action import ActionRunContext
from genkit.plugins.google_genai import GoogleAI

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

logger = structlog.get_logger(__name__)

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
    req: ModelRequest,
    ctx: ActionRunContext,
    next_handler: Callable[[ModelRequest, ActionRunContext], Awaitable[ModelResponse]],
) -> ModelResponse:
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
    req: ModelRequest,
    ctx: ActionRunContext,
    next_handler: Callable[[ModelRequest, ActionRunContext], Awaitable[ModelResponse]],
) -> ModelResponse:
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


async def main() -> None:
    pass


if __name__ == '__main__':
    ai.run_main(main())
