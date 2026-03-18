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

"""Dynamic tools - create tools at runtime and trace plain functions."""

from pydantic import BaseModel, Field

from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-2.5-flash')


class DynamicToolInput(BaseModel):
    """Input for runtime tool creation."""

    value: int = Field(default=5, description='Value to square with a runtime tool')


class RunStepInput(BaseModel):
    """Input for traced step demo."""

    text: str = Field(default='hello dynamic tools', description='Text to process with traced steps')


@ai.flow()
async def dynamic_tool_demo(input: DynamicToolInput) -> str:
    """Create a tool at runtime and call it immediately."""

    async def square(value: int) -> int:
        return value * value

    tool = ai.dynamic_tool(name='square', description='Square a number', fn=square)
    result = await tool.run(input.value)
    return f'{input.value} squared is {result.response}'


@ai.flow()
async def run_step_demo(input: RunStepInput) -> dict[str, int | str]:
    """Wrap plain async functions in traceable `ai.run()` steps."""

    async def normalize() -> str:
        return input.text.strip().lower()

    async def count_words() -> int:
        return len(normalized.split())

    normalized = await ai.run(name='normalize_text', fn=normalize)
    word_count = await ai.run(name='count_words', fn=count_words)
    return {'normalized': normalized, 'word_count': word_count}


async def main() -> None:
    """Run both dynamic tool demos once."""

    print(await dynamic_tool_demo(DynamicToolInput()))  # noqa: T201
    print(await run_step_demo(RunStepInput()))  # noqa: T201


if __name__ == '__main__':
    ai.run_main(main())
