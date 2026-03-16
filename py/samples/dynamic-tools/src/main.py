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

"""Dynamic tools demo - ai.dynamic_tool() and ai.run() for runtime tools and traced sub-spans."""

import os

import structlog
from pydantic import BaseModel, Field

from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.5-flash',
)


class DynamicToolInput(BaseModel):
    """Input for dynamic tool demo."""

    value: int = Field(default=5, description='Value to pass to the dynamic tool')


class RunStepInput(BaseModel):
    """Input for run step demo."""

    data: str = Field(default='hello world', description='Data to process in the traced step')


class CombinedInput(BaseModel):
    """Input for combined demo."""

    input_val: str = Field(default='Dynamic tools demo', description='Input value for demo')


@ai.flow()
async def dynamic_tool_demo(input: DynamicToolInput) -> dict[str, object]:
    """Create and invoke a tool at runtime using ai.dynamic_tool().

    Unlike ``@ai.tool()`` which globally registers a tool, dynamic tools
    are created on-the-fly and exist only for the current scope. They
    can be called directly or passed to ``ai.generate(tools=[...])``.

    Args:
        input: Input with a value to pass to the dynamic tool.

    Returns:
        A dict containing the tool result and metadata.
    """

    def multiplier_fn(x: int) -> int:
        return x * 10

    dynamic_multiplier = ai.dynamic_tool(
        name='dynamic_multiplier',
        fn=multiplier_fn,
        description='Multiplies input by 10',
    )
    result = await dynamic_multiplier.run(input.value)

    return {
        'input_value': input.value,
        'tool_result': result.response,
        'tool_name': dynamic_multiplier.metadata.get('name', 'unknown'),
        'tool_metadata': dynamic_multiplier.metadata,
    }


@ai.flow()
async def run_step_demo(input: RunStepInput) -> dict[str, str]:
    """Wrap a plain function as a traceable step using ai.run().

    ``ai.run(name=..., fn=...)`` creates a named sub-span in the trace.
    The step's output is recorded and visible in the Dev UI trace viewer.

    Args:
        input: Input with data to process.

    Returns:
        A dict containing the original and processed data.
    """

    async def uppercase() -> str:
        return input.data.upper()

    async def reverse() -> str:
        return step1[::-1]

    step1 = await ai.run(name='uppercase_step', fn=uppercase)
    step2 = await ai.run(name='reverse_step', fn=reverse)

    return {
        'original': input.data,
        'after_uppercase': step1,
        'after_reverse': step2,
    }


@ai.flow()
async def combined_demo(input: CombinedInput) -> dict[str, object]:
    """Combine ai.run() sub-spans with ai.dynamic_tool() in one flow.

    This flow demonstrates using both features together:
    1. ``ai.run()`` wraps a preprocessing function as a trace span.
    2. ``ai.dynamic_tool()`` creates a scaler tool at runtime.
    3. Both appear in the trace as inspectable steps.

    Args:
        input: Input with a value string.

    Returns:
        A dict with results from both the step and the dynamic tool.
    """

    async def preprocess() -> str:
        return f'processed: {input.input_val}'

    step_result = await ai.run(name='preprocess_step', fn=preprocess)

    async def scale_fn(x: int) -> int:
        return x * 10

    scaler = ai.dynamic_tool(name='scaler', fn=scale_fn, description='Scales input by 10')
    tool_result = await scaler.run(7)

    return {
        'step_result': step_result,
        'tool_result': tool_result.response,
        'tool_metadata': scaler.metadata,
    }


async def main() -> None:
    pass


if __name__ == '__main__':
    ai.run_main(main())
