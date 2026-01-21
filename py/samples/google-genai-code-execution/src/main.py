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

"""Sample demonstrating code execution using the Google Gemini API with GenAI."""

import structlog

from genkit.ai import Genkit
from genkit.blocks.model import MessageWrapper
from genkit.core.typing import CustomPart, Message, TextPart
from genkit.plugins.google_genai import GeminiConfigSchema, GoogleAI
from genkit.plugins.google_genai.models.utils import PartConverter

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-3-flash-preview',
)


@ai.flow()
async def execute_code(task: str) -> MessageWrapper:
    """Execute code for the given task.

    Args:
        name: the task to send to test function

    Returns:
        The generated response enclosed in a MessageWrapper. The content field should contain the following:
        1. CustomPart with executableCode(language and code).
        2. CustomPart with codeExecutionResult(outcome and output).
        3. Textpart describing code and output generated.
    """
    response = await ai.generate(
        prompt=f'Generate and run code for the task: {task}',
        config=GeminiConfigSchema(temperature=1, code_execution=True).model_dump(),
    )
    return response.message


def display_code_execution(message: Message):
    """Display the code execution results from a message."""
    print('\n=== INTERNAL CODE EXECUTION ===')
    for part in message.content:
        if isinstance(part.root, CustomPart):
            if PartConverter.EXECUTABLE_CODE in part.root.custom:
                code_data = part.root.custom[PartConverter.EXECUTABLE_CODE]
                lang = code_data.get(PartConverter.LANGUAGE, 'unknown')
                code = code_data.get(PartConverter.CODE, '')
                print(f'Language: {lang}')
                print(f'```{lang}\n{code}\n```')
            elif PartConverter.CODE_EXECUTION_RESULT in part.root.custom:
                result_data = part.root.custom[PartConverter.CODE_EXECUTION_RESULT]
                outcome = result_data.get(PartConverter.OUTCOME, 'unknown')
                output = result_data.get(PartConverter.OUTPUT, '')
                print('\nExecution result:')
                print(f'Status: {outcome}')
                print('Output:')
                if not output.strip():
                    print('  <no output>')
                else:
                    for line in output.splitlines():
                        print(f'  {line}')
        elif isinstance(part.root, TextPart) and part.root.text.strip():
            print(f'\nExplanation:\n{part.root.text}')
    print('\n=== COMPLETE INTERNAL CODE EXECUTION ===')


async def main() -> None:
    """Main entry point for the Google genai code execution sample - keep alive for Dev UI.

    This function demonstrates how to perform code execution using the
    Genkit framework.
    """
    response_msg = await execute_code('What is the sum of the first 50 prime numbers?')
    display_code_execution(response_msg)
    await logger.ainfo(response_msg.text)


if __name__ == '__main__':
    ai.run_main(main())
