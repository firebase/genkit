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


import base64
import os

from case_05.prompts import s05_readMenuPrompt, s05_textMenuPrompt
from menu_ai import ai
from menu_schemas import (
    AnswerOutputSchema,
    MenuQuestionInputSchema,
    ReadMenuPromptOutputSchema,
    TextMenuQuestionInputSchema,
)


@ai.flow(name='s05_readMenuFlow')
async def s05_readMenuFlow(_) -> ReadMenuPromptOutputSchema:
    image_data_url = inline_data_url('menu.jpeg', 'image/jpeg')
    response = await s05_readMenuPrompt(
        image_url=image_data_url,
    )
    return ReadMenuPromptOutputSchema(
        menu_text=response.text,
    )


@ai.flow(name='s05_textMenuQuestion')
async def s05_textMenuQuestionFlow(
    my_input: TextMenuQuestionInputSchema,
) -> AnswerOutputSchema:
    response = await s05_textMenuPrompt(
        menu_text=my_input.menu_text,
        question=my_input.question,
    )
    return ReadMenuPromptOutputSchema(
        menu_text=response.text,
    )


@ai.flow(name='s05_visionMenuQuestion')
async def s05_visionMenuQuestionFlow(
    my_input: MenuQuestionInputSchema,
) -> AnswerOutputSchema:
    menu_result = await s05_readMenuFlow()
    return s05_textMenuQuestionFlow(
        my_input=TextMenuQuestionInputSchema(
            question=my_input.question,
            menu_text=menu_result.menu_text,
        )
    )


def inline_data_url(image_filename: str, content_type: str) -> str:
    file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', image_filename)
    with open(file_path, 'rb') as image_file:
        image_data = image_file.read()
    base64_data = base64.b64encode(image_data).decode('utf-8')
    return f'data:{content_type};base64,{base64_data}'
