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

"""Hello Vertex AI sample - Google Cloud's Vertex AI with Genkit.

This sample demonstrates how to use Vertex AI (Google Cloud's ML platform)
with Genkit for enterprise-grade AI applications.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Vertex AI           │ Google Cloud's AI platform. Like GoogleAI but      │
    │                     │ for enterprise with more security features.        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ GCP Project         │ Your Google Cloud project. Like a folder that      │
    │                     │ holds all your cloud resources.                    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Location            │ Which data center to use (us-central1, etc.).      │
    │                     │ Pick one near your users.                          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ ADC                 │ Application Default Credentials. Google's way      │
    │                     │ of auto-finding your login credentials.            │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ gcloud auth         │ The command to log in. Run once and Google         │
    │                     │ remembers who you are.                             │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[VertexAI(...)])` |
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

Testing This Demo
=================
1. **Prerequisites**:
   ```bash
   # Set GCP project and location
   export GOOGLE_CLOUD_PROJECT=your_project_id
   export GOOGLE_CLOUD_LOCATION=us-central1

   # Authenticate with GCP
   gcloud auth application-default login
   ```

2. **Run the demo**:
   ```bash
   cd py/samples/google-genai-vertexai-hello
   ./run.sh
   ```

3. **Open DevUI** at http://localhost:4000

4. **Test basic flows**:
   - [ ] `say_hi` - Simple generation
   - [ ] `say_hi_stream` - Streaming response
   - [ ] `say_hi_with_configured_temperature` - Custom config

5. **Test tools**:
   - [ ] `simple_generate_with_tools_flow` - Tool calling
   - [ ] `simple_generate_with_interrupts` - Tool interrupts

6. **Test structured output**:
   - [ ] `generate_character` - Constrained output
   - [ ] `generate_character_unconstrained` - Unconstrained

7. **Test embeddings**:
   - [ ] `embed_docs` - Document embedding

8. **Note**: Vertex AI requires a GCP project with billing enabled.
"""

import os

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output, ToolRunContext, tool_response
from genkit.blocks.model import GenerateResponseWrapper
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    VertexAI,
)
from genkit.types import (
    Embedding,
    GenerationCommonConfig,
    Message,
    Part,
    Role,
    TextPart,
)

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

logger = get_logger(__name__)

# Check for GCLOUD_PROJECT or GOOGLE_CLOUD_PROJECT
# If GOOGLE_CLOUD_PROJECT is set but GCLOUD_PROJECT isn't, use it
if 'GCLOUD_PROJECT' not in os.environ:
    if 'GOOGLE_CLOUD_PROJECT' in os.environ:
        os.environ['GCLOUD_PROJECT'] = os.environ['GOOGLE_CLOUD_PROJECT']
    else:
        os.environ['GCLOUD_PROJECT'] = input('Please enter your GCLOUD_PROJECT_ID: ')


ai = Genkit(
    plugins=[VertexAI()],
    model='vertexai/gemini-3-pro-preview',
)


class CurrencyExchangeInput(BaseModel):
    """Currency exchange flow input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_curr: str = Field(description='Source currency code', default='USD')
    to_curr: str = Field(description='Target currency code', default='EUR')


class CurrencyInput(BaseModel):
    """Currency conversion input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_currency: str = Field(description='Source currency code (e.g., USD)', default='USD')
    to_currency: str = Field(description='Target currency code (e.g., EUR)', default='EUR')


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


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


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mittens', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    name: str = Field(default='Shadow', description='Name for streaming greeting')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class TemperatureInput(BaseModel):
    """Input for temperature config flow."""

    data: str = Field(default='Mittens', description='Name to greet')


class ToolsFlowInput(BaseModel):
    """Input for tools flow."""

    value: int = Field(default=42, description='Value for gablorken calculation')


@ai.tool()
def convert_currency(input: CurrencyInput) -> str:
    """Convert currency amount.

    Args:
        input: Currency conversion parameters.

    Returns:
        Converted amount.
    """
    # Mock conversion rates
    rates = {
        ('USD', 'EUR'): 0.85,
        ('EUR', 'USD'): 1.18,
        ('USD', 'GBP'): 0.73,
        ('GBP', 'USD'): 1.37,
    }

    rate = rates.get((input.from_currency, input.to_currency), 1.0)
    converted = input.amount * rate

    return f'{input.amount} {input.from_currency} = {converted:.2f} {input.to_currency}'


