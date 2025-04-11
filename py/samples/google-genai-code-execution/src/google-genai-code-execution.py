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
from genkit.plugins.google_genai import GoogleAI, googleai_name
from genkit.plugins.google_genai.models.gemini import GeminiConfigSchema

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model=googleai_name('gemini-2.0-flash-exp'),
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
        config=GeminiConfigSchema(temperature=1, code_execution=True),
    )
    return response.message


async def main() -> None:
    """Main entry point for the  Google genai code execution sample.

    This function demonstrates how to perform code execution using the
    Genkit framework.
    """
    await logger.ainfo(await execute_code('What is the sum of the first 50 prime numbers?'))


if __name__ == '__main__':
    ai.run_main(main())
