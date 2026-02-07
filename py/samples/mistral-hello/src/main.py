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

"""Mistral AI hello sample - Mistral models with Genkit.

This sample demonstrates how to use Mistral AI's models with Genkit,
including Mistral Large 3, Mistral Small 3.2, Codestral, Magistral

See README.md for testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Mistral AI          │ French AI company known for efficient, powerful    │
    │                     │ models. Great balance of speed and quality.        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ mistral-large       │ Most capable model. Best for complex reasoning,    │
    │                     │ coding, and nuanced tasks.                         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ mistral-small       │ Fast and efficient. Great for everyday tasks       │
    │                     │ like chat, summarization, and simple coding.       │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ codestral           │ Specialized coding model. Optimized for code       │
    │                     │ generation, completion, and explanation.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Tool Calling        │ Let the model call your functions. Like giving     │
    │                     │ the AI a toolbox to help answer questions.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Structured Output   │ Get responses in a specific format (JSON).         │
    │                     │ Like filling out a form instead of free text.      │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Get the response word-by-word as it's generated.   │
    │                     │ Feels faster, like watching someone type.          │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                     | Example Function / Code Snippet         |
|-----------------------------------------|-----------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[Mistral(...)])`   |
| Default Model Configuration             | `ai = Genkit(model=mistral_name(...))` |
| Defining Flows                          | `@ai.flow()` decorator                  |
| Defining Tools                          | `@ai.tool()` decorator                  |
| Simple Generation (Prompt String)       | `say_hi`                                |
| Streaming Response                      | `say_hi_stream`                         |
| Code Generation (Codestral)             | `code_flow`                             |
| Generation with Config                  | `say_hi_with_config`                    |
| Multi-turn Chat                         | `chat_flow`                             |
| Tool Calling                            | `weather_flow`                          |
| Structured Output (JSON)                | `generate_character`                    |
| Multimodal (Image Input)                | `describe_image`                        |
| Reasoning (Magistral)                   | `reasoning_flow`                        |
| Embeddings (Text)                       | `embed_flow`                            |
| Embeddings (Code)                       | `code_embed_flow`                       |
| Audio Transcription (Voxtral)           | `audio_flow`                            |
"""

import asyncio
import base64
import os
import random
from pathlib import Path

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.blocks.document import Document
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.core.typing import Media, MediaPart, Message, Part, Role, TextPart, ToolChoice
from genkit.plugins.mistral import Mistral, mistral_name

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if 'MISTRAL_API_KEY' not in os.environ:
    os.environ['MISTRAL_API_KEY'] = input('Please enter your MISTRAL_API_KEY: ')

logger = get_logger(__name__)

ai = Genkit(
    plugins=[Mistral()],
    model=mistral_name('mistral-small-latest'),
)


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mistral', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    topic: str = Field(default='artificial intelligence', description='Topic to generate about')


class CodeInput(BaseModel):
    """Input for code generation flow."""

    task: str = Field(default='Write a Python function to calculate fibonacci numbers', description='Coding task')


class CustomConfigInput(BaseModel):
    """Input for custom config flow."""

    task: str = Field(default='creative', description='Task type: creative, precise, or detailed')


class WeatherInput(BaseModel):
    """Input schema for the weather tool."""

    location: str = Field(description='City or location name')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='Paris', description='Location to get weather for')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class EmbedInput(BaseModel):
    """Input for embedding flow."""

    text: str = Field(default='Artificial intelligence is transforming the world.', description='Text to embed')


class CodeEmbedInput(BaseModel):
    """Input for code embedding flow."""

    code: str = Field(
        default='def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)',
        description='Code to embed',
    )


class ImageInput(BaseModel):
    """Input for image description flow."""

    image_url: str = Field(
        default='https://picsum.photos/id/237/400/300',
        description='URL of the image to describe',
    )


class ReasoningInput(BaseModel):
    """Input for reasoning flow."""

    question: str = Field(
        default='John is one of 4 children. His sister is 4 years old. How old is John?',
        description='Reasoning question',
    )


class AudioInput(BaseModel):
    """Input for audio transcription flow."""

    audio_path: str = Field(
        default='',
        description='Path to audio file (defaults to bundled genkit.wav)',
    )


class Skills(BaseModel):
    """A set of core character skills for an RPG character."""

    strength: int = Field(description='strength (0-100)')
    charisma: int = Field(description='charisma (0-100)')
    endurance: int = Field(description='endurance (0-100)')


