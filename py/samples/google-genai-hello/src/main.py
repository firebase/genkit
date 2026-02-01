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

"""Hello Google GenAI sample - Comprehensive Google AI features demo.

This sample demonstrates the full range of Google GenAI plugin capabilities,
from basic generation to advanced features like tool calling, streaming,
structured output, and multimodal inputs.

See README.md for testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Genkit              │ A framework for building AI apps. Like Lego       │
    │                     │ blocks for connecting AI models to your code.     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Flow                │ A function that does AI work. Decorated with      │
    │                     │ @ai.flow() so Genkit can track and manage it.     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Tool                │ A function the AI can call. Like giving the AI    │
    │                     │ a calculator or search engine to use.             │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Generation          │ Asking the AI to write something. "Generate       │
    │                     │ a poem about cats" → AI writes the poem.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Getting the response word-by-word as it's made.   │
    │                     │ Feels faster, like watching someone type.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Structured Output   │ Getting AI responses as proper data (JSON).       │
    │                     │ Not just text, but name="Bob", age=25, etc.       │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Embedding           │ Converting text to numbers that capture meaning.  │
    │                     │ "Happy" and "joyful" become similar numbers.      │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Multimodal          │ AI that understands multiple types of input.      │
    │                     │ Not just text, but also images and videos.        │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[GoogleAI()])`    |
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
| GCP Telemetry (Traces and Metrics)                       | `add_gcp_telemetry()`                  |
| Thinking Mode (CoT)                                      | `thinking_level_pro`, `thinking_level_flash` |
| Search Grounding                                         | `search_grounding`                     |
| URL Context                                              | `url_context`                          |
| Multimodal Generation (Video input)                      | `youtube_videos`                       |
"""

import argparse
import asyncio
import base64
import os
import sys
import tempfile

from google import genai as google_genai_sdk
from rich.traceback import install as install_rich_traceback

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if sys.version_info < (3, 11):
    from strenum import StrEnum  # pyright: ignore[reportUnreachable]
else:
    from enum import StrEnum

from pydantic import BaseModel, Field

from genkit.ai import Genkit, Output, ToolRunContext, tool_response
from genkit.blocks.model import GenerateResponseWrapper
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.evaluators import GenkitMetricType, MetricConfig, define_genkit_evaluators
from genkit.plugins.google_cloud import add_gcp_telemetry
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    GoogleAI,
)
from genkit.types import (
    GenerationCommonConfig,
    Media,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
)

logger = get_logger(__name__)


if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')


ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-3-pro-preview',
)

