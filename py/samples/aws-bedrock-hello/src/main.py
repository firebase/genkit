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

"""AWS Bedrock hello sample - Foundation models with Genkit.

This sample demonstrates how to use AWS Bedrock models with Genkit,
including tools, streaming, multimodal, and embedding capabilities.

See README.md for setup and testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ AWS Bedrock         │ Amazon's AI model marketplace. One place to        │
    │                     │ access Claude, Llama, Nova, and more.              │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Converse API        │ A unified way to talk to ANY Bedrock model.        │
    │                     │ Same code works for Claude, Llama, Nova, etc.      │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Inference Profile   │ A cross-region alias for a model. Required         │
    │                     │ when using API keys instead of IAM roles.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ IAM Role            │ AWS's way of granting permissions. Like a          │
    │                     │ badge that lets your code access models.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Region              │ Which AWS data center to use. Pick one near        │
    │                     │ you (us-east-1, eu-west-1, ap-northeast-1).        │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[AWSBedrock()])` |
| Default Model Configuration             | `ai = Genkit(model=...)`            |
| Defining Flows                          | `@ai.flow()` decorator              |
| Defining Tools                          | `@ai.tool()` decorator              |
| Pydantic for Tool Input Schema          | `WeatherInput`, `CurrencyInput`     |
| Simple Generation (Prompt String)       | `say_hi`                            |
| Streaming Generation                    | `say_hi_stream`                     |
| Generation with Tools                   | `weather_flow`, `currency_exchange` |
| Generation Configuration (temperature)  | `say_hi_with_config`                |
| Multimodal (Image Input)                | `describe_image`                    |
| Embeddings                              | `embed_text`                        |

Supported Models
================
- Claude (Anthropic): claude-sonnet-4-5, claude-opus-4-5, claude-haiku-4-5
- Nova (Amazon): nova-pro, nova-lite, nova-micro
- Llama (Meta): llama-3.3-70b, llama-4-maverick
- Mistral: mistral-large-3, pixtral-large
- DeepSeek: deepseek-r1, deepseek-v3
- And many more...
"""

import asyncio
import os
import random

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.aws_bedrock import (
    AWSBedrock,
    bedrock_model,
    # Direct model IDs (for IAM credentials)
    claude_sonnet_4_5,
    deepseek_r1,
    # Inference profile helper (for API keys)
    inference_profile,
    nova_pro,
)
from genkit.types import GenerationCommonConfig, Media, MediaPart, Part, TextPart

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

# Prompt for AWS region if not set
if 'AWS_REGION' not in os.environ:
    os.environ['AWS_REGION'] = input('Please enter your AWS_REGION (e.g., us-east-1): ')

logger = get_logger(__name__)

# Default model configuration
# Model IDs without regional prefix - used as base for both auth methods
_CLAUDE_SONNET_MODEL_ID = 'anthropic.claude-sonnet-4-5-20250929-v1:0'
_DEEPSEEK_R1_MODEL_ID = 'deepseek.r1-v1:0'
_NOVA_PRO_MODEL_ID = 'amazon.nova-pro-v1:0'
_TITAN_EMBED_MODEL_ID = 'amazon.titan-embed-text-v2:0'

# Detect authentication method and choose appropriate model reference
# - API keys (AWS_BEARER_TOKEN_BEDROCK) require inference profiles
# - IAM credentials work with direct model IDs
_using_api_key = 'AWS_BEARER_TOKEN_BEDROCK' in os.environ

# Choose models based on auth method
# API keys require inference profiles with regional prefix (us., eu., apac.)
# IAM credentials work with direct model IDs
if _using_api_key:
    _default_model = inference_profile(_CLAUDE_SONNET_MODEL_ID)
    _deepseek_model = inference_profile(_DEEPSEEK_R1_MODEL_ID)
    _nova_model = inference_profile(_NOVA_PRO_MODEL_ID)
    _embed_model = inference_profile(_TITAN_EMBED_MODEL_ID)
    logger.info('Using API key auth - model IDs will use inference profiles')
else:
    _default_model = claude_sonnet_4_5
    _deepseek_model = deepseek_r1
    _nova_model = nova_pro
    _embed_model = bedrock_model(_TITAN_EMBED_MODEL_ID)
    logger.info('Using IAM credentials - model IDs are direct')

# Initialize Genkit with AWS Bedrock plugin
# Region is required - either from env var (prompted above) or explicit
ai = Genkit(
    plugins=[AWSBedrock(region=os.environ.get('AWS_REGION'))],
    model=_default_model,
)


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mittens', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    topic: str = Field(default='cats and their behaviors', description='Topic to write about')


class WeatherInput(BaseModel):
    """Weather tool input schema."""

    location: str = Field(description='Location to get weather for')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='San Francisco', description='Location to get weather for')


class CurrencyInput(BaseModel):
    """Currency conversion tool input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_currency: str = Field(description='Source currency code (e.g., USD)', default='USD')
    to_currency: str = Field(description='Target currency code (e.g., EUR)', default='EUR')


class CurrencyExchangeInput(BaseModel):
    """Currency exchange flow input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_curr: str = Field(description='Source currency code', default='USD')
    to_curr: str = Field(description='Target currency code', default='EUR')


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


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class ImageDescribeInput(BaseModel):
    """Input for image description."""

    image_url: str = Field(
        # Public domain cat image from Wikimedia Commons (no copyright, free for any use)
        # Source: https://commons.wikimedia.org/wiki/File:Cute_kitten.jpg
        default='https://upload.wikimedia.org/wikipedia/commons/1/13/Cute_kitten.jpg',
        description='URL of the image to describe (replace with your own image URL)',
    )


