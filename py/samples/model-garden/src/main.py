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

"""Model Garden sample.

from typing import Annotated
import asyncio

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
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
        ModelGardenPlugin(),
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

    amount: float = Field(description='Amount to convert', default=100)
    from_curr: str = Field(description='Source currency code', default='USD')
    to_curr: str = Field(description='Target currency code', default='EUR')

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
#     result = ''
#     async for data in stream:
#         for part in data.content:
#             result += part.root.text
#     return result


@ai.flow()
async def jokes_flow(subject: Annotated[str, Field(default='banana')] = 'banana') -> str:
    """Generate a joke about the given subject.

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


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    response = await ai.generate(
        # model=model_garden_name('meta/llama-3.2-90b-vision-instruct-maas'),
        # Using Anthropic for Model Garden example as it is reliably available
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        config={'temperature': 1},
        prompt=f'hi {name}',
    )

    return response.text


@ai.flow()
async def say_hi_stream(
    name: Annotated[str, Field(default='Alice')] = 'Alice',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Say hi to a name and stream the response.

    Args:
        name: The name to say hi to.
        ctx: Action context for streaming.

    Returns:
        The response from the model.
    """
    stream, _ = ai.generate_stream(
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        config={'temperature': 1},
        prompt=f'hi {name}',
    )
    result = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        result += data.text
    return result


@ai.flow()
async def weather_flow(location: Annotated[str, Field(default='Paris, France')] = 'Paris, France') -> str:
    """Tool calling with Model Garden."""
    response = await ai.generate(
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        tools=['getWeather'],
        prompt=f"What's the weather in {location}?",
        config={'temperature': 1},
    )
    return response.text


async def main() -> None:
    """Main entry point for the Model Garden sample - keep alive for Dev UI."""
    import asyncio

    # For testing/demo purposes, you can uncomment these to run them on startup:
    # await logger.ainfo(await say_hi('Alice'))
    # await logger.ainfo(await jokes_flow('banana'))

    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
