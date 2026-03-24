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

"""Tool interrupts — human-in-the-loop with ctx.interrupt() and tool.respond().

After ``generate`` stops with ``finish_reason`` interrupted, read ``response.interrupts``,
then resume by passing ``your_tool.respond(interrupt, user_output)`` in ``tool_responses``.
See README.md.
"""

import os

from pydantic import BaseModel, Field

from genkit import (
    Genkit,
    ToolRunContext,
)
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.google_genai.models import gemini

ai = Genkit(
    plugins=[GoogleAI()],
    model=f'googleai/{gemini.GoogleAIGeminiVersion.GEMINI_3_FLASH_PREVIEW}',
)


class TriviaQuestions(BaseModel):
    """Trivia questions."""

    question: str = Field(description='the main question')
    answers: list[str] = Field(description='list of multiple choice answers (typically 4), 1 correct 3 wrong')


@ai.tool()
async def present_questions(questions: TriviaQuestions, ctx: ToolRunContext) -> None:
    """Presents questions to the user and responds with the selected answer."""
    ctx.interrupt(questions.model_dump())


@ai.flow()
async def play_trivia(theme: str = 'Science') -> str:
    """Plays a trivia game with the user."""
    response = await ai.generate(
        prompt='You are a trivia game host. Cheerfully greet the user when they '
        + f'first join. The user has selected the theme: "{theme}". '
        + 'Call `present_questions` tool with questions and the tools will present '
        + 'the questions in a nice UI. The user will pick an answer and then you '
        + 'tell them if they were right or wrong. Be dramatic (but terse)! It is a '
        + 'show!\n\n[user joined the game]',
        tools=['present_questions'],
    )

    # Check for interrupts and return the question to the user
    if len(response.interrupts):
        interrupt = response.interrupts[0]
        question_data = interrupt.tool_request.input
        if question_data:
            # For a full interactive flow, you would typically:
            # 1. Prompt the user for their answer here (e.g., using input()).
            # 2. Call present_questions.respond(interrupt, user_answer) and pass that part
            #    in tool_responses= to generate() (see main() below).
            # 3. Regenerate with messages + tool_responses.

            # Prepend the greeting/text response if available
            text_response = (response.text + '\n\n') if response.text else ''
            question = question_data.get('question')
            answers = question_data.get('answers')
            return f'{text_response}INTERRUPTED: {question}\nAnswers: {answers}'
        return 'INTERRUPTED: (No input data)'

    return response.text


async def main() -> None:
    """Dev mode: return immediately; run_main keeps Dev UI alive. Standalone: interactive trivia CLI."""
    if os.environ.get('GENKIT_ENV') == 'dev':
        return
    try:
        response = await ai.generate(
            prompt='You are a trivia game host. Cheerfully greet the user when they '
            + 'first join and ask them for the theme of the trivia game. Suggest '
            + 'a few theme options, but they do not have to use them. When the user is ready, call '
            + '`present_questions` so the UI can show the question and answers. '
            + 'After the user answers, tell them if they were right or wrong. Be dramatic but brief.\n\n'
            + '[user joined the game]',
        )
        messages = response.messages
        while True:
            response = await ai.generate(
                messages=messages,
                prompt=input('Say: '),
                tools=['present_questions'],
            )
            messages = response.messages
            if len(response.interrupts) > 0:
                intr = response.interrupts[0]
                # Use the decorated tool's .respond — not tool_response() or registry lookup by name.
                response_part = present_questions.respond(intr, input('Your answer (number): '))
                response = await ai.generate(
                    messages=messages,
                    tool_responses=[response_part],
                    tools=['present_questions'],
                )
                messages = response.messages
    except Exception as error:
        print(f'Set GEMINI_API_KEY to a valid value before running this sample directly.\n{error}')  # noqa: T201


if __name__ == '__main__':
    ai.run_main(main())
