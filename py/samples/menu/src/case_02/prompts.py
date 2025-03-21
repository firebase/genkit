# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from menu_ai import ai
from menu_schemas import MenuQuestionInputSchema

from genkit.plugins.google_genai.models.gemini import gemini15Flash

s02_dataMenuPrompt = ai.define_prompt(
    variant='s02_dataMenu',
    model=gemini15Flash,
    input_schema=MenuQuestionInputSchema,
    output_format='text',
    tools=['menuTool'],
    system="""You are acting as a helpful AI assistant named Walt that can answer
questions about the food available on the menu at Walt's Burgers.

Answer this customer's question, in a concise and helpful manner,
as long as it is about food on the menu or something harmless like sports.
Use the tools available to answer menu questions.
DO NOT INVENT ITEMS NOT ON THE MENU.

Question:
{{question}} ?
""",
)
