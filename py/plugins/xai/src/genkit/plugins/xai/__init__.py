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

"""xAI plugin for Genkit.

This plugin provides integration with xAI's Grok models for the
Genkit framework. It registers Grok models as Genkit actions, enabling
text generation and multimodal operations.

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           xAI Plugin                                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  ├── XAI - Plugin class                                                 │
    │  └── xai_name() - Helper to create namespaced model names               │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  plugin.py - Plugin Implementation                                      │
    │  ├── XAI class (registers models)                                       │
    │  └── Client initialization with xAI API                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models.py - Model Implementation                                       │
    │  ├── XAIModel (OpenAI-compatible API integration)                       │
    │  ├── Request/response conversion                                        │
    │  └── Streaming support                                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  model_info.py - Model Registry                                         │
    │  ├── SUPPORTED_MODELS (grok-3, grok-3-mini, grok-4, etc.)               │
    │  └── Model capabilities and metadata                                    │
    └─────────────────────────────────────────────────────────────────────────┘

Supported Models:
    - grok-3: Latest Grok model with multimodal capabilities
    - grok-3-mini: Smaller, faster variant
    - grok-4: Most capable model
    - grok-vision-beta: Vision model for image understanding

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.xai import XAI

    # Uses XAI_API_KEY env var or pass api_key explicitly
    ai = Genkit(plugins=[XAI()], model='xai/grok-3')

    response = await ai.generate(prompt='Hello, Grok!')
    print(response.text)
    ```

Caveats:
    - Requires XAI_API_KEY environment variable or api_key parameter
    - Model names are prefixed with 'xai/' (e.g., 'xai/grok-3')
    - Uses OpenAI-compatible API format

See Also:
    - xAI documentation: https://docs.x.ai/
    - Genkit documentation: https://genkit.dev/
"""

from genkit.plugins.xai.plugin import XAI, xai_name

__all__ = ['XAI', 'xai_name']
