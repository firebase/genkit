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

"""DeepSeek hello sample.

Key features demonstrated in this sample:

| Feature Description                     | Example Function / Code Snippet         |
|-----------------------------------------|-----------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[DeepSeek(...)])`  |
| Default Model Configuration             | `ai = Genkit(model=deepseek_name(...))` |
| Defining Flows                          | `@ai.flow()` decorator                  |
| Defining Tools                          | `@ai.tool()` decorator                  |
| Pydantic for Tool Input Schema          | `WeatherInput`                          |
| Simple Generation (Prompt String)       | `say_hi`                                |
| Streaming Response                      | `streaming_flow`                        |
| Generation with Tools                   | `weather_flow`                          |
| Reasoning Model (deepseek-reasoner)     | `reasoning_flow`                        |
| Generation with Config                  | `custom_config_flow`                    |
| Multi-turn Chat                         | `chat_flow`                             |
"""

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
from genkit.plugins.deepseek import DeepSeek, deepseek_name
from genkit.types import Message, Role, TextPart

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[DeepSeek()],
    model=deepseek_name('deepseek-chat'),
)


class WeatherInput(BaseModel):
    """Input schema for the weather tool."""

    location: str = Field(description='Location to get weather for')


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Get weather of a location, the user should supply a location first.

    Args:
        input: Weather input with location (city and state, e.g. San Francisco, CA).

    Returns:
        Weather information.
    """
    return f'24°C'


@ai.flow()
async def say_hi(name: str) -> str:
    """Generate a simple greeting.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(prompt=f'Say hello to {name}!')
    return response.text


@ai.flow()
async def streaming_flow(topic: str, ctx: ActionRunContext) -> str:
    """Generate with streaming response.

    Args:
        topic: Topic to generate about.
        ctx: Action run context for streaming chunks to client.

    Returns:
        Generated text.
    """
    response = await ai.generate(
        prompt=f'Tell me a fun fact about {topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def weather_flow(location: str) -> str:
    """Get weather using tools.

    Args:
        location: Location to get weather for.

    Returns:
        Weather information.
    """
    response = await ai.generate(
        prompt=f"How's the weather in {location}?",
        tools=['get_weather'],
    )
    return response.text


@ai.flow()
async def reasoning_flow() -> str:
    """Solve a classic reasoning problem using deepseek-reasoner model.

    Returns:
        The reasoning and answer.
    """
    response = await ai.generate(
        model=deepseek_name('deepseek-reasoner'),
        prompt='What is heavier, one kilo of steel or one kilo of feathers?',
    )
    return response.text


@ai.flow()
async def custom_config_flow(prompt: str) -> str:
    """Generate with custom model configuration.

    Args:
        prompt: The prompt to generate from.

    Returns:
        Generated response.
    """
    response = await ai.generate(
        prompt=prompt,
        config={
            'temperature': 0.7,
            'max_tokens': 256,
        },
    )
    return response.text


@ai.flow()
async def chat_flow() -> str:
    """Multi-turn chat example.

    Returns:
        Final chat response.
    """
    history = []
    # First turn
    prompt1 = 'My name is Alice.'
    response1 = await ai.generate(
        prompt=prompt1,
    )
    history.append(Message(role=Role.USER, content=[TextPart(text=prompt1)]))
    history.append(response1.message)
    await logger.ainfo('chat_flow turn 1', result=response1.text)

    # Second turn - model should remember context from previous turns
    response2 = await ai.generate(
        messages=history
        + [Message(role=Role.USER, content=[TextPart(text='What is my name?')])],
        system='You are a helpful assistant. Remember previous conversation.',
    )
    return response2.text


async def main() -> None:
    """Main entry point for the DeepSeek sample."""
    # Simple greeting
    result = await say_hi('World')
    await logger.ainfo('say_hi', result=result)

    # Streaming response
    result = await streaming_flow('deepseek')
    await logger.ainfo('streaming_flow', result=result)

    # Weather with tools
    result = await weather_flow('Hangzhou, Zhejiang')
    await logger.ainfo('weather_flow', result=result)

    # Reasoning model
    result = await reasoning_flow()
    await logger.ainfo('reasoning_flow', result=result)

    # Custom config
    result = await custom_config_flow('Write a haiku about AI.')
    await logger.ainfo('custom_config_flow', result=result)

    # Multi-turn chat
    result = await chat_flow()
    await logger.ainfo('chat_flow', result=result)


if __name__ == '__main__':
    ai.run_main(main())