class RpgCharacter(BaseModel):
    """An RPG character."""

    name: str = Field(description='name of the character')
    back_story: str = Field(description='back story', alias='backStory')
    abilities: list[str] = Field(description='list of abilities (3-4)')
    skills: Skills


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Return a random realistic weather string for a location.

    Args:
        input: Weather input location.

    Returns:
        Weather information with temperature in degrees Celsius.
    """
    weather_options = [
        '18° C sunny with light clouds',
        '22° C partly cloudy',
        '15° C overcast with chance of rain',
        '25° C clear and warm',
    ]
    return f'Weather in {input.location}: {random.choice(weather_options)}'


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a simple greeting.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(prompt=f'Say hello to {input.name}!')
    return response.text


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext | None = None,
) -> str:
    """Generate with streaming response.

    Args:
        input: Input with topic to generate about.
        ctx: Action run context for streaming chunks to client.

    Returns:
        Generated text.
    """
    response = await ai.generate(
        prompt=f'Tell me an interesting fact about {input.topic}',
        on_chunk=ctx.send_chunk if ctx else None,
    )
    return response.text


@ai.flow()
async def code_flow(input: CodeInput) -> str:
    """Generate code using Codestral model.

    Args:
        input: Input with coding task description.

    Returns:
        Generated code.
    """
    response = await ai.generate(
        model=mistral_name('codestral-latest'),
        prompt=input.task,
        system='You are an expert programmer. Provide clean, well-documented code with explanations.',
    )
    return response.text


@ai.flow()
async def say_hi_with_config(input: CustomConfigInput) -> str:
    """Demonstrate custom model configurations for different tasks.

    Shows how different config parameters affect generation behavior:
    - 'creative': High temperature for diverse, creative outputs
    - 'precise': Low temperature for consistent, focused outputs
    - 'detailed': Extended output for comprehensive explanations

    Args:
        input: Input with task type.

    Returns:
        Generated response showing the effect of different configs.
    """
    task = input.task

    prompts = {
        'creative': 'Write a creative story opener about a robot discovering art',
        'precise': 'List the exact steps to make a cup of tea',
        'detailed': 'Explain how photosynthesis works in detail',
    }

    configs: dict[str, dict[str, object]] = {
        'creative': {
            'temperature': 0.9,
            'max_tokens': 200,
            'top_p': 0.95,
            'presence_penalty': 0.6,
            'frequency_penalty': 0.4,
        },
        'precise': {
            'temperature': 0.1,
            'max_tokens': 150,
        },
        'detailed': {
            'temperature': 0.5,
            'max_tokens': 400,
        },
    }

    prompt = prompts.get(task, prompts['creative'])
    config: dict[str, object] = configs.get(task, configs['creative'])

    response = await ai.generate(
        prompt=prompt,
        config=config,
    )
    return response.text


@ai.flow()
async def chat_flow() -> str:
    """Multi-turn chat example demonstrating context retention.

    Returns:
        Final chat response.
    """
    history: list[Message] = []

    # First turn - User shares information
    prompt1 = (
        "Hi! I'm planning a trip to Paris next month. I'm really excited because I love French cuisine, "
        'especially croissants and macarons.'
    )
    response1 = await ai.generate(
        prompt=prompt1,
        system='You are a helpful travel assistant specializing in French destinations.',
    )
    history.append(Message(role=Role.USER, content=[Part(root=TextPart(text=prompt1))]))
    if response1.message:
        history.append(response1.message)
    await logger.ainfo('chat_flow turn 1', result=response1.text)

    # Second turn - Ask question requiring context from first turn
    response2 = await ai.generate(
        messages=[
            *history,
            Message(role=Role.USER, content=[Part(root=TextPart(text='What foods did I say I enjoy?'))]),
        ],
        system='You are a helpful travel assistant specializing in French destinations.',
    )
    history.append(Message(role=Role.USER, content=[Part(root=TextPart(text='What foods did I say I enjoy?'))]))
    if response2.message:
        history.append(response2.message)
    await logger.ainfo('chat_flow turn 2', result=response2.text)

    # Third turn - Ask for recommendation based on context
    response3 = await ai.generate(
        messages=[
            *history,
            Message(
                role=Role.USER,
                content=[Part(root=TextPart(text='Based on our conversation, suggest one bakery I should visit.'))],
            ),
        ],
        system='You are a helpful travel assistant specializing in French destinations.',
    )
    return response3.text


@ai.flow()
async def large_model_flow() -> str:
    """Use Mistral Large for complex reasoning tasks.

    Returns:
        Response from Mistral Large model.
    """
    response = await ai.generate(
        model=mistral_name('mistral-large-latest'),
        prompt=(
            'Analyze the pros and cons of microservices vs monolithic architecture. '
            'Consider scalability, maintainability, and team organization.'
        ),
        system='You are a senior software architect with 20 years of experience.',
    )
    return response.text


@ai.flow()
async def weather_flow(input: WeatherFlowInput) -> str:
    """Get weather using Mistral tool calling.

    Demonstrates how to use tools with Mistral models. The model
    will automatically call the get_weather tool when asked about weather.

    Args:
        input: Input with location to get weather for.

    Returns:
        Weather information for the location.
    """
    response = await ai.generate(
        model=mistral_name('mistral-small-latest'),
        prompt=f'What is the weather in {input.location}?',
        system=(
            'You have a tool called get_weather. '
            "It takes an object with a 'location' field. "
            'Always use this tool when asked about weather.'
        ),
        tools=['get_weather'],
        tool_choice=ToolChoice.REQUIRED,
        max_turns=2,
    )
    return response.text


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character using structured output.

    Demonstrates how to use Mistral's JSON mode for structured output.
    The model returns data that matches the RpgCharacter schema.

    Args:
        input: Input with character name.

    Returns:
        The generated RPG character.
    """
    prompt = (
        f'Generate an RPG character named {input.name}. '
        'Include a creative backstory, 3-4 unique abilities, '
        'and skill ratings for strength, charisma, and endurance (0-100 each).'
    )
    result = await ai.generate(
        model=mistral_name('mistral-small-latest'),
        prompt=prompt,
        output=Output(schema=RpgCharacter),
    )
    return result.output


