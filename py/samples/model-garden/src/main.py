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

"""Model Garden sample."""

import asyncio
import os

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.google_genai import VertexAI
from genkit.plugins.vertex_ai.model_garden import ModelGardenPlugin, model_garden_name

logger = structlog.get_logger(__name__)


def get_project_id() -> str:
    """Get Google Cloud project ID from environment or prompt user."""
    project_id = os.getenv('GCLOUD_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        # Fallback to a hardcoded default for testing if env var is missing,
        # or raise error. Since user provided a project ID that had quotes,
        # they likely set it in env var.
        raise ValueError('Environment variable GCLOUD_PROJECT or GOOGLE_CLOUD_PROJECT must be set.')

    # Sanitize project_id to remove potential smart quotes or regular quotes
    project_id = project_id.strip().strip("'").strip('"').strip('‘').strip('’')

    # Update env vars so other plugins (like VertexAI) pick up the sanitized ID
    os.environ['GCLOUD_PROJECT'] = project_id
    os.environ['GOOGLE_CLOUD_PROJECT'] = project_id

    return project_id


def get_location() -> str:
    """Get Google Cloud location from environment or prompt user."""
    location = os.getenv('GOOGLE_CLOUD_LOCATION') or os.getenv('GOOGLE_CLOUD_REGION')
    if not location:
        location = input('Enter your Google Cloud Location (default: us-central1): ').strip()
        if not location:
            location = 'us-central1'
        os.environ['GOOGLE_CLOUD_LOCATION'] = location
    return location


project_id = get_project_id()
location = get_location()

ai = Genkit(
    plugins=[
        ModelGardenPlugin(
            project_id=project_id,
            location=location,
            model_locations={
                'anthropic/claude-sonnet-4@20250514': 'us-east5',
                'meta/llama-3.2-90b-vision-instruct-maas': 'us-central1',
                'mistralai/ministral-3-14b-instruct-2512': 'us-central1',
                'mistralai/mistral-large-3-instruct-2512': 'us-central1',
                'Mistral-Nemo-Instruct-2407': 'us-central1',
                'mistral-ai/mixtral': 'us-central1',
            },
        ),
        VertexAI(location=location),
    ],
)


class WeatherInput(BaseModel):
    """Input for getting weather."""

    location: str = Field(..., description='Location for which to get the weather, ex: San-Francisco, CA')


@ai.tool()
def get_weather(input: WeatherInput) -> dict:
    """Used to get current weather for a location."""
    return {
        'location': input.location,
        'temperature_celcius': 21.5,
        'conditions': 'cloudy',
    }


class TemperatureInput(BaseModel):
    """Input for converting temperature."""

    celsius: float = Field(..., description='Temperature in Celsius')


@ai.tool()
def celsius_to_fahrenheit(input: TemperatureInput) -> float:
    """Converts Celsius to Fahrenheit."""
    return (input.celsius * 9) / 5 + 32


class ToolFlowInput(BaseModel):
    """Input for tool flow."""

    location: str = Field('Paris, France', description='Location to check weather for')


@ai.flow(name='gemini-2.5-flash - tool_flow')
async def gemini_model(input: ToolFlowInput) -> str:
    """Gemini tool flow.

    Args:
        input: The location input.
    """
    response = await ai.generate(
        model='vertexai/gemini-2.5-flash',
        config={'temperature': 1},
        tools=['get_weather', 'celsius_to_fahrenheit'],
        prompt=f"What's the weather in {input.location}? Convert the temperature to Fahrenheit.",
    )
    return response.text


@ai.flow(name='llama-3.2 - basic_flow')
async def llama_model() -> str:
    """Generate a greeting."""
    try:
        response = await ai.generate(
            model=model_garden_name('meta/llama-3.2-90b-vision-instruct-maas'),
            config={
                'temperature': 1,
                'location': 'us-central1',
            },
            prompt='You are a helpful assistant named Walt. Say hello',
        )
        logger.info(f'Response received: {response.text[:100] if response.text else "None"}')
        return response.text
    except Exception as e:
        logger.error(f'Error in llama 3.2 basic_flow: {e}', exc_info=True)
        raise


@ai.flow(name='claude-sonnet-4 - tool_calling_flow')
async def anthropic_model(input: ToolFlowInput) -> str:
    """Anthropic tool flow.

    Args:
        input: The location input.
    """
    response = await ai.generate(
        # Note: The model name includes the publisher prefix for Model Garden
        model=model_garden_name('anthropic/claude-sonnet-4@20250514'),
        config={'temperature': 1},
        tools=['get_weather', 'celsius_to_fahrenheit'],
        prompt=f"What's the weather in {input.location}? Convert the temperature to Fahrenheit.",
    )
    return response.text

    Field(description='Amount to convert', default=100)
    Field(description='Source currency code', default='USD')
    Field(description='Target currency code', default='EUR')


class MistralInput(BaseModel):
    """Input for Mistral Medium flow."""

    concept: str = Field('concurrency', description='Programming concept to explain')


@ai.flow(name='ministral-3 - explain_concept')
async def explain_concept(input: MistralInput) -> str:
    """Explain a concept using Ministral 3 .

    Args:
        input: The input object.
    """
    response = await ai.generate(
        model=model_garden_name('mistralai/ministral-3'),
        prompt=f'Explain {input.concept} in programming. Include practical examples.',
        config={'temperature': 0.7},
    )
    return response.text


class MistralAnalyzeInput(BaseModel):
    """Input for Mistral code analysis."""

    code: str = Field("console.log('hello world');", description='Code to analyze')


@ai.flow(name='mistral-large-3 - analyze_code')
async def analyze_code(input: MistralAnalyzeInput) -> str:
    """Analyze code using Mistral Large 3.

    Args:
        input: The input object.
    """
    response = await ai.generate(
        model=model_garden_name('mistralai/mistral-large-3'),
        prompt=f'Analyze this code for potential issues and suggest improvements:\n{input.code}',
    )
    return response.text


class GenerateFunctionInput(BaseModel):
    """Input for function generation."""

    description: str = Field(
        'greets me and asks my favourite colour',
        description='Description of what the function should do.',
    )


@ai.flow(name='mistral-nemo - generate_function')
async def generate_function(input: GenerateFunctionInput) -> str:
    """Generate a function using Mistral Nemo.

    Args:
        input: The input object containing the description.
    """
    response = await ai.generate(
        model=model_garden_name('mixtral'),
        prompt=f'Create a Python function that {input.description}. Include error handling and types.',
    )
    return response.text


@ai.flow(name='mixtral - jokes_flow')
async def jokes_flow(subject: str) -> str:
    """Tell a joke about the subject using Mixtral."""
    response = await ai.generate(
        model=model_garden_name('mistral-ai/mixtral'),
        prompt=f'Tell a clean joke about {subject}.',
    )
    return response.text


async def main() -> None:
    """Main entry point for the Model Garden sample - keep alive for Dev UI."""


    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
