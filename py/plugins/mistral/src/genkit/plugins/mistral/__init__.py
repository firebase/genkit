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

"""Mistral AI plugin for Genkit.

This plugin provides integration with Mistral AI's models for the
Genkit framework. Mistral AI offers powerful, efficient language models
including Mistral Large, Mistral Small, and specialized coding models.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Mistral AI          │ French AI company known for efficient, powerful    │
    │                     │ open-weight models. Great balance of speed/quality.│
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Mistral Large       │ Most capable model. Best for complex reasoning,    │
    │                     │ coding, and nuanced tasks.                         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Mistral Small       │ Fast and efficient. Great for everyday tasks       │
    │                     │ like chat, summarization, and simple coding.       │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Codestral           │ Specialized coding model. Optimized for code       │
    │                     │ generation, completion, and explanation.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Pixtral             │ Vision-language model. Can understand images       │
    │                     │ and answer questions about them.                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Function Calling    │ Model can call your tools/functions. Like giving   │
    │                     │ the AI a toolbox to help answer questions.         │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                  HOW MISTRAL PROCESSES YOUR REQUEST                     │
    │                                                                         │
    │    Your Code                                                            │
    │    ai.generate(prompt="Explain quantum computing...")                   │
    │         │                                                               │
    │         │  (1) Request goes to Mistral plugin                           │
    │         ▼                                                               │
    │    ┌─────────────────┐                                                  │
    │    │  Mistral        │   Adds API key, formats request                  │
    │    │  Plugin         │   (Mistral SDK format)                           │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (2) HTTPS to api.mistral.ai                              │
    │             ▼                                                           │
    │    ════════════════════════════════════════════════════                 │
    │             │  Internet                                                 │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Mistral API    │   Model processes your prompt                    │
    │    │  (Large/Small)  │   Supports tools, vision, streaming              │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (3) Response with generated text                         │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Your App       │   response.text = "Quantum computing is..."      │
    │    └─────────────────┘                                                  │
    └─────────────────────────────────────────────────────────────────────────┘

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        Mistral AI Plugin                                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  ├── Mistral - Plugin class                                             │
    │  ├── mistral_name() - Helper to create namespaced model names           │
    │  └── DEFAULT_MISTRAL_API_URL - API endpoint constant                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  plugin.py - Plugin Implementation                                      │
    │  ├── Mistral class (registers models)                                   │
    │  └── Configuration and API key handling                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models.py - Model Implementation                                       │
    │  ├── MistralModel (generation logic)                                    │
    │  ├── Message conversion (Genkit <-> Mistral)                            │
    │  └── Streaming support                                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  model_info.py - Model Registry                                         │
    │  ├── SUPPORTED_MODELS (mistral-large, mistral-small, etc.)              │
    │  └── Model capabilities and metadata                                    │
    └─────────────────────────────────────────────────────────────────────────┘

Supported Models:
    - mistral-large-latest: Most capable model for complex tasks
    - mistral-small-latest: Fast and efficient for everyday use
    - codestral-latest: Specialized for code generation
    - pixtral-large-latest: Vision-language model
    - ministral-8b-latest: Compact model for edge deployment
    - ministral-3b-latest: Smallest model for resource-constrained environments

Supported Embedders:
    - mistral-embed: 1024-dimensional text embeddings for RAG and search

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.mistral import Mistral

    # Uses MISTRAL_API_KEY env var or pass api_key explicitly
    ai = Genkit(plugins=[Mistral()], model='mistral/mistral-large-latest')

    response = await ai.generate(prompt='Hello, Mistral!')
    print(response.text)
    ```

Caveats:
    - Requires MISTRAL_API_KEY environment variable or api_key parameter
    - Model names are prefixed with 'mistral/' (e.g., 'mistral/mistral-large-latest')
    - Uses official Mistral Python SDK

See Also:
    - Mistral AI documentation: https://docs.mistral.ai/
    - Mistral API Reference: https://docs.mistral.ai/api/
    - Genkit documentation: https://genkit.dev/
"""

from .embeddings import SUPPORTED_EMBEDDING_MODELS, MistralEmbedConfig
from .model_info import SUPPORTED_MISTRAL_MODELS
from .models import MISTRAL_PLUGIN_NAME, mistral_name
from .plugin import Mistral

# Official Mistral API endpoint
DEFAULT_MISTRAL_API_URL = 'https://api.mistral.ai'

__all__ = [
    'DEFAULT_MISTRAL_API_URL',
    'MISTRAL_PLUGIN_NAME',
    'MistralEmbedConfig',
    'Mistral',
    'SUPPORTED_EMBEDDING_MODELS',
    'SUPPORTED_MISTRAL_MODELS',
    'mistral_name',
]
