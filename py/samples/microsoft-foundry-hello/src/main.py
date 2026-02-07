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

"""Microsoft Foundry hello sample - Microsoft Foundry models with Genkit.

This sample demonstrates how to use Microsoft Foundry models with Genkit.
Microsoft Foundry (formerly Azure AI Foundry) provides access to 11,000+ AI models.

Documentation:
- Microsoft Foundry Portal: https://ai.azure.com/
- Model Catalog: https://ai.azure.com/catalog/models
- SDK Overview: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview
- Switching Endpoints: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/switching-endpoints

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Microsoft Foundry   │ Microsoft's AI supermarket. One place to access    │
    │                     │ GPT-4o, Claude, Llama, and 11,000+ more models.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Azure               │ Microsoft's cloud platform. Where the models       │
    │                     │ actually run and your data stays secure.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Endpoint            │ The web address where your AI models live.         │
    │                     │ Like your-resource.openai.azure.com.               │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ API Key             │ Your password to access the models. Keep it        │
    │                     │ secret! Set as AZURE_OPENAI_API_KEY.               │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Deployment          │ A specific instance of a model you've set up.      │
    │                     │ Like having your own copy of GPT-4o.               │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature                          | Example                                |
|----------------------------------|----------------------------------------|
| Plugin Initialization            | `MicrosoftFoundry(api_key=..., ...)`   |
| Default Model Configuration      | `ai = Genkit(model=gpt4o)`             |
| Defining Flows                   | `@ai.flow()` decorator            |
| Defining Tools                   | `@ai.tool()` decorator            |
| Simple Generation                | `say_hi`                          |
| Streaming Generation             | `say_hi_stream`                   |
| Generation with Tools            | `weather_flow`                    |
| Generation Configuration         | `say_hi_with_config`              |
| Code Generation                  | `code_flow`                       |
| Multimodal (Image Input)         | `describe_image`                  |
| Structured Output (JSON)         | `generate_character`              |
| Embeddings                       | `embed_flow`                      |

Endpoint Types
==============
The plugin supports two endpoint types:

1. **Azure OpenAI endpoint** (traditional):
   Format: `https://<resource-name>.openai.azure.com/`
   Requires `api_version` parameter (e.g., '2024-10-21').

2. **Azure AI Foundry project endpoint** (new unified endpoint):
   Format: `https://<resource-name>.services.ai.azure.com/api/projects/<project-name>`
   Uses v1 API - no api_version needed.

The plugin auto-detects the endpoint type based on the URL format.

Authentication Methods
======================
1. **API Key** (simple):
   Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables.

2. **Azure AD / Managed Identity** (recommended for production):
   ```python
   from azure.identity import DefaultAzureCredential, get_bearer_token_provider

   credential = DefaultAzureCredential()
   token_provider = get_bearer_token_provider(credential, 'https://cognitiveservices.azure.com/.default')

   ai = Genkit(
       plugins=[
           MicrosoftFoundry(
               azure_ad_token_provider=token_provider,
               endpoint='https://your-resource.openai.azure.com/',
           )
       ]
   )
   ```

Finding Your Credentials
========================
1. Go to Microsoft Foundry Portal (https://ai.azure.com/)
2. Select your Project
3. Navigate to Models → Deployments
4. Click on your Deployment (e.g., gpt-4o)
5. Open the Details pane

You'll find:
- Target URI: Contains the endpoint URL and API version
- Key: Your API key
- Name: Your deployment name

Testing
=======
1. Set environment variables (extract from Target URI in the Details pane):

   # Example Target URI:
   # https://your-resource.cognitiveservices.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview

   export AZURE_OPENAI_ENDPOINT="https://your-resource.cognitiveservices.azure.com/"  # Base URL only
   export AZURE_OPENAI_API_KEY="your-api-key"  # From Key field
   export AZURE_OPENAI_API_VERSION="2024-05-01-preview"  # From api-version in Target URI
   export AZURE_OPENAI_DEPLOYMENT="gpt-4o"  # From Name field

2. Run the sample:
   ./run.sh

3. Open the Genkit Dev UI and test the flows.

See Also:
    - Microsoft Foundry Documentation: https://learn.microsoft.com/en-us/azure/ai-foundry/
    - Model Catalog: https://ai.azure.com/catalog/models

Note:
    This is a community sample and is not officially endorsed by Microsoft.
    "Microsoft", "Azure", and "Microsoft Foundry" are trademarks of Microsoft Corporation.
"""

import asyncio
import os
import random

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.microsoft_foundry import MicrosoftFoundry, gpt4o, microsoft_foundry_name
from genkit.types import Media, MediaPart, Part, TextPart

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

# Configuration from environment variables
# Find these values in Microsoft Foundry Portal:
# ai.azure.com > [Project] > Models > Deployments > [Deployment] > Details
API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-05-01-preview')
DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')

