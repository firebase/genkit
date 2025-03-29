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

import asyncio

from pydantic import BaseModel, Field

from genkit.ai import Document, Genkit, ToolRunContext, tool_response
from genkit.core.typing import (
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.google_ai.models import gemini
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    GeminiEmbeddingModels,
    GoogleGenai,
    google_genai_name,
)

ai = Genkit(
    plugins=[GoogleGenai()],
    model=google_genai_name('gemini-2.0-flash'),
)


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


@ai.tool('calculates a gablorken')
def gablorkenTool(input_: GablorkenInput) -> int:
    """The user-defined tool function."""
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
        model=google_genai_name(gemini.GoogleAiVersion.GEMINI_1_5_FLASH),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'what is a gablorken of {value}')],
            ),
        ],
        tools=['gablorkenTool'],
    )
    return response.text


@ai.tool('calculates a gablorken')
def gablorkenTool2(input_: GablorkenInput, ctx: ToolRunContext):
    ctx.interrupt()


@ai.flow()
async def simple_generate_with_interrupts(value: int) -> str:
    response1 = await ai.generate(
        model=google_genai_name(gemini.GoogleAiVersion.GEMINI_1_5_FLASH),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'what is a gablorken of {value}')],
            ),
        ],
        tools=['gablorkenTool2'],
    )
    print(f'len(response.tool_requests)={len(response1.tool_requests)}')
    if len(response1.tool_requests) == 0:
        return response1.text

    tr = tool_response(response1.tool_requests[0], 178)
    response = await ai.generate(
        model=google_genai_name(gemini.GoogleAiVersion.GEMINI_1_5_FLASH),
        messages=response1.messages,
        tool_responses=[tr],
        tools=['gablorkenTool'],
    )
    return response


@ai.flow()
async def say_hi(data: str):
    resp = await ai.generate(
        prompt=f'hi {data}',
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
        model=google_genai_name(GeminiEmbeddingModels.TEXT_EMBEDDING_004),
        documents=[Document.from_text(doc) for doc in docs],
        options=options,
    )


@ai.flow()
async def say_hi_with_configured_temperature(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def say_hi_stream(name: str, ctx):
    stream, _ = ai.generate_stream(
        prompt=f'hi {name}',
    )
    result = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        for part in data.content:
            result += part.root.text

    return result


class RpgCharacter(BaseModel):
    name: str = Field(description='name of the character')
    story: str = Field(description='back story')
    weapons: list[str] = Field(description='list of weapons (3-4)')


@ai.flow()
async def generate_character(name: str, ctx):
    if ctx.is_streaming:
        stream, result = ai.generate_stream(
            prompt=f'generate an RPC character named {name}',
            output_schema=RpgCharacter,
        )
        async for data in stream:
            ctx.send_chunk(data.output)

        return (await result).output
    else:
        result = await ai.generate(
            prompt=f'generate an RPC character named {name}',
            output_schema=RpgCharacter,
        )
        return result.text

async def main() -> None:
    print(await say_hi(', tell me a joke'))


if __name__ == '__main__':
    asyncio.run(main())


# prevent app from exiting when genkit is running in dev mode
ai.join()
