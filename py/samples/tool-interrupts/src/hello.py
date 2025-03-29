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

from pydantic import BaseModel, Field

from genkit.ai import (
    Genkit,
    ToolRunContext,
    tool_response,
)
from genkit.plugins.google_genai import GoogleGenai

ai = Genkit(
    plugins=[GoogleGenai()],
    model='google_genai/gemini-2.0-flash',
)


class TriviaQuestions(BaseModel):
    """Trivia questions."""

    question: str = Field(description='the main question')
    answers: list[str] = Field(description='list of multiple choice answers (typically 4), 1 correct 3 wrong')


@ai.tool("can present questions to the user, responds with the user' selected answer")
def present_questions(questions: TriviaQuestions, ctx: ToolRunContext):
    ctx.interrupt(questions)


async def main() -> None:
    response = await ai.generate(
        prompt='You a trivia game host. Cheerfully greet the user when they '
        + 'first join and ank them to for the theme of the trivia game, suggest '
        + "a few theme options, they don't have to use your suggestion, feel free "
        + 'to be silly. When they user us ready, call '
        + '`present_questions` tool with questions and the tools will present '
        + 'the questions in a nice UI. The user will pick an answer and then you '
        + 'tell them if they were right or wrong. Be dramatic (but terse)! It is a '
        + 'show!\n\n[user joined the game]',
    )
    print(response.text)
    messages = response.messages
    while True:
        response = await ai.generate(
            messages=messages,
            prompt=input('Say: '),
            tools=['present_questions'],
        )
        messages = response.messages
        if len(response.tool_requests) > 0:
            request = response.tool_requests[0]
            print(request.tool_request.input.get('question'))
            i = 1
            for question in request.tool_request.input.get('answers'):
                print(f'   ({i}) {question}')
                i += 1

            tr = tool_response(request, input('Your answer (number): '))
            response = await ai.generate(
                messages=messages,
                tool_responses=[tr],
                tools=['present_questions'],
            )
            print(response.text)
            messages = response.messages
        else:
            print(response.text)


if __name__ == '__main__':
    asyncio.run(main())