logger = get_logger(__name__)

# Log configuration for debugging (mask API key for security)

if not API_KEY or not ENDPOINT:
    logger.warning(
        'AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set. Set these environment variables to use the sample.'
    )

ai = Genkit(
    plugins=[
        MicrosoftFoundry(
            api_key=API_KEY,
            endpoint=ENDPOINT,
            api_version=API_VERSION,
            deployment=DEPLOYMENT,
        )
    ],
    model=gpt4o,
)


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='World', description='Name to greet')


class WeatherInput(BaseModel):
    """Weather tool input schema."""

    location: str = Field(description='Location to get weather for')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='San Francisco', description='Location to get weather for')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    topic: str = Field(default='cats', description='Topic to write about')


class ImageDescribeInput(BaseModel):
    """Input for image description flow."""

    # Public domain cat image from Wikimedia Commons (no copyright, free for any use)
    # Source: https://commons.wikimedia.org/wiki/File:Cute_kitten.jpg
    image_url: str = Field(
        default='https://upload.wikimedia.org/wikipedia/commons/1/13/Cute_kitten.jpg',
        description='URL of the image to describe',
    )


class CodeInput(BaseModel):
    """Input for code generation flow."""

    task: str = Field(
        default='Write a Python function to calculate fibonacci numbers',
        description='Coding task description',
    )


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Azure', description='Character name')


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


class EmbedInput(BaseModel):
    """Input for embedding flow."""

    text: str = Field(
        default='The quick brown fox jumps over the lazy dog.',
        description='Text to generate embeddings for',
    )


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a simple greeting.

    This demonstrates basic text generation with Microsoft Foundry.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name} in a friendly way',
    )
    return response.text


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Return weather information for a location.

    This is a mock tool that demonstrates function calling with Microsoft Foundry.

    Args:
        input: Weather input with location.

    Returns:
        Weather information string.
    """
    weather_options = [
        '32° C sunny',
        '17° C cloudy',
        '22° C partly cloudy',
        '19° C humid',
    ]
    return f'{input.location}: {random.choice(weather_options)}'


@ai.flow()
async def weather_flow(input: WeatherFlowInput) -> str:
    """Get weather using function calling.

    This demonstrates Microsoft Foundry's tool/function calling capability.
    """
    response = await ai.generate(
        prompt=f'What is the weather in {input.location}?',
        tools=['get_weather'],
    )
    return response.text


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate streaming response.

    This demonstrates streaming with Microsoft Foundry.
    """
    response = await ai.generate(
        prompt=f'Write a short poem about {input.topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def describe_image(input: ImageDescribeInput) -> str:
    """Describe an image using Microsoft Foundry.

    This demonstrates multimodal capabilities with vision models.
    Note: Requires a vision-capable model like gpt-4o.
    """
    response = await ai.generate(
        prompt=[
            Part(root=TextPart(text='Describe this image in detail')),
            Part(root=MediaPart(media=Media(url=input.image_url, content_type='image/jpeg'))),
        ],
        config={'visual_detail_level': 'auto'},
    )
    return response.text


@ai.flow()
async def say_hi_with_config(input: SayHiInput) -> str:
    """Generate greeting with custom configuration.

    This demonstrates using MicrosoftFoundryConfig for fine-tuned control.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name}',
        config={
            'temperature': 0.9,
            'max_tokens': 50,
            'frequency_penalty': 0.5,
        },
    )
    return response.text


@ai.flow()
async def code_flow(input: CodeInput) -> str:
    """Generate code using Microsoft Foundry models.

    Args:
        input: Input with coding task description.

    Returns:
        Generated code.
    """
    response = await ai.generate(
        prompt=input.task,
        system='You are an expert programmer. Provide clean, well-documented code with explanations.',
    )
    return response.text


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character using structured output.

    Demonstrates JSON mode for structured output with Microsoft Foundry.
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
        prompt=prompt,
        output=Output(schema=RpgCharacter),
    )
    return result.output


@ai.flow()
async def embed_flow(input: EmbedInput) -> list[float]:
    """Generate text embeddings using Microsoft Foundry.

    Demonstrates the embedding capability using text-embedding-3-small,
    which is available through Azure OpenAI endpoints.

    Args:
        input: Input with text to embed.

    Returns:
        First 10 dimensions of the embedding vector.
    """
    embeddings = await ai.embed(
        embedder=microsoft_foundry_name('text-embedding-3-small'),
        content=input.text,
    )
    embedding = embeddings[0].embedding if embeddings else []
    return embedding[:10] if len(embedding) > 10 else embedding


async def main() -> None:
    """Main entry point for the sample."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    await logger.ainfo('Open the Genkit Dev UI to test the flows.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