define_genkit_evaluators(
    ai,
    [
        MetricConfig(metric_type=GenkitMetricType.REGEX),
        MetricConfig(metric_type=GenkitMetricType.DEEP_EQUAL),
        MetricConfig(metric_type=GenkitMetricType.JSONATA),
    ],
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


class ThinkingLevel(StrEnum):
    """Thinking level enum."""

    LOW = 'LOW'
    HIGH = 'HIGH'


class ThinkingLevelFlash(StrEnum):
    """Thinking level flash enum."""

    MINIMAL = 'MINIMAL'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


class WeatherInput(BaseModel):
    """Input for getting weather."""

    location: str = Field(description='The city and state, e.g. San Francisco, CA')


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Whiskers', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    name: str = Field(default='Shadow', description='Name to write story about')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class TemperatureInput(BaseModel):
    """Input for temperature config flow."""

    data: str = Field(default='Mittens', description='Name to greet')


class ToolsFlowInput(BaseModel):
    """Input for tools flow."""

    value: int = Field(default=42, description='Value for gablorken calculation')


class DynamicToolsInput(BaseModel):
    """Input for dynamic tools demo."""

    input_val: str = Field(default='Dynamic tools demo', description='Input value for demo')


class ToolCallingInput(BaseModel):
    """Input for tool calling flow."""

    location: str = Field(default='Paris, France', description='Location to get weather for')


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
async def simple_generate_with_interrupts(input: ToolsFlowInput) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with value for gablorken calculation.

    Returns:
        The generated response with a function.
    """
    response1 = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[Part(root=TextPart(text=f'what is a gablorken of {input.value}'))],
            ),
        ],
        tools=['gablorkenTool2'],
    )
    await logger.ainfo(f'len(response.tool_requests)={len(response1.tool_requests)}')
    if len(response1.interrupts) == 0:
        return response1.text

    tr = tool_response(response1.interrupts[0], {'output': 178})
    response = await ai.generate(
        messages=response1.messages,
        tool_responses=[tr],
        tools=['gablorkenTool'],
    )
    return response.text


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with name to greet.

    Returns:
        The generated greeting response.

    Example:
        >>> result = await say_hi(SayHiInput(name='Mr. Fluffington'))
        >>> print(result)
        Hello Mr. Fluffington! *purrs contentedly*
    """
    resp = await ai.generate(
        prompt=f'hi {input.name}',
    )

    await logger.ainfo(
        'generation_response',
        has_usage=hasattr(resp, 'usage'),
        usage_dict=resp.usage.model_dump() if hasattr(resp, 'usage') and resp.usage else None,
        text_length=len(resp.text),
    )

    return resp.text


@ai.flow()
async def demo_dynamic_tools(input: DynamicToolsInput) -> dict[str, object]:
    """Demonstrates advanced Genkit features: ai.run() and ai.dynamic_tool().

    This flow shows how to:
    1. Use `ai.run()` to create sub-spans (steps) within a flow trace.
    2. Use `ai.dynamic_tool()` to create tools on-the-fly without registration.

    To test this in the Dev UI:
    1. Select 'demo_dynamic_tools' from the flows list.
    2. Run it with the default input or provide a custom string.
    3. Click 'View trace' to see the 'process_data_step' sub-span and tool execution.
    """

    # ai.run() allows you to wrap any function in a trace span, which is visible
    # in the Dev UI. It supports an optional input argument as the second parameter.
    def process_data(data: str) -> str:
        return f'processed: {data}'

    run_result = await ai.run('process_data_step', input.input_val, process_data)

    # ai.dynamic_tool() creates a tool that isn't globally registered but can be
    # used immediately or passed to generate() calls.
    def multiplier_fn(x: int) -> int:
        return x * 10

    dynamic_multiplier = ai.dynamic_tool('dynamic_multiplier', multiplier_fn, description='Multiplies by 10')
    tool_res = await dynamic_multiplier.arun(5)

    return {
        'step_result': run_result,
        'dynamic_tool_result': tool_res.response,
        'tool_metadata': dynamic_multiplier.metadata,
    }


@ai.flow()
async def describe_image() -> str:
    """Describe an image (reads from photo.jpg)."""
    # Read the photo.jpg file and encode to base64
    current_dir = os.path.dirname(os.path.abspath(__file__))
    photo_path = os.path.join(current_dir, '..', 'photo.jpg')

    with open(photo_path, 'rb') as photo_file:
        photo_base64 = base64.b64encode(photo_file.read()).decode('utf-8')

    response = await ai.generate(
        prompt=[
            Part(root=TextPart(text='describe this photo')),
            Part(root=MediaPart(media=Media(url=f'data:image/jpeg;base64,{photo_base64}', content_type='image/jpeg'))),
        ],
    )
    return response.text


@ai.tool(name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> dict[str, int]:
    """Calculate a gablorken.

    Returns:
        The calculated gablorken.
    """
    return {'result': input_.value * 3 - 5}


@ai.tool(name='gablorkenTool2')
def gablorken_tool2(_input: GablorkenInput, ctx: ToolRunContext) -> None:
    """The user-defined tool function."""
    pass


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
    _ctx: ActionRunContext | None = None,
) -> RpgCharacter:
    """Generate an unconstrained RPG character.

    Args:
        input: Input with character name.
        _ctx: the context of the tool (unused)

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
        input: Input with name for greeting.

    Returns:
        The generated response with a function.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text=f'hi {input.data}'))])],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def search_grounding() -> str:
    """Search grounding demo - retrieves current info from the web.

    This flow demonstrates Google Search grounding, which allows the model
    to access real-time information from the web to answer questions.

    Returns:
        Information about cats with web-grounded facts.
    """
    response = await ai.generate(
        prompt='What are the most popular cat breeds in 2024 and their characteristics?',
        config={'google_search_retrieval': True},
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


@ai.flow()
async def thinking_level_flash(_level: ThinkingLevelFlash) -> str:
    """Gemini 3.0 thinkingLevel config (Flash)."""
    response = await ai.generate(
        prompt=(
            'Alice, Bob, and Carol each live in a different house on the '
            'same street: red, green, and blue. The person who lives in the red house '
            'owns a cat. Bob does not live in the green house. Carol owns a dog. The '
            'green house is to the left of the red house. Alice does not own a cat. '
            'The person in the blue house owns a fish. '
            'Who lives in each house, and what pet do they own? Provide your '
            'step-by-step reasoning.'
        ),
        config={
            'thinking_config': {
                'include_thoughts': True,
            }
        },
    )
    return response.text


class ThinkingLevelFlash(StrEnum):
    """Thinking level flash enum."""

    MINIMAL = 'MINIMAL'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


@ai.flow()
async def thinking_level_pro(_level: ThinkingLevel) -> str:
    """Gemini 3.0 thinkingLevel config (Pro)."""
    response = await ai.generate(
        prompt=(
            'Alice, Bob, and Carol each live in a different house on the '
            'same street: red, green, and blue. The person who lives in the red house '
            'owns a cat. Bob does not live in the green house. Carol owns a dog. The '
            'green house is to the left of the red house. Alice does not own a cat. '
            'The person in the blue house owns a fish. '
            'Who lives in each house, and what pet do they own? Provide your '
            'step-by-step reasoning.'
        ),
        config={
            'thinking_config': {
                'include_thoughts': True,
            }
        },
    )
    return response.text


@ai.flow()
async def url_context() -> str:
    """URL context demo - analyzes content from web pages.

    This flow demonstrates URL context feature, allowing the model to
    read and analyze content from specified web URLs.

    Returns:
        Analysis of cat care information from the web.
    """
    response = await ai.generate(
        prompt=('Summarize the key cat care tips from https://www.aspca.org/pet-care/cat-care/general-cat-care'),
        config={'url_context': {}, 'api_version': 'v1alpha'},
    )
    return response.text


async def create_file_search_store(client: google_genai_sdk.Client) -> str:
    """Creates a file search store."""
    file_search_store = await client.aio.file_search_stores.create()
    if not file_search_store.name:
        raise ValueError('File Search Store created without a name.')
    return file_search_store.name


async def upload_blob_to_file_search_store(client: google_genai_sdk.Client, file_search_store_name: str) -> None:
    """Uploads a blob to the file search store."""
    text_content = (
        'The Whispering Woods In the heart of Eldergrove, there stood a forest whispered about by the villagers. '
        'They spoke of trees that could talk and streams that sang. Young Elara, curious and adventurous, '
        'decided to explore the woods one crisp autumn morning. As she wandered deeper, the leaves rustled with '
        'excitement, revealing hidden paths. Elara noticed the trees bending slightly as if beckoning her to come '
        'closer. When she paused to listen, she heard soft murmurs—stories of lost treasures and forgotten dreams. '
        'Drawn by the enchanting sounds, she followed a narrow trail until she stumbled upon a shimmering pond. '
        'At its edge, a wise old willow tree spoke, “Child of the village, what do you seek?” “I seek adventure,” '
        'Elara replied, her heart racing. “Adventure lies not in faraway lands but within your spirit,” the willow '
        'said, swaying gently. “Every choice you make is a step into the unknown.” With newfound courage, Elara left '
        'the woods, her mind buzzing with possibilities. The villagers would say the woods were magical, but to Elara, '
        'it was the spark of her imagination that had transformed her ordinary world into a realm of endless '
        'adventures. She smiled, knowing her journey was just beginning'
    )

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp:
        tmp.write(text_content)
        tmp_path = tmp.name

    try:
        # Use the high-level helper to upload directly to the store with metadata
        print(f'Uploading file to store {file_search_store_name}...')
        op = await client.aio.file_search_stores.upload_to_file_search_store(
            file_search_store_name=file_search_store_name,
            file=tmp_path,
            config={'custom_metadata': [{'key': 'author', 'string_value': 'foo'}]},
        )

        # Poll for completion
        while not op.done:
            await asyncio.sleep(2)
            # Fetch the updated operation status
            op = await client.aio.operations.get(operation=op)
            print(f'Operation status: {op.metadata.get("state") if op.metadata else "processing"}')

        print('Upload complete.')

    finally:
        os.unlink(tmp_path)
    return


async def delete_file_search_store(client: google_genai_sdk.Client, name: str) -> None:
    """Deletes the file search store."""
    await client.aio.file_search_stores.delete(name=name, config={'force': True})


@ai.flow()
async def file_search() -> str:
    """File Search."""
    # Create a client using the same API Key as the plugin
    api_key = os.environ.get('GEMINI_API_KEY')
    client = google_genai_sdk.Client(api_key=api_key)

    # 1. Create Store
    store_name = await create_file_search_store(client)
    print(f'Created store: {store_name}')

    try:
        # 2. Upload Blob (Story)
        await upload_blob_to_file_search_store(client, store_name)

        # 3. Generate
        response = await ai.generate(
            prompt="What is the character's name in the story?",
            config={
                'file_search': {
                    'file_search_store_names': [store_name],
                    'metadata_filter': 'author=foo',
                },
                'api_version': 'v1alpha',
            },
        )
        return response.text
    finally:
        # 4. Cleanup
        await delete_file_search_store(client, store_name)
        print(f'Deleted store: {store_name}')


@ai.flow()
async def embed_docs(
    docs: list[str] | None = None,
) -> list[dict]:
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embeddings as serializable dicts.
    """
    if docs is None:
        docs = ['Hello world', 'Genkit is great', 'Embeddings are fun']
    options = {'task_type': EmbeddingTaskType.CLUSTERING}
    embeddings = await ai.embed_many(
        embedder='googleai/text-embedding-004',
        content=docs,
        options=options,
    )
    # Serialize embeddings to dicts for JSON compatibility
    return [emb.model_dump(by_alias=True) for emb in embeddings]


@ai.flow()
async def youtube_videos() -> str:
    """YouTube videos."""
    response = await ai.generate(
        prompt=[
            Part(root=TextPart(text='transcribe this video')),
            Part(
                root=MediaPart(media=Media(url='https://www.youtube.com/watch?v=3p1P5grjXIQ', content_type='video/mp4'))
            ),
        ],
        config={},
    )
    return response.text


class ScreenshotInput(BaseModel):
    """Input for screenshot tool."""

    url: str = Field(description='The URL to take a screenshot of')


@ai.tool(name='screenShot')
def take_screenshot(input_: ScreenshotInput) -> dict:
    """Take a screenshot of a given URL."""
    # Implement your screenshot logic here
    print(f'Taking screenshot of {input_.url}')
    return {'url': input_.url, 'screenshot_path': '/tmp/screenshot.png'}


@ai.tool(name='getWeather')
def get_weather(input_: WeatherInput) -> dict:
    """Used to get current weather for a location."""
    return {
        'location': input_.location,
        'temperature_celcius': 21.5,
        'conditions': 'cloudy',
    }


@ai.tool(name='celsiusToFahrenheit')
def celsius_to_fahrenheit(celsius: float) -> float:
    """Converts Celsius to Fahrenheit."""
    return (celsius * 9) / 5 + 32


@ai.flow()
async def tool_calling(input: ToolCallingInput) -> str:
    """Tool calling with Gemini."""
    response = await ai.generate(
        tools=['getWeather', 'celsiusToFahrenheit'],
        prompt=f"What's the weather in {input.location}? Convert the temperature to Fahrenheit.",
        config=GenerationCommonConfig(temperature=1),
    )
    return response.text


async def main() -> None:
    """Main function - keep alive for Dev UI."""
    # Keep the process alive for Dev UI
    _ = await asyncio.Event().wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Google GenAI Hello Sample')
    _ = parser.add_argument(
        '--enable-gcp-telemetry',
        action='store_true',
        help='Enable Google Cloud Platform telemetry',
    )
    args = parser.parse_args()
    if args.enable_gcp_telemetry:
        add_gcp_telemetry()
    ai.run_main(main())