@ai.flow()
async def currency_exchange(input: CurrencyExchangeInput) -> str:
    """Convert currency using tools.

    Args:
        input: Currency exchange parameters.

    Returns:
        Conversion result.
    """
    response = await ai.generate(
        prompt=f'Convert {input.amount} {input.from_curr} to {input.to_curr}',
        tools=['convert_currency'],
    )
    return response.text


@ai.flow()
async def embed_docs(docs: list[str] | None = None) -> list[Embedding]:
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embedding.
    """
    if docs is None:
        docs = ['Hello world', 'Genkit is great', 'Embeddings are fun']
    options = {'task_type': EmbeddingTaskType.CLUSTERING}
    return await ai.embed_many(
        embedder='vertexai/text-embedding-004',
        content=docs,
        options=options,
    )


@ai.tool(name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> int:
    """Calculate a gablorken.

    Args:
        input_: The input to calculate gablorken for.

    Returns:
        The calculated gablorken.
    """
    return input_.value * 3 - 5


@ai.tool(name='gablorkenTool2')
def gablorken_tool2(input_: GablorkenInput, ctx: ToolRunContext) -> None:
    """The user-defined tool function.

    Args:
        input_: the input to the tool
        ctx: the tool run context

    Returns:
        The calculated gablorken.
    """
    ctx.interrupt()


@ai.flow()
async def generate_character(
    input: CharacterInput,
    ctx: ActionRunContext | None = None,
) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        input: Input with character name.
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    if ctx is not None and ctx.is_streaming:
        stream, result = ai.generate_stream(
            prompt=f'generate an RPG character named {input.name}',
            output=Output(schema=RpgCharacter),
        )
        async for data in stream:
            ctx.send_chunk(data.output)

        return (await result).output
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {input.name}',
            output=Output(schema=RpgCharacter),
        )
        return result.output


@ai.flow()
async def generate_character_unconstrained(
    input: CharacterInput,
    ctx: ActionRunContext | None = None,
) -> RpgCharacter:
    """Generate an unconstrained RPG character.

    Args:
        input: Input with character name.
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'generate an RPG character named {input.name}',
        output=Output(schema=RpgCharacter),
        output_constrained=False,
        output_instructions=True,
    )
    return result.output


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with name to greet.

    Returns:
        The generated response with a function.
    """
    resp = await ai.generate(
        prompt=f'hi {input.name}',
    )
    return resp.text


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext | None = None,
) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with name for streaming.
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    stream, _ = ai.generate_stream(prompt=f'hi {input.name}')
    result: str = ''
    async for data in stream:
        if ctx is not None:
            ctx.send_chunk(data.text)
        result += data.text

    return result


@ai.flow()
async def say_hi_with_configured_temperature(input: TemperatureInput) -> GenerateResponseWrapper:
    """Generate a greeting for the given name.

    Args:
        input: Input with name to greet.

    Returns:
        The generated response with a function.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text=f'hi {input.data}'))])],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def simple_generate_with_interrupts(input: ToolsFlowInput) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with value for gablorken calculation.

    Returns:
        The generated response with a function.
    """
    response1 = await ai.generate(
        prompt=f'what is a gablorken of {input.value}',
        tools=['gablorkenTool2'],
    )
    await logger.ainfo(f'len(response.tool_requests)={len(response1.tool_requests)}')
    if len(response1.tool_requests) == 0:
        return response1.text

    tr = tool_response(response1.tool_requests[0], 178)
    response = await ai.generate(
        messages=response1.messages,
        tool_responses=[tr],
        tools=['gablorkenTool'],
    )
    return response.text


@ai.flow()
async def simple_generate_with_tools_flow(input: ToolsFlowInput) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with value for gablorken calculation.

    Returns:
        The generated response with a function.
    """
    response = await ai.generate(
        prompt=f'what is a gablorken of {input.value}',
        tools=['gablorkenTool'],
    )
    return response.text


async def main() -> None:
    """Main function - runs when script starts."""
    await logger.ainfo('VertexAI Hello sample initialized. Use Dev UI to invoke flows.')


if __name__ == '__main__':
    ai.run_main(main())
