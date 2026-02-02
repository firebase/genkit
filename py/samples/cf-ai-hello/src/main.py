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

"""CF AI Hello World Sample - Cloudflare Workers AI.

This sample demonstrates how to use Cloudflare Workers AI models with Genkit,
including text generation, streaming, tool calling, and embeddings.

Cloudflare Workers AI runs AI models at the edge, providing low-latency
inference with global availability. This plugin supports:

- Text generation with Llama, Mistral, Qwen, and other models
- Streaming responses via Server-Sent Events (SSE)
- Tool/function calling for supported models
- Text embeddings using BGE and other embedding models

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Workers AI          │ AI models running on Cloudflare's global network.  │
    │                     │ Like having smart robots in data centers worldwide.│
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Edge Computing      │ Processing data close to where users are located.  │
    │                     │ Like having mini-computers in every neighborhood.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Getting the AI response word-by-word as it thinks. │
    │                     │ Like watching someone type their answer in chat.   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Embeddings          │ Converting text into numbers that capture meaning. │
    │                     │ Like translating words into coordinates on a map.  │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    User Request
         │
         ▼
    ┌───────────────────┐
    │  Genkit Flow      │
    │  (say_hello)      │
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐     ┌───────────────────┐
    │ CfAI Plugin       │────▶│ Cloudflare Edge   │
    │ (cf-ai)           │     │ (Global Network)  │
    └───────────────────┘     └─────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │ Llama 3.1 8B      │
                              │ (or other model)  │
                              └─────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │ AI Response       │
                              │ (text/stream)     │
                              └───────────────────┘

Testing Instructions:

    1. Set environment variables:
       export CLOUDFLARE_ACCOUNT_ID=your_account_id
       export CLOUDFLARE_API_TOKEN=your_api_token

    2. Run the sample:
       ./run.sh

    3. Open DevUI at http://localhost:4000

    4. Test flows:
       - say_hello: Enter a name, get a greeting
       - streaming_demo: Watch tokens stream in real-time
       - tool_demo: See weather tool in action
       - embedding_demo: Generate text embeddings
"""

import asyncio

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit import Genkit
from genkit.plugins.cf_ai import (
    CfAI,
    bge_base_en,
    cf_model,
)
from genkit.plugins.cf_ai.typing import CfConfig
from genkit.types import Media, MediaPart, Message, Part, Role, TextPart

install_rich_traceback(show_locals=True, width=120, extra_lines=3)


# Initialize Genkit with CF AI plugin
ai = Genkit(
    plugins=[CfAI()],
    model=cf_model('@cf/meta/llama-3.1-8b-instruct'),
)


class HelloInput(BaseModel):
    """Input for the say_hello flow.

    Attributes:
        name: Name of the person to greet.
    """

    name: str = Field(
        default='World',
        description='Name of the person to greet',
    )