class EmbedInput(BaseModel):
    """Input for embedding flow."""

    text: str = Field(default='Hello, world!', description='Text to embed')


class ReasoningInput(BaseModel):
    """Input for reasoning demo."""

    question: str = Field(
        default='What is 15% of 240? Show your work step by step.',
        description='Question requiring reasoning',
    )


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Return a random realistic weather string for a location.

    Args:
        input: Weather input with location.

    Returns:
        Weather information with temperature in degree Celsius.
    """
    weather_options = [
        '32° C sunny',
        '17° C cloudy',
        '22° C partly cloudy',
        '19° C humid',
        '25° C clear skies',
    ]
    return f'{input.location}: {random.choice(weather_options)}'


@ai.tool()
def convert_currency(input: CurrencyInput) -> str:
    """Convert currency amount.

    Args:
        input: Currency conversion parameters.

    Returns:
        Converted amount string.
    """
    # Mock conversion rates
    rates = {
        ('USD', 'EUR'): 0.85,
        ('EUR', 'USD'): 1.18,
        ('USD', 'GBP'): 0.73,
        ('GBP', 'USD'): 1.37,
        ('USD', 'JPY'): 110.0,
        ('JPY', 'USD'): 0.0091,
    }

    rate = rates.get((input.from_currency, input.to_currency), 1.0)
    converted = input.amount * rate

    return f'{input.amount} {input.from_currency} = {converted:.2f} {input.to_currency}'


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a simple greeting.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name} in a friendly way',
    )
    return response.text


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate streaming response.

    Args:
        input: Input with topic to write about.
        ctx: Action run context for streaming.

    Returns:
        Complete generated text.
    """
    response = await ai.generate(
        prompt=f'Write a short story about {input.topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def say_hi_with_config(input: SayHiInput) -> str:
    """Generate greeting with custom configuration.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name}',
        config=GenerationCommonConfig(
            temperature=0.7,
            max_output_tokens=100,
        ),
    )
    return response.text


@ai.flow()
async def weather_flow(input: WeatherFlowInput) -> str:
    """Get weather using tools.

    Args:
        input: Input with location to get weather for.

    Returns:
        Weather information.
    """
    response = await ai.generate(
        prompt=f'What is the weather in {input.location}?',
        tools=['get_weather'],
    )
    return response.text


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
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character with structured output.

    Args:
        input: Character generation input with name.

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'generate an RPG character named {input.name}',
        output=Output(schema=RpgCharacter),
    )
    return result.output


@ai.flow()
async def describe_image(input: ImageDescribeInput) -> str:
    """Describe an image using Claude or Nova (multimodal models).

    Note: This requires a model that supports image input (Claude, Nova Pro/Lite).

    Args:
        input: Input with image URL.

    Returns:
        Image description.
    """
    response = await ai.generate(
        prompt=[
            Part(root=TextPart(text='Describe this image in detail')),
            Part(root=MediaPart(media=Media(url=input.image_url, content_type='image/jpeg'))),
        ],
    )
    return response.text


@ai.flow()
async def describe_image_nova(input: ImageDescribeInput) -> str:
    """Describe an image using Amazon Nova Pro.

    When using API keys (AWS_BEARER_TOKEN_BEDROCK), this automatically uses
    the inference profile version of the model (e.g., us.amazon.nova-pro-v1:0).

    Args:
        input: Input with image URL.

    Returns:
        Image description.
    """
    response = await ai.generate(
        model=_nova_model,
        prompt=[
            Part(root=TextPart(text='Describe this image')),
            Part(root=MediaPart(media=Media(url=input.image_url, content_type='image/jpeg'))),
        ],
    )
    return response.text


@ai.flow()
async def embed_text(input: EmbedInput) -> list[float]:
    """Generate text embeddings using Amazon Titan.

    When using API keys (AWS_BEARER_TOKEN_BEDROCK), this automatically uses
    the inference profile version of the model.

    Args:
        input: Input with text to embed.

    Returns:
        Embedding vector (first 10 dimensions shown).
    """
    embeddings = await ai.embed(
        embedder=_embed_model,
        content=input.text,
    )
    # Return first 10 dimensions as a sample
    embedding = embeddings[0].embedding if embeddings else []
    return embedding[:10] if len(embedding) > 10 else embedding


@ai.flow()
async def reasoning_demo(input: ReasoningInput) -> str:
    """Demonstrate reasoning with DeepSeek R1.

    Note: DeepSeek R1 includes reasoning content in the response.
    For optimal quality, limit max_tokens to 8,192 or fewer.

    When using API keys (AWS_BEARER_TOKEN_BEDROCK), this automatically uses
    the inference profile version of the model (e.g., us.deepseek.r1-v1:0).

    Args:
        input: Input with question requiring reasoning.

    Returns:
        Answer with reasoning steps.
    """
    response = await ai.generate(
        model=_deepseek_model,
        prompt=input.question,
        config={
            'max_tokens': 4096,
            'temperature': 0.5,
        },
    )
    return response.text


async def main() -> None:
    """Main entry point for the AWS Bedrock sample - keep alive for Dev UI."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
