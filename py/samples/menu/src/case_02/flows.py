# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from menu_ai import ai
from menu_schemas import AnswerOutputSchema, MenuQuestionInputSchema

from .prompts import s02_dataMenuPrompt


@ai.flow(name='s02_menuQuestion')
def s02_menuQuestionFlow(
    my_input: MenuQuestionInputSchema,
) -> AnswerOutputSchema:
    text = s02_dataMenuPrompt({'question': my_input.question})
    return AnswerOutputSchema(
        answer=text,
    )