@ai.flow()
async def embed_flow(input: EmbedInput) -> list[float]:
    """Generate embeddings for text using Mistral's mistral-embed model.

    Embeddings are dense vector representations of text, useful for:
    - Semantic search: find documents similar to a query
    - Clustering: group similar documents together
    - RAG: retrieve relevant context for generation

    Args:
        input: Input with text to embed.

    Returns:
        The embedding vector (list of floats).
    """
    doc = Document.from_text(input.text)
    embeddings = await ai.embed(
        embedder=mistral_name('mistral-embed'),
        content=doc,
    )
    return embeddings[0].embedding


@ai.flow()
async def code_embed_flow(input: CodeEmbedInput) -> list[float]:
    """Generate code embeddings using Mistral's codestral-embed model.

    Codestral Embed produces semantic representations of code snippets,
    useful for code search, clone detection, and similarity comparisons.

    See: https://docs.mistral.ai/models/codestral-embed-25-05

    Args:
        input: Input with code snippet to embed.

    Returns:
        The embedding vector (list of floats).
    """
    doc = Document.from_text(input.code)
    embeddings = await ai.embed(
        embedder=mistral_name('codestral-embed-2505'),
        content=doc,
    )
    return embeddings[0].embedding


@ai.flow()
async def describe_image(input: ImageInput) -> str:
    """Describe an image using Mistral Large 3 (vision).

    Mistral Large 3, Medium 3.1, Small 3.2, and Ministral 3 all support
    image input alongside text. The model can analyze and describe the
    contents of the image.

    See: https://docs.mistral.ai/capabilities/vision/

    Args:
        input: Input with image URL.

    Returns:
        Description of the image.
    """
    response = await ai.generate(
        model=mistral_name('mistral-large-latest'),
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=MediaPart(media=Media(url=input.image_url, content_type='image/png'))),
                    Part(root=TextPart(text='Describe this image in detail.')),
                ],
            ),
        ],
    )
    return response.text


@ai.flow()
async def reasoning_flow(input: ReasoningInput) -> str:
    """Use Magistral for step-by-step reasoning.

    Magistral models think through problems step by step before answering.
    They are optimized for math, logic, and complex reasoning tasks.

    See: https://docs.mistral.ai/capabilities/reasoning

    Args:
        input: Input with reasoning question.

    Returns:
        The reasoned answer.
    """
    response = await ai.generate(
        model=mistral_name('magistral-small-latest'),
        prompt=input.question,
    )
    return response.text


@ai.flow()
async def audio_flow(input: AudioInput) -> str:
    """Transcribe audio using Voxtral Mini.

    Voxtral models accept audio input alongside text. The audio is
    base64-encoded and sent as a MediaPart with audio/* content type.

    Uses the bundled genkit.wav file by default.

    See: https://docs.mistral.ai/capabilities/audio/

    Args:
        input: Input with optional path to an audio file.

    Returns:
        Transcription of the audio content.
    """
    audio_path = input.audio_path or str(Path(__file__).parent.parent / 'assets' / 'genkit.wav')
    audio_bytes = Path(audio_path).read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
    data_uri = f'data:audio/wav;base64,{audio_b64}'

    response = await ai.generate(
        model=mistral_name('voxtral-mini-latest'),
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=MediaPart(media=Media(url=data_uri, content_type='audio/wav'))),
                    Part(root=TextPart(text='Transcribe this audio. Return only the transcription.')),
                ],
            ),
        ],
    )
    return response.text


async def main() -> None:
    """Main entry point for the Mistral sample - keep alive for Dev UI."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
