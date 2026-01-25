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

"""Prompt demo sample."""

import os
import weakref
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from genkit.ai import ActionKind, Genkit
from genkit.core.action import ActionRunContext
from genkit.plugins.google_genai import GoogleAI

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

logger = structlog.get_logger(__name__)


current_dir = Path(__file__).resolve().parent
prompts_path = current_dir.parent / 'prompts'

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-3-flash-preview', prompt_dir=prompts_path)


def list_helper(data, *args, **kwargs):
    """Format a list of strings as bullet points.

    Args:
        data: List of items to format.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        Formatted string or empty string if not a list.
    """
    if not isinstance(data, list):
        return ''
    return '\n'.join(f'- {item}' for item in data)


ai.define_helper('list', list_helper)


class Ingredient(BaseModel):
    """An ingredient in a recipe."""

    name: str
    quantity: str


class Recipe(BaseModel):
    """A recipe."""

    title: str = Field(..., description='recipe title')
    ingredients: list[Ingredient]
    steps: list[str] = Field(..., description='the steps required to complete the recipe')


ai.define_schema('Recipe', Recipe)

_sticky_prompts = {}


async def get_sticky_prompt(name: str, variant: str | None = None):
    """Helper to get a prompt and keep it alive."""
    key = f'{name}:{variant}' if variant else name
    if key in _sticky_prompts:
        return _sticky_prompts[key]

    prompt = await ai.prompt(name, variant=variant)
    if isinstance(prompt, weakref.ReferenceType):
        ref = prompt
        prompt = ref()
        if prompt is None:
            # Stale reference; retry loading the prompt as the comments suggest.
            prompt = await ai.prompt(name, variant=variant)
            if isinstance(prompt, weakref.ReferenceType):
                prompt = prompt()
            if prompt is None:
                raise RuntimeError(f"Failed to load prompt '{name}' with variant '{variant}' after retry.")

    # Store strong ref
    _sticky_prompts[key] = prompt
    return prompt


class ChefInput(BaseModel):
    """Input for the chef flow."""

    food: str


@ai.flow(name='chef_flow')
async def chef_flow(input: ChefInput) -> Recipe:
    """Generate a recipe for the given food.

    Args:
        input: Input containing the food item.

    Returns:
        A formatted recipe.

    Example:
        >>> await chef_flow(ChefInput(food='banana bread'))
        Recipe(title='Banana Bread', ...)
    """
    await logger.ainfo(f'chef_flow called with input: {input}')
    recipe_prompt = await get_sticky_prompt('recipe')

    response = await recipe_prompt(input={'food': input.food})
    # Ensure we return a Pydantic model as expected by the type hint and caller
    result = Recipe.model_validate(response.output)
    await logger.ainfo(f'chef_flow result: {result}')
    return result


@ai.flow(name='robot_chef_flow')
async def robot_chef_flow(input: ChefInput) -> Recipe:
    """Generate a robot-themed recipe for the given food.

    Args:
        input: Input containing the food item.

    Returns:
        A formatted robot recipe.

    Example:
        >>> await robot_chef_flow(ChefInput(food='cookie'))
        Recipe(title='Robo-Cookie', ...)
    """
    await logger.ainfo(f'robot_chef_flow called with input: {input}')
    recipe_prompt = await get_sticky_prompt('recipe', variant='robot')
    result = Recipe.model_validate((await recipe_prompt(input={'food': input.food})).output)
    await logger.ainfo(f'robot_chef_flow result: {result}')
    return result


class StoryInput(BaseModel):
    """Input for the story flow."""

    subject: str
    personality: str | None = None


@ai.flow(name='tell_story')
async def tell_story(input: StoryInput, ctx: ActionRunContext) -> str:
    """Tell a story about the given subject.

    Args:
        input: Input containing the subject and optional personality.
        ctx: Action context for streaming.

    Returns:
        The generated story text.

    Example:
        >>> await tell_story(StoryInput(subject='toaster', personality='courageous'), ctx)
        'Once upon a time...'
    """
    await logger.ainfo(f'tell_story called with input: {input}')
    story_prompt = await get_sticky_prompt('story')
    stream, _response = story_prompt.stream(input={'subject': input.subject, 'personality': input.personality})

    full_text = ''
    async for chunk in stream:
        if chunk.text:
            ctx.send_chunk(chunk.text)
            full_text += chunk.text

    await logger.ainfo(f'tell_story completed, returning length: {len(full_text)}')
    return full_text


async def main():
    """Run the sample flows."""
    prompts = ai.registry.get_actions_by_kind(ActionKind.PROMPT)
    executable_prompts = ai.registry.get_actions_by_kind(ActionKind.EXECUTABLE_PROMPT)
    all_prompts = list(prompts.keys()) + list(executable_prompts.keys())

    await logger.ainfo('Registry Status', loaded_prompts=all_prompts)

    if not all_prompts:
        await logger.awarning('No prompts found! Check directory structure.')
        return

    # Chef Flow
    await logger.ainfo('--- Running Chef Flow ---')
    chef_result = await chef_flow(ChefInput(food='banana bread'))
    await logger.ainfo('Chef Flow Result', result=chef_result.model_dump())

    # Robot Chef Flow
    await logger.ainfo('--- Running Robot Chef Flow ---')
    robot_result = await robot_chef_flow(ChefInput(food='cookie'))
    await logger.ainfo('Robot Chef Flow Result', result=robot_result)

    # Tell Story Flow (Streaming)
    await logger.ainfo('--- Running Tell Story Flow ---')
    # To demonstrate streaming, we'll iterate over the streamer if calling directly like a flow would be consumed.
    story_stream, _ = tell_story.stream(StoryInput(subject='a brave little toaster', personality='courageous'))  # type: ignore

    async for chunk in story_stream:
        print(chunk, end='', flush=True)

    print()  # Newline after stream
    await logger.ainfo('Tell Story Flow Completed')


if __name__ == '__main__':
    ai.run_main(main())
