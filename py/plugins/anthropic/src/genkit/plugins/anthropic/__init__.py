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

"""Anthropic plugin for Genkit.

This plugin provides integration with Anthropic's Claude models for the
Genkit framework. It registers Claude models as Genkit actions, enabling
text generation operations.

Overview:
    The Anthropic plugin adds support for Claude models to Genkit. It uses
    the official Anthropic Python SDK and registers models that can be used
    with ai.generate() and other Genkit generation methods.

Supported Models:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Model                     │ Description                                 │
    ├───────────────────────────┼─────────────────────────────────────────────┤
    │ claude-3-5-sonnet-latest  │ Balanced performance and capability         │
    │ claude-3-5-haiku-latest   │ Fast and cost-effective                     │
    │ claude-3-opus-latest      │ Most capable, complex tasks                 │
    │ claude-sonnet-4-20250514  │ Latest Sonnet model                         │
    └───────────────────────────┴─────────────────────────────────────────────┘

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component           │ Purpose                                           │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ Anthropic           │ Plugin class to register with Genkit              │
    │ anthropic_name()    │ Helper to create namespaced model names           │
    └─────────────────────┴───────────────────────────────────────────────────┘

Example:
    Basic usage:

    ```python
    from genkit import Genkit
    from genkit.plugins.anthropic import Anthropic

    # Uses ANTHROPIC_API_KEY env var or pass api_key explicitly
    ai = Genkit(
        plugins=[Anthropic()],
        model='anthropic/claude-3-5-sonnet-latest',
    )

    response = await ai.generate(prompt='Hello, Claude!')
    print(response.text)

    # With custom configuration
    response = await ai.generate(
        model='anthropic/claude-3-5-haiku-latest',
        prompt='Write a haiku about AI',
        config={'temperature': 0.7, 'max_tokens': 100},
    )
    ```

    With tools:

    ```python
    @ai.tool()
    def get_weather(city: str) -> str:
        return f'Weather in {city}: Sunny, 72°F'


    response = await ai.generate(
        model='anthropic/claude-3-5-sonnet-latest',
        prompt='What is the weather in Paris?',
        tools=['get_weather'],
    )
    ```

Caveats:
    - Requires ANTHROPIC_API_KEY environment variable or api_key parameter
    - Model names are prefixed with 'anthropic/' (e.g., 'anthropic/claude-3-5-sonnet-latest')
    - Anthropic models may have different tool calling behavior than Google models

See Also:
    - Anthropic documentation: https://docs.anthropic.com/
    - Genkit documentation: https://genkit.dev/
"""

from genkit.plugins.anthropic.plugin import Anthropic, anthropic_name

__all__ = ['Anthropic', 'anthropic_name']
