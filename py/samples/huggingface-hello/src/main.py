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

"""Hugging Face hello sample - Access 1M+ models with Genkit.

This sample demonstrates how to use Hugging Face's Inference API with Genkit,
giving you access to millions of open-source models through a unified interface.

See README.md for testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Hugging Face        │ The "GitHub for AI models". Hosts millions of      │
    │                     │ models you can use through their API.              │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Inference API       │ HF's API to run models. Like a free trial for      │
    │                     │ AI models with rate limits.                        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Model ID            │ The model's address on HF, like "meta-llama/       │
    │                     │ Llama-3.3-70B-Instruct". Owner/model-name format.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Inference Providers │ 17+ partner services (Cerebras, Groq, Together)    │
    │                     │ accessible through one HF API. Pick the fastest!   │
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
| Plugin Initialization                   | `ai = Genkit(plugins=[HuggingFace()])` |
| Default Model Configuration             | `ai = Genkit(model=huggingface_name())`|
| Defining Flows                          | `@ai.flow()` decorator                  |
| Defining Tools                          | `@ai.tool()` decorator                  |
| Simple Generation (Prompt String)       | `say_hi`                                |
| Streaming Response                      | `streaming_flow`                        |
| Different Models                        | `llama_flow`, `qwen_flow`               |
| Generation with Config                  | `custom_config_flow`                    |
| Multi-turn Chat                         | `chat_flow`                             |
| Tool Calling                            | `weather_flow`                          |
| Structured Output (JSON)                | `generate_character`                    |
"""

import asyncio
import os
import random

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.core.typing import Message, Part, Role, TextPart, ToolChoice
from genkit.plugins.huggingface import HuggingFace, huggingface_name

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if 'HF_TOKEN' not in os.environ:
    os.environ['HF_TOKEN'] = input('Please enter your HF_TOKEN: ')

logger = get_logger(__name__)

# Default to a popular, capable model
ai = Genkit(
    plugins=[HuggingFace()],
    model=huggingface_name('mistralai/Mistral-7B-Instruct-v0.3'),
)


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Hugging Face', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    topic: str = Field(default='machine learning', description='Topic to generate about')


class ModelInput(BaseModel):
    """Input for model-specific flows."""

    prompt: str = Field(default='What is the meaning of life?', description='Prompt to send to the model')


class CustomConfigInput(BaseModel):
    """Input for custom config flow."""

    task: str = Field(default='creative', description='Task type: creative, precise, or detailed')


class WeatherInput(BaseModel):
    """Input schema for the weather tool."""

    location: str = Field(description='City or location name')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='San Francisco', description='Location to get weather for')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Luna', description='Character name')


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
        '20° C sunny with light breeze',
        '15° C foggy morning',
        '22° C clear skies',
        '18° C partly cloudy',
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
async def streaming_flow(
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
async def llama_flow(input: ModelInput) -> str:
    """Use Meta's Llama model for generation.

    Args:
        input: Input with prompt.

    Returns:
        Generated response from Llama.
    """
    response = await ai.generate(
        model=huggingface_name('meta-llama/Llama-3.1-8B-Instruct'),
        prompt=input.prompt,
    )
    return response.text


@ai.flow()
async def qwen_flow(input: ModelInput) -> str:
    """Use Alibaba's Qwen model for generation.

    Args:
        input: Input with prompt.

    Returns:
        Generated response from Qwen.
    """
    response = await ai.generate(
        model=huggingface_name('Qwen/Qwen2.5-7B-Instruct'),
        prompt=input.prompt,
    )
    return response.text


@ai.flow()
async def gemma_flow(input: ModelInput) -> str:
    """Use Google's Gemma model for generation.

    Args:
        input: Input with prompt.

    Returns:
        Generated response from Gemma.
    """
    response = await ai.generate(
        model=huggingface_name('google/gemma-2-9b-it'),
        prompt=input.prompt,
    )
    return response.text


@ai.flow()
async def custom_config_flow(input: CustomConfigInput) -> str:
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
    prompt1 = "Hi! I'm learning about neural networks. I find the concept of backpropagation particularly interesting."
    response1 = await ai.generate(
        prompt=prompt1,
        system='You are a helpful AI tutor specializing in machine learning.',
    )
    history.append(Message(role=Role.USER, content=[Part(root=TextPart(text=prompt1))]))
    if response1.message:
        history.append(response1.message)
    await logger.ainfo('chat_flow turn 1', result=response1.text)

    # Second turn - Ask question requiring context from first turn
    response2 = await ai.generate(
        messages=[
            *history,
            Message(role=Role.USER, content=[Part(root=TextPart(text='What concept did I say I find interesting?'))]),
        ],
        system='You are a helpful AI tutor specializing in machine learning.',
    )
    history.append(
        Message(role=Role.USER, content=[Part(root=TextPart(text='What concept did I say I find interesting?'))])
    )
    if response2.message:
        history.append(response2.message)
    await logger.ainfo('chat_flow turn 2', result=response2.text)

    # Third turn - Ask for more details based on context
    response3 = await ai.generate(
        messages=[
            *history,
            Message(
                role=Role.USER, content=[Part(root=TextPart(text='Can you explain that concept in simple terms?'))]
            ),
        ],
        system='You are a helpful AI tutor specializing in machine learning.',
    )
    return response3.text


@ai.flow()
async def weather_flow(input: WeatherFlowInput) -> str:
    """Get weather using Hugging Face tool calling.

    Demonstrates how to use tools with Hugging Face models. The model
    will automatically call the get_weather tool when asked about weather.

    Note: Tool calling support depends on the specific model. Many popular
    models like Llama 3 and Mistral support function calling.

    Args:
        input: Input with location to get weather for.

    Returns:
        Weather information for the location.
    """
    response = await ai.generate(
        model=huggingface_name('mistralai/Mistral-7B-Instruct-v0.3'),
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

    Demonstrates how to use JSON mode for structured output with
    Hugging Face models. The model returns data that matches the
    RpgCharacter schema.

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
        model=huggingface_name('mistralai/Mistral-7B-Instruct-v0.3'),
        prompt=prompt,
        output=Output(schema=RpgCharacter),
    )
    return result.output


async def main() -> None:
    """Main entry point for the Hugging Face sample - keep alive for Dev UI."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
