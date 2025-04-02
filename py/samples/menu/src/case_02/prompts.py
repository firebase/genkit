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
from menu_ai import ai
from menu_schemas import MenuQuestionInputSchema

from genkit.plugins.google_genai import google_genai_name
from genkit.plugins.google_genai.models.gemini import GeminiVersion

s02_dataMenuPrompt = ai.define_prompt(
    variant='s02_dataMenu',
    model=google_genai_name(GeminiVersion.GEMINI_1_5_FLASH),
    input_schema=MenuQuestionInputSchema,
    tools=['menu_tool'],
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
