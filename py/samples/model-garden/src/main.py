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

import os
import asyncio

import structlog
from pydantic import Field

from genkit.ai import Genkit
from genkit.plugins.vertex_ai.model_garden import ModelGardenPlugin, model_garden_name
from genkit.plugins.google_genai import VertexAI
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


def get_project_id() -> str:
    """Get Google Cloud project ID from environment or prompt user."""
    project_id = os.getenv('GCLOUD_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        project_id = input('Enter your Google Cloud Project ID: ').strip()
        if not project_id:
            raise ValueError('Project ID is required.')
        os.environ['GCLOUD_PROJECT'] = project_id
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
        VertexAI(location=location),
        ModelGardenPlugin(
            project_id=project_id,
            location=location,
            model_locations={
                'meta/llama-3.2-90b-vision-instruct-maas': 'us-central1',
                'anthropic/claude-sonnet-4@20250514': 'us-east5',
            },
        ),
    ],
)



class WeatherInput(BaseModel):
    location: str = Field(..., description="Location for which to get the weather, ex: San-Francisco, CA")


@ai.tool()
def get_weather(input: WeatherInput) -> dict:
    """Used to get current weather for a location."""
    return {
        'location': input.location,
        'temperature_celcius': 21.5,
        'conditions': 'cloudy',
    }


class TemperatureInput(BaseModel):
    celsius: float = Field(..., description="Temperature in Celsius")


@ai.tool()
def celsius_to_fahrenheit(input: TemperatureInput) -> float:
    """Converts Celsius to Fahrenheit."""
    return (input.celsius * 9) / 5 + 32


class ToolFlowInput(BaseModel):
    location: str = Field('Paris, France', description="Location to check weather for")


@ai.flow(name='gemini-2.5-flash - tool_flow')
async def gemini_model(input: ToolFlowInput) -> str:
    """Gemini tool flow.
    
    Args:
        location: The location to check weather for.
    """
    response = await ai.generate(
        model='vertexai/gemini-2.5-flash',
        config={'temperature': 1},
        tools=['get_weather', 'celsius_to_fahrenheit'],
        prompt=f"What's the weather in {input.location}? Convert the temperature to Fahrenheit.",
    )
    return response.text


@ai.flow(name='llama-3.2 - basic_flow')
async def llama_model(location: str = None) -> str:
    """Generate a greeting.

    Args:
        location: Ignored input to match JS sample.
    """
    response = await ai.generate(
        model=model_garden_name('meta/llama-3.2-90b-vision-instruct-maas'),
        config={'temperature': 1},
        prompt='You are a helpful assistant named Walt. Say hello',
    )
    return response.text




@ai.flow(name='claude-sonnet-4 - tool_calling_flow')
async def anthropic_model(input: ToolFlowInput) -> str:
    """Anthropic tool flow.
    
    Args:
        location: The location to check weather for.
    """
    response = await ai.generate(
        # Note: The model name includes the publisher prefix for Model Garden
        model=model_garden_name('anthropic/claude-sonnet-4@20250514'),
        config={'temperature': 1},
        tools=['get_weather', 'celsius_to_fahrenheit'],
        prompt=f"What's the weather in {input.location}? Convert the temperature to Fahrenheit.",
    )
    return response.text


# @ai.flow()
# async def jokes_flow(subject: str) -> str:
#     """Generate a joke about the given subject.
# 
#     Args:
#         subject: The subject of the joke.
# 
#     Returns:
#         The generated joke.
#     """
#     response = await ai.generate(
#         # Note: The model name usually includes the publisher prefix for Model Garden
#         model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
#         config={'temperature': 1, 'max_output_tokens': 1024},
#         prompt=f'Tell a short joke about {subject}',
#     )
# 
#     return response.text


class MistralExplainInput(BaseModel):
    concept: str = Field('concurrency', description="Concept to explain")


# @ai.flow(name='mistral-medium - explain_concept')
async def mistral_explain_concept(input: MistralExplainInput) -> str:
    """Explain a concept using Mistral Medium.
    
    Args:
        input: The input object.
    """
    response = await ai.generate(
        model=model_garden_name('mistral-medium-3'),
        prompt=f'Explain {input.concept} in programming. Include practical examples.',
        config={'temperature': 0.7},
    )
    return response.text


class MistralAnalyzeInput(BaseModel):
    code: str = Field("console.log('hello world');", description="Code to analyze")


# @ai.flow(name='mistral-small - analyze_code')
async def analyze_code(input: MistralAnalyzeInput) -> str:
    """Analyze code using Mistral Small.
    
    Args:
        input: The input object.
    """
    response = await ai.generate(
        model=model_garden_name('mistral-small-2503'),
        prompt=f'Analyze this code for potential issues and suggest improvements:\\n{input.code}',
    )
    return response.text


class GenerateFunctionInput(BaseModel):
    description: str = Field(
        'greets me and asks my favourite colour',
        description='Description of what the function should do.',
    )


# @ai.flow(name='codestral - generate_function')
async def generate_function(input: GenerateFunctionInput) -> str:
    """Generate a function using Codestral.
    
    Args:
        input: The input object containing the description.
    """
    response = await ai.generate(
        model=model_garden_name('codestral-2'),
        prompt=f'Create a Python function that {input.description}. Include error handling and types.',
    )
    return response.text


async def main() -> None:
    await logger.ainfo(await llama_model())
    # await logger.ainfo(await jokes_flow('banana'))
    await logger.ainfo(await anthropic_model(ToolFlowInput(location='Paris, France')))
    
    # Gemini flows
    await logger.ainfo(await gemini_model(ToolFlowInput(location='Paris, France')))
    
    # Mistral flows - Commenting out as they require project enablement
    # await logger.ainfo(await mistral_explain_concept(MistralExplainInput(concept='concurrency')))
    # await logger.ainfo(await analyze_code(MistralAnalyzeInput(code="console.log('hello world');")))
    # await logger.ainfo(await generate_function(GenerateFunctionInput(description='greets me and asks my favourite colour')))
    
    # Keep the process alive for Dev UI
    print('Genkit server running. Press Ctrl+C to stop.')
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
