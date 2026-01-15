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

import asyncio
from pathlib import Path

import structlog
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI

logger = structlog.get_logger(__name__)


current_dir = Path(__file__).resolve().parent
prompts_path = current_dir.parent / 'prompts'

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-3-flash-preview', prompt_dir=prompts_path)


def my_helper(content, *_, **__):
    if isinstance(content, list):
        content = content[0] if content else ''
    return f'*** {content} ***'


ai.define_helper('my_helper', my_helper)


class OutputSchema(BaseModel):
    short: str
    friendly: str
    like_a_pirate: str


@ai.flow(name='simplePrompt')
async def simple_prompt(input: str = ''):
    return await ai.generate(prompt='You are a helpful AI assistant named Walt, say hello')


@ai.flow(name='simpleTemplate')
async def simple_template(input: str = ''):
    name = 'Fred'
    return await ai.generate(prompt=f'You are a helpful AI assistant named Walt. Say hello to {name}.')


hello_dotprompt = ai.define_prompt(
    input_schema={'name': str},
    prompt='You are a helpful AI assistant named Walt. Say hello to {{name}}',
)


class NameInput(BaseModel):
    name: str = 'Fred'


@ai.flow(name='simpleDotprompt')
async def simple_dotprompt(input: NameInput):
    return await hello_dotprompt(input={'name': input.name})


three_greetings_prompt = ai.define_prompt(
    input_schema={'name': str},
    output_schema=OutputSchema,
    prompt='You are a helpful AI assistant named Walt. Say hello to {{name}}, write a response for each of the styles requested',
)


@ai.flow(name='threeGreetingsPrompt')
async def three_greetings(input: str = 'Fred') -> OutputSchema:
    response = await three_greetings_prompt(input={'name': input})
    return response.output


async def main():
    # List actions to verify loading
    actions = ai.registry.list_serializable_actions()

    # Filter for prompts to be specific
    # Keys start with /prompt
    prompts = [key for key in actions.keys() if key.startswith(('/prompt/', '/executable-prompt/'))]

    await logger.ainfo('Registry Status', total_actions=len(actions), loaded_prompts=prompts)

    if not prompts:
        await logger.awarning('No prompts found! Check directory structure.')
        return

    # Execute the 'hello' prompt
    hello_prompt = await ai.prompt('hello')
    response = await hello_prompt(input={'name': 'Genkit User'})

    await logger.ainfo('Prompt Execution Result', text=response.text)

    res = await simple_prompt()
    await logger.ainfo('Flow: simplePrompt', text=res.text)

    res = await simple_template()
    await logger.ainfo('Flow: simpleTemplate', text=res.text)

    res = await simple_dotprompt(NameInput(name='Fred'))
    await logger.ainfo('Flow: simpleDotprompt', text=res.text)

    res = await three_greetings()
    await logger.ainfo('Flow: threeGreetingsPrompt', output=res)

    # Call one of the prompts just to validate everything is hooked up properly
    res = await hello_dotprompt(input={'name': 'Bob'})
    await logger.ainfo('Prompt: hello_dotprompt', text=res.text)


if __name__ == '__main__':
    ai.run_main(main())
