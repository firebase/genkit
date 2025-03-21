# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from menu_ai import ai
from menu_schemas import ReadMenuImagePromptSchema, TextMenuQuestionInputSchema

from genkit.plugins.google_genai.models.gemini import gemini15Flash

s05_readMenuPrompt = ai.define_prompt(
    variant='s05_readMenu',
    model=gemini15Flash,
    input_schema=ReadMenuImagePromptSchema,
    output_format='text',
    config={'temperature': 0.1},
    system="""
Extract _all_ of the text, in order,
from the following image of a restaurant menu.

{{media url=image_url}}
""",
)

s05_textMenuPrompt = ai.define_prompt(
    variant='s05_textMenu',
    model=gemini15Flash,
    input_schema=TextMenuQuestionInputSchema,
    output_format='text',
    config={'temperature': 0.3},
    system="""
You are acting as Walt, a helpful AI assistant here at the restaurant.
You can answer questions about the food on the menu or any other questions
customers have about food in general.

Here is the text of today's menu to help you answer the customer's question:
{{menu_text}}

Answer this customer's question:
{{question}}?
""",
)