@ai.flow()
async def say_hello(input: HelloInput) -> str:
    """Generate a friendly greeting for someone.

    This flow demonstrates basic text generation with Cloudflare Workers AI.

    Args:
        input: HelloInput with the name to greet.

    Returns:
        A friendly greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name}! Be friendly and creative.',
    )
    return response.text


class StreamingInput(BaseModel):
    """Input for the streaming demo flow.

    Attributes:
        prompt: The prompt to send to the model.
    """

    prompt: str = Field(
        default='Tell me a short joke about programming.',
        description='Prompt for streaming generation',
    )


@ai.flow()
async def streaming_demo(input: StreamingInput) -> str:
    """Demonstrate streaming text generation.

    This flow shows how to use streaming with Cloudflare Workers AI,
    where tokens are received one at a time as the model generates them.

    Args:
        input: StreamingInput with the prompt.

    Returns:
        The complete generated text.
    """
    result_text = ''
    stream, _ = ai.generate_stream(prompt=input.prompt)
    async for chunk in stream:
        result_text += chunk.text
        # In a real application, you would stream this to the client
    return result_text


class WeatherInput(BaseModel):
    """Input for the get_weather tool.

    Attributes:
        location: The city or location to get weather for.
    """

    location: str = Field(
        description='The city or location to get weather for',
    )


@ai.tool()
async def get_weather(input: WeatherInput) -> str:
    """Get the current weather for a location.

    This is a mock weather tool to demonstrate tool calling.

    Args:
        input: WeatherInput with the location to check.

    Returns:
        A weather description string.
    """
    # Mock implementation - in production, call a real weather API
    return f'The weather in {input.location} is sunny, 72°F (22°C) with clear skies.'


class ToolDemoInput(BaseModel):
    """Input for the tool demo flow.

    Attributes:
        location: Location to check weather for.
    """

    location: str = Field(
        default='San Francisco',
        description='Location to check weather for',
    )


@ai.flow()
async def tool_demo(input: ToolDemoInput) -> str:
    """Demonstrate tool calling with Cloudflare Workers AI.

    This flow shows how models can call tools to get external information.

    Args:
        input: ToolDemoInput with the location.

    Returns:
        A response that incorporates the tool result.
    """
    response = await ai.generate(
        prompt=f'What is the weather like in {input.location}? Use the get_weather tool to find out.',
        tools=['get_weather'],
    )
    return response.text


class EmbeddingInput(BaseModel):
    """Input for the embedding demo flow.

    Attributes:
        text: Text to generate embedding for.
    """

    text: str = Field(
        default='Hello, world! This is a test of text embeddings.',
        description='Text to embed',
    )


@ai.flow()
async def embedding_demo(input: EmbeddingInput) -> dict[str, object]:
    """Demonstrate text embedding generation.

    This flow shows how to generate vector embeddings for text using
    Cloudflare's BGE embedding models.

    Args:
        input: EmbeddingInput with the text to embed.

    Returns:
        Dictionary with embedding dimensions and first few values.
    """
    result = await ai.embed(
        embedder=bge_base_en,
        content=input.text,
    )

    if result:
        embedding = result[0].embedding
        return {
            'text': input.text,
            'dimensions': len(embedding),
            'first_5_values': embedding[:5],
            'model': '@cf/baai/bge-base-en-v1.5',
        }

    return {'error': 'No embeddings generated'}


class ModelComparisonInput(BaseModel):
    """Input for comparing different models.

    Attributes:
        prompt: The prompt to test with different models.
    """

    prompt: str = Field(
        default='Explain quantum computing in one sentence.',
        description='Prompt for model comparison',
    )


@ai.flow()
async def model_comparison(input: ModelComparisonInput) -> dict[str, str]:
    """Compare responses from different Cloudflare AI models.

    This flow demonstrates using multiple models and comparing their outputs.

    Args:
        input: ModelComparisonInput with the prompt.

    Returns:
        Dictionary mapping model names to their responses.
    """
    models = [
        '@cf/meta/llama-3.1-8b-instruct',
        '@hf/mistral/mistral-7b-instruct-v0.2',
    ]

    results: dict[str, str] = {}

    for model_id in models:
        try:
            response = await ai.generate(
                prompt=input.prompt,
                model=cf_model(model_id),
            )
            results[model_id] = response.text
        except Exception as e:
            results[model_id] = f'Error: {e!s}'

    return results


class ImageDescribeInput(BaseModel):
    """Input for image description flow.

    Attributes:
        image_url: URL of the image to describe.
    """

    image_url: str = Field(
        # Public domain cat image from Wikimedia Commons (no copyright, free for any use)
        # Source: https://commons.wikimedia.org/wiki/File:Cute_kitten.jpg
        default='https://upload.wikimedia.org/wikipedia/commons/1/13/Cute_kitten.jpg',
        description='URL of the image to describe (replace with your own image URL)',
    )


@ai.flow()
async def describe_image(input: ImageDescribeInput) -> str:
    """Describe an image using a multimodal Cloudflare AI model.

    This flow demonstrates multimodal capabilities with vision models like
    Llama 4 Scout and Gemma 3. Note that not all Cloudflare models support
    image inputs.

    Args:
        input: ImageDescribeInput with the image URL.

    Returns:
        A description of the image.
    """
    response = await ai.generate(
        # Use a multimodal model that supports image inputs
        model=cf_model('@cf/meta/llama-4-scout-17b-16e-instruct'),
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=TextPart(text='Describe this image in detail.')),
                    Part(root=MediaPart(media=Media(url=input.image_url))),
                ],
            )
        ],
    )
    return response.text


class ConfigDemoInput(BaseModel):
    """Input for config demo flow.

    Attributes:
        prompt: The prompt to generate with.
    """

    prompt: str = Field(
        default='Write a haiku about programming.',
        description='Prompt for generation with custom config',
    )


@ai.flow()
async def say_hi_with_config(input: ConfigDemoInput) -> str:
    """Generate text with custom configuration.

    This flow demonstrates using CfConfig for fine-tuned control over
    generation parameters like temperature, top_k, and repetition_penalty.

    Args:
        input: ConfigDemoInput with the prompt.

    Returns:
        The generated text.
    """
    response = await ai.generate(
        prompt=input.prompt,
        config=CfConfig(
            temperature=0.9,  # Higher for more creativity
            top_k=40,  # Limit token selection
            repetition_penalty=1.2,  # Discourage repetition
            max_output_tokens=256,
        ),
    )
    return response.text


async def main() -> None:
    """Main entry point for the sample application."""
    print('CF AI Hello sample started.')
    print('Open http://localhost:4000 to access the DevUI.')
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
