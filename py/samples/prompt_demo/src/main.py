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

import weakref
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
from genkit.plugins.google_genai import GoogleAI

logger = structlog.get_logger(__name__)


current_dir = Path(__file__).resolve().parent
prompts_path = current_dir.parent / 'prompts'

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-3-flash-preview', prompt_dir=prompts_path)


def list_helper(data, *args, **kwargs):
    if not isinstance(data, list):
        return ''
    return '\n'.join(f'- {item}' for item in data)


ai.define_helper('list', list_helper)


class Ingredient(BaseModel):
    name: str
    quantity: str


class Recipe(BaseModel):
    title: str = Field(..., description='recipe title')
    ingredients: list[Ingredient]
    steps: list[str] = Field(..., description='the steps required to complete the recipe')


# Register the schema so it can be resolved by name in prompt files
# Note: internal API usage until define_schema is exposed
if hasattr(ai.registry.dotprompt, '_schemas'):
    ai.registry.dotprompt._schemas['Recipe'] = Recipe

# Global stickiness cache for prompts to prevent premature GC
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
    food: str


@ai.flow(name='chef_flow')
async def chef_flow(input: ChefInput) -> Recipe:
    await logger.ainfo(f'chef_flow called with input: {input}')
    recipe_prompt = await get_sticky_prompt('recipe')
    recipe_prompt._output_format = 'json'
    recipe_prompt._output_schema = Recipe
    recipe_prompt._model = 'googleai/gemini-3-flash-preview'

    response = await recipe_prompt(input={'food': input.food})
    # Ensure we return a Pydantic model as expected by the type hint and caller
    result = Recipe.model_validate(response.output)
    await logger.ainfo(f'chef_flow result: {result}')
    return result


@ai.flow(name='robot_chef_flow')
async def robot_chef_flow(input: ChefInput) -> Recipe:
    await logger.ainfo(f'robot_chef_flow called with input: {input}')
    recipe_prompt = await get_sticky_prompt('recipe', variant='robot')
    recipe_prompt._output_format = 'json'
    recipe_prompt._output_schema = Recipe
    recipe_prompt._model = 'googleai/gemini-3-flash-preview'
    result = Recipe.model_validate((await recipe_prompt(input={'food': input.food})).output)
    await logger.ainfo(f"robot_chef_flow result: {result}")
    return result


class StoryInput(BaseModel):
    subject: str
    personality: str | None = None


@ai.flow(name='tell_story')
async def tell_story(input: StoryInput, ctx: ActionRunContext) -> str:
    await logger.ainfo(f'tell_story called with input: {input}')
    story_prompt = await get_sticky_prompt('story')
    story_prompt._model = 'googleai/gemini-3-flash-preview'
    story_prompt._output_format = None
    stream, response = story_prompt.stream(input={'subject': input.subject, 'personality': input.personality})

    full_text = ''
    # We yield the chunks as they stream in
    async for chunk in stream:
        if chunk.text:
            ctx.send_chunk(chunk.text)
            full_text += chunk.text

    await logger.ainfo(f'tell_story completed, returning length: {len(full_text)}')
    return full_text


async def main():
    # List actions to verify loading
    actions = ai.registry.list_serializable_actions()

    # Filter for prompts
    prompts = [key for key in actions.keys() if key.startswith(('/prompt/', '/executable-prompt/'))]
    await logger.ainfo('Registry Status', total_actions=len(actions), loaded_prompts=prompts)

    if not prompts:
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
    story_stream, _ = tell_story.stream(StoryInput(subject='a brave little toaster', personality='courageous'))

    async for chunk in story_stream:
        print(chunk, end='', flush=True)
        # Note: The actual return value of the flow (final string) is not yielded by the generator in Python's async generator implementation easily
        # unless we wrap it or inspect the StopAsyncIteration value, but typically for streaming flows we just consume the stream.
        # BUT `tell_story` implementation above yields chunks.

    print()  # Newline after stream
    await logger.ainfo('Tell Story Flow Completed')


if __name__ == '__main__':
    ai.run_main(main())
