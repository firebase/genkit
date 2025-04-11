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

"""Hello Google GenAI sample.

Key features demonstrated in this sample:

| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[GoogleAI()])` |
| Default Model Configuration                              | `ai = Genkit(model=...)`               |
| Defining Flows                                           | `@ai.flow()` decorator (multiple uses) |
| Defining Tools                                           | `@ai.tool()` decorator (multiple uses) |
| Pydantic for Tool Input Schema                           | `GablorkenInput`                       |
| Simple Generation (Prompt String)                        | `say_hi`                               |
| Generation with Messages (`Message`, `Role`, `TextPart`) | `simple_generate_with_tools_flow`      |
| Generation with Tools                                    | `simple_generate_with_tools_flow`      |
| Tool Response Handling                                   | `simple_generate_with_interrupts`      |
| Tool Interruption (`ctx.interrupt`)                      | `gablorken_tool2`                      |
| Embedding (`ai.embed`, `Document`)                       | `embed_docs`                           |
| Generation Configuration (`temperature`, etc.)           | `say_hi_with_configured_temperature`   |
| Streaming Generation (`ai.generate_stream`)              | `say_hi_stream`                        |
| Streaming Chunk Handling (`ctx.send_chunk`)              | `say_hi_stream`, `generate_character`  |
| Structured Output (Schema)                               | `generate_character`                   |
| Pydantic for Structured Output Schema                    | `RpgCharacter`                         |
| Unconstrained Structured Output                          | `generate_character_unconstrained`     |
| Multi-modal Output Configuration                         | `generate_images`                      |

"""

import argparse
import asyncio

import structlog
import uvicorn
from pydantic import BaseModel, Field

from genkit.ai import Document, Genkit, ToolRunContext, tool_response
from genkit.core.flows import create_flows_asgi_app
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    GeminiConfigSchema,
    GeminiEmbeddingModels,
    GoogleAI,
    googleai_name,
)
from genkit.plugins.google_genai.models import gemini
from genkit.types import (
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model=googleai_name('gemini-2.0-flash-exp'),
)


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


@ai.tool(name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> int:
    """Calculate a gablorken.

    Args:
        input_: The input to calculate gablorken for.

    Returns:
        The calculated gablorken.
    """
    return input_.value * 3 - 5


@ai.flow()
async def simple_generate_with_tools_flow(value: int) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function

    Returns:
        The generated response with a function.
    """
    response = await ai.generate(
        model=googleai_name(gemini.GoogleAIGeminiVersion.GEMINI_2_0_FLASH),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'what is a gablorken of {value}')],
            ),
        ],
        tools=['gablorkenTool'],
    )
    return response.text


@ai.tool(name='interruptingTool')
def interrupting_tool(input_: GablorkenInput, ctx: ToolRunContext):
    """The user-defined tool function.

    Args:
        input_: the input to the tool
        ctx: the tool run context

    Returns:
        The calculated gablorken.
    """
    ctx.interrupt()


@ai.flow()
async def simple_generate_with_interrupts(value: int) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function

    Returns:
        The generated response with a function.
    """
    response1 = await ai.generate(
        model=googleai_name(gemini.GoogleAIGeminiVersion.GEMINI_2_0_FLASH),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'what is a gablorken of {value}')],
            ),
        ],
        tools=['interruptingTool'],
    )
    await logger.ainfo(f'len(response.tool_requests)={len(response1.tool_requests)}')
    if len(response1.interrupts) == 0:
        return response1.text

    tr = tool_response(response1.interrupts[0], 178)
    response = await ai.generate(
        model=googleai_name(gemini.GoogleAIGeminiVersion.GEMINI_2_0_FLASH),
        messages=response1.messages,
        tool_responses=[tr],
        tools=['gablorkenTool'],
    )
    return response


@ai.flow()
async def say_hi(name: str):
    """Generate a greeting for the given name.

    Args:
        name: the name to send to test function

    Returns:
        The generated response with a function.
    """
    resp = await ai.generate(
        prompt=f'hi {name}',
    )
    return resp.text


@ai.flow()
async def embed_docs(docs: list[str]):
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embedding.
    """
    options = {'task_type': EmbeddingTaskType.CLUSTERING}
    return await ai.embed(
        embedder=googleai_name(GeminiEmbeddingModels.TEXT_EMBEDDING_004),
        documents=[Document.from_text(doc) for doc in docs],
        options=options,
    )


@ai.flow()
async def say_hi_with_configured_temperature(data: str):
    """Generate a greeting for the given name.

    Args:
        data: the name to send to test function

    Returns:
        The generated response with a function.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def say_hi_stream(name: str, ctx):
    """Generate a greeting for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    stream, _ = ai.generate_stream(prompt=f'hi {name}')
    result = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        for part in data.content:
            result += part.root.text

    return result


@ai.flow()
async def stream_greeting(name: str, ctx) -> str:
    """Stream a greeting for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    chunks = [
        'hello',
        name,
        'how are you?',
    ]
    for data in chunks:
        await asyncio.sleep(1)
        ctx.send_chunk(data)

    return 'test streaming response'


class Skills(BaseModel):
    """Skills for an RPG character."""

    strength: int = Field(description='strength (0-100)')
    charisma: int = Field(description='charisma (0-100)')
    endurance: int = Field(description='endurance (0-100)')


class RpgCharacter(BaseModel):
    """An RPG character."""

    name: str = Field(description='name of the character')
    back_story: str = Field(description='back story', alias='backStory')
    abilities: list[str] = Field(description='list of abilities (3-4)')
    skills: Skills


@ai.flow()
async def generate_character(name: str, ctx):
    """Generate an RPG character.

    Args:
        name: the name of the character
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    if ctx.is_streaming:
        stream, result = ai.generate_stream(
            prompt=f'generate an RPG character named {name}',
            output_schema=RpgCharacter,
        )
        async for data in stream:
            ctx.send_chunk(data.output)

        return (await result).output
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {name}',
            output_schema=RpgCharacter,
        )
        return result.output


@ai.flow()
async def generate_character_unconstrained(name: str, ctx):
    """Generate an unconstrained RPG character.

    Args:
        name: the name of the character
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'generate an RPG character named {name}',
        output_schema=RpgCharacter,
        output_constrained=False,
        output_instructions=True,
    )
    return result.output


@ai.flow()
async def generate_images(name: str, ctx):
    """Generate images for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    result = await ai.generate(
        prompt='tell me a about the Eifel Tower with photos',
        config=GeminiConfigSchema(response_modalities=['text', 'image']),
    )
    return result


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        The parsed command line arguments.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true', help='Run the application as a server')
    return parser.parse_args()


async def server_main(ai: Genkit) -> None:
    """Entry point function for the server application."""

    async def on_app_startup() -> None:
        """Handle application startup."""
        await logger.ainfo('[LIFESPAN] Starting flows server...')
        # Any initialization could go here

    async def on_app_shutdown() -> None:
        """Handle application shutdown."""
        await logger.ainfo('[LIFESPAN] Shutting down flows server...')

    app = create_flows_asgi_app(
        registry=ai.registry,
        context_providers=[],
        on_app_startup=on_app_startup,
        on_app_shutdown=on_app_shutdown,
    )
    config = uvicorn.Config(app, host='localhost', port=3400)
    server = uvicorn.Server(config)
    await server.serve()


async def main(ai: Genkit) -> None:
    """Main function."""
    await logger.ainfo(await say_hi(', tell me a joke'))


if __name__ == '__main__':
    config: argparse.Namespace = parse_args()
    runner = server_main if config.server else main
    ai.run_main(runner(ai))
