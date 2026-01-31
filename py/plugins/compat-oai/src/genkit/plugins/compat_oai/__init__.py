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


"""OpenAI-compatible model provider for Genkit.

This plugin provides integration with OpenAI and any OpenAI-compatible API
endpoints (like Azure OpenAI, Together AI, Anyscale, etc.) for the Genkit
framework. It uses the official OpenAI Python SDK.

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                     OpenAI-Compatible Plugin                            │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  ├── OpenAI - Plugin class                                              │
    │  ├── openai_model() - Helper to create model references                 │
    │  └── OpenAIConfig - Configuration schema                                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  typing.py - Type-Safe Configuration Classes                            │
    │  ├── OpenAIConfig (base configuration)                                  │
    │  └── Model-specific parameters                                          │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  openai_plugin.py - Plugin Implementation                               │
    │  ├── OpenAI class (registers models)                                    │
    │  └── Client initialization with OpenAI SDK                              │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models/model.py - Model Implementation                                 │
    │  ├── OpenAIModel (chat completions API)                                 │
    │  ├── Request/response conversion                                        │
    │  └── Streaming support                                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models/handler.py - Request Handler                                    │
    │  └── Message conversion and tool handling                               │
    └─────────────────────────────────────────────────────────────────────────┘

Supported Providers:
    - OpenAI (api.openai.com)
    - Azure OpenAI
    - Together AI
    - Anyscale
    - Any OpenAI-compatible endpoint

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.compat_oai import OpenAI

    # Uses OPENAI_API_KEY env var or pass api_key explicitly
    ai = Genkit(plugins=[OpenAI()], model='openai/gpt-4o')

    response = await ai.generate(prompt='Hello, GPT!')
    print(response.text)

    # With custom endpoint (e.g., Together AI)
    ai = Genkit(
        plugins=[OpenAI(base_url='https://api.together.xyz/v1')],
        model='openai/meta-llama/Llama-3-70b-chat-hf',
    )
    ```

Caveats:
    - Requires OPENAI_API_KEY environment variable or api_key parameter
    - Model names are prefixed with 'openai/' (e.g., 'openai/gpt-4o')
    - Custom endpoints may have different model availability

See Also:
    - OpenAI documentation: https://platform.openai.com/docs/
    - Genkit documentation: https://genkit.dev/
"""

from .openai_plugin import OpenAI, openai_model
from .typing import OpenAIConfig


def package_name() -> str:
    """The package name for the OpenAI-compatible model provider."""
    return 'genkit.plugins.compat_oai'


__all__ = ['OpenAI', 'OpenAIConfig', 'openai_model', 'package_name']
