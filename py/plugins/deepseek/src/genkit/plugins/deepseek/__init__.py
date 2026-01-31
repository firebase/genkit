# Copyright 2026 Google LLC
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

"""DeepSeek plugin for Genkit.

This plugin provides integration with DeepSeek's AI models for the
Genkit framework. DeepSeek offers powerful reasoning models (R1) and
general-purpose models (V3) with competitive performance.

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        DeepSeek Plugin                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  ├── DeepSeek - Plugin class                                            │
    │  ├── deepseek_name() - Helper to create namespaced model names          │
    │  └── DEFAULT_DEEPSEEK_API_URL - API endpoint constant                   │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  plugin.py - Plugin Implementation                                      │
    │  ├── DeepSeek class (registers models)                                  │
    │  └── Configuration and API key handling                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  client.py - API Client                                                 │
    │  ├── DeepSeekClient (OpenAI-compatible API)                             │
    │  └── Request/response handling                                          │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models.py - Model Implementation                                       │
    │  ├── DeepSeekModel (generation logic)                                   │
    │  └── Streaming support                                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  model_info.py - Model Registry                                         │
    │  ├── SUPPORTED_MODELS (deepseek-r1, deepseek-v3, etc.)                  │
    │  └── Model capabilities and metadata                                    │
    └─────────────────────────────────────────────────────────────────────────┘

Supported Models:
    - deepseek-chat: General-purpose chat model
    - deepseek-reasoner: R1 reasoning model with chain-of-thought

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.deepseek import DeepSeek

    # Uses DEEPSEEK_API_KEY env var or pass api_key explicitly
    ai = Genkit(plugins=[DeepSeek()], model='deepseek/deepseek-chat')

    response = await ai.generate(prompt='Hello, DeepSeek!')
    print(response.text)
    ```

Caveats:
    - Requires DEEPSEEK_API_KEY environment variable or api_key parameter
    - Model names are prefixed with 'deepseek/' (e.g., 'deepseek/deepseek-chat')
    - Uses OpenAI-compatible API format

See Also:
    - DeepSeek documentation: https://api-docs.deepseek.com/
    - Genkit documentation: https://genkit.dev/
"""

from .client import DEFAULT_DEEPSEEK_API_URL
from .models import deepseek_name
from .plugin import DeepSeek

__all__ = ['DEFAULT_DEEPSEEK_API_URL', 'DeepSeek', 'deepseek_name']
