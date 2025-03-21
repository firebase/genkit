# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from menu_ai import ai
from menu_schemas import DataMenuQuestionInputSchema

from genkit.plugins.google_genai.models.gemini import gemini15Flash

s04_ragDataMenuPrompt = ai.define_prompt(
    variant='s04_ragDataMenu',
    model=gemini15Flash,
    input_schema=DataMenuQuestionInputSchema,
    output_format='text',
    config={'temperature': 0.3},
    system="""
You are acting as Walt, a helpful AI assistant here at the restaurant.
You can answer questions about the food on the menu or any other questions
customers have about food in general.

Here are some items that are on today's menu that are relevant to
helping you answer the customer's question:
{{#each menuData~}}
- {{this.title}} ${{this.price}}
  {{this.description}}
{{~/each}}

Answer this customer's question:
{{question}}?
""",
)
