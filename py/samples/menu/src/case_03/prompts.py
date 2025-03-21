# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from menu_ai import ai
from menu_schemas import DataMenuQuestionInputSchema

from genkit.plugins.google_genai.models.gemini import gemini15Flash

s03_chatPreamblePrompt = ai.define_prompt(
    variant='s03_chatPreamble',
    model=gemini15Flash,
    input_schema=DataMenuQuestionInputSchema,
    output_format='text',
    config={'temperature': 0.3},
    system="""{{ role "user" }}
  Hi. What's on the menu today?

  {{ role "model" }}
  I am Walt, a helpful AI assistant here at the restaurant.
  I can answer questions about the food on the menu or any other questions
  you have about food in general. I probably can't help you with anything else.
  Here is today's menu:
  {{#each menuData~}}
  - {{this.title}} ${{this.price}}
    {{this.description}}
  {{~/each}}
  Do you have any questions about the menu?
""",
)
