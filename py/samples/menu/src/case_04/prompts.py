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
from menu_schemas import DataMenuQuestionInputSchema

from genkit.plugins.google_genai import google_genai_name
from genkit.plugins.google_genai.models.gemini import GeminiVersion

s04_ragDataMenuPrompt = ai.define_prompt(
    variant='s04_ragDataMenu',
    model=google_genai_name(GeminiVersion.GEMINI_1_5_FLASH),
    input_schema=DataMenuQuestionInputSchema,
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
