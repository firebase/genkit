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

"""CF AI plugin for Genkit - Cloudflare Workers AI integration.

This plugin provides access to Cloudflare Workers AI models through the Genkit
framework. Cloudflare Workers AI runs AI models at the edge, close to users,
providing low-latency inference with global availability.

Documentation Links:
    - Cloudflare Workers AI: https://developers.cloudflare.com/workers-ai/
    - Model Catalog: https://developers.cloudflare.com/workers-ai/models/
    - REST API: https://developers.cloudflare.com/workers-ai/get-started/rest-api/

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Workers AI          │ AI models that run on Cloudflare's edge servers.   │
    │                     │ Like having AI helpers in data centers worldwide.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Account ID          │ Your unique Cloudflare identifier. Like your       │
    │                     │ customer number at a store.                        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ API Token           │ Your secret key to access the API. Like a password │
    │                     │ that proves you're allowed to use the service.     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Model ID            │ The specific AI model to use. Format is like       │
    │                     │ @cf/meta/llama-3.1-8b-instruct.                    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Edge Computing      │ Running code close to users geographically. Like   │
    │                     │ having mini-servers in every city instead of one.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Getting the response word-by-word as it's          │
    │                     │ generated, instead of waiting for all of it.       │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    User Request
         │
         ▼
    ┌───────────────────┐     ┌───────────────────┐
    │  Genkit Flow      │────▶│  CfAI Plugin      │
    │  (your app)       │     │  (cf-ai)          │
    └───────────────────┘     └─────────┬─────────┘
                                        │
                                        │ HTTPS with Bearer Token
                                        ▼
    ┌───────────────────────────────────────────────────────────────┐
    │               Cloudflare Workers AI (Edge)                     │
    ├───────────────────────────────────────────────────────────────┤
    │  @cf/meta/llama-*     │ Text Generation (chat, instruct)       │
    │  @cf/mistral/*        │ Fast inference, reasoning              │
    │  @cf/baai/bge-*       │ Text embeddings for search             │
    │  @cf/qwen/*           │ Multilingual models                    │
    └───────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────┐     ┌───────────────────┐
    │  JSON Response    │ or  │  SSE Stream       │
    │  (complete)       │     │  (token by token) │
    └───────────────────┘     └───────────────────┘

Plugin Architecture::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         CF AI Plugin (cf-ai)                             │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  __init__.py - Plugin Entry Point                                        │
    │  ├── CfAI - Plugin class (this module re-exports from plugin.py)         │
    │  ├── cf_name() - Helper to create qualified model names                  │
    │  ├── cf_model() - Convenience alias for cf_name                          │
    │  └── Pre-defined model references (llama_3_1_8b, bge_base_en, etc.)      │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  typing.py - Configuration Types                                         │
    │  ├── CfConfig - Base configuration for all models                        │
    │  ├── CfEmbedConfig - Embedding-specific options                          │
    │  └── Parameter constraints (temperature, top_k, etc.)                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  plugin.py - Plugin Implementation                                       │
    │  ├── CfAI(Plugin) - Registers models and embedders                       │
    │  ├── init() - Initializes httpx client with auth                         │
    │  ├── resolve() - Lazy-loads models on demand                             │
    │  └── list_actions() - Lists available models                             │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models/model.py - Model Implementation                                  │
    │  ├── CfModel - Handles text generation                                   │
    │  ├── _build_request() - Converts Genkit messages to CF format            │
    │  ├── generate() - Non-streaming generation                               │
    │  └── _generate_streaming() - SSE-based streaming                         │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models/model_info.py - Model Registry                                   │
    │  ├── SUPPORTED_MODELS - Dict of text generation models                   │
    │  ├── SUPPORTED_EMBEDDING_MODELS - Dict of embedding models               │
    │  └── get_model_info() - Lookup model capabilities                        │
    └─────────────────────────────────────────────────────────────────────────┘

Example Usage::

    from genkit import Genkit
    from genkit.plugins.cf_ai import CfAI, cf_model

    ai = Genkit(
        plugins=[CfAI()],
        model=cf_model('@cf/meta/llama-3.1-8b-instruct'),
    )

    # Simple generation
    response = await ai.generate(prompt='Tell me a joke.')
    print(response.text)

    # With streaming
    async for chunk in ai.generate_stream(prompt='Write a story.'):
        print(chunk.text, end='')

Authentication:
    The plugin requires two environment variables:

    - ``CLOUDFLARE_ACCOUNT_ID``: Your Cloudflare account ID
    - ``CLOUDFLARE_API_TOKEN``: API token with Workers AI permissions

    These can also be passed directly to the plugin constructor.

Implementation Notes & Edge Cases
---------------------------------

**Media URL Fetching (Cloudflare-Specific Requirement)**

Unlike other AI providers (Anthropic, OpenAI, Google GenAI) that accept media URLs
directly in their APIs, Cloudflare Workers AI **only accepts base64 data URIs** for
multimodal models like Llama 4 Scout. From the Cloudflare docs:

    "url string - image uri with data (e.g. data:image/jpeg;base64,/9j/...).
    HTTP URL will not be accepted"

The plugin automatically fetches images from URLs and converts them to base64::

    # User provides:
    MediaPart(media=Media(url='https://example.com/image.jpg'))

    # Plugin sends to Cloudflare:
    {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,...'}}

**User-Agent Header for External URLs**

Some servers (notably Wikipedia/Wikimedia) block requests without a proper
``User-Agent`` header, returning HTTP 403 Forbidden. The plugin includes::

    'User-Agent': 'Genkit/1.0 (https://github.com/firebase/genkit; genkit@google.com)'

**Tool Calling Format**

For models supporting function calling, Cloudflare expects tool calls as JSON
serialized in the assistant message's ``content`` field::

    # Assistant requesting a tool call:
    {'role': 'assistant', 'content': '{"name": "get_weather", "arguments": {...}}'}

    # Tool response:
    {'role': 'tool', 'name': 'get_weather', 'content': '{"temperature": "72°F"}'}

This differs from OpenAI's ``tool_calls`` array format.

**Tool Input Schema Wrapping**

Cloudflare requires tool parameters to be object schemas. Primitive schemas
(e.g., ``{'type': 'string'}``) are automatically wrapped::

    {'type': 'object', 'properties': {'input': {...}}, 'required': ['input']}

**Server-Sent Events (SSE) Streaming**

Streaming uses SSE format. Each event contains a JSON payload with the
generated text chunk::

    async for line in response.aiter_lines():
        if line.startswith('data: '):
            chunk = json.loads(line[6:])
            yield chunk['response']

**Model ID Format**

Model IDs use hierarchical format: ``@cf/<provider>/<model>``.
Example: ``@cf/meta/llama-3.1-8b-instruct``.

Trademark Notice:
    This is a community plugin and is not officially supported by Cloudflare.
    "Cloudflare", "Workers", "CF", and related marks are trademarks of
    Cloudflare, Inc.
"""

from genkit.plugins.cf_ai.models.model_info import (
    SUPPORTED_CF_MODELS as SUPPORTED_CF_MODELS,
    SUPPORTED_EMBEDDING_MODELS as SUPPORTED_EMBEDDING_MODELS,
)
from genkit.plugins.cf_ai.plugin import (
    CF_AI_PLUGIN_NAME as CF_AI_PLUGIN_NAME,
    CfAI as CfAI,
    cf_model as cf_model,
    cf_name as cf_name,
)
from genkit.plugins.cf_ai.typing import CfConfig as CfConfig

# Pre-defined model references for convenience
# Text Generation Models
llama_3_3_70b = cf_name('@cf/meta/llama-3.3-70b-instruct-fp8-fast')
llama_3_1_8b = cf_name('@cf/meta/llama-3.1-8b-instruct')
llama_3_1_8b_fast = cf_name('@cf/meta/llama-3.1-8b-instruct-fast')
llama_4_scout = cf_name('@cf/meta/llama-4-scout-17b-16e-instruct')
mistral_7b = cf_name('@cf/mistral/mistral-7b-instruct-v0.2')
qwen_14b = cf_name('@cf/qwen/qwen1.5-14b-chat-awq')

# Embedding Models
bge_base_en = cf_name('@cf/baai/bge-base-en-v1.5')
bge_large_en = cf_name('@cf/baai/bge-large-en-v1.5')
bge_small_en = cf_name('@cf/baai/bge-small-en-v1.5')

__all__ = [
    # Plugin
    'CfAI',
    'CF_AI_PLUGIN_NAME',
    # Helpers
    'cf_name',
    'cf_model',
    # Config
    'CfConfig',
    # Model registries
    'SUPPORTED_CF_MODELS',
    'SUPPORTED_EMBEDDING_MODELS',
    # Pre-defined model references
    'llama_3_3_70b',
    'llama_3_1_8b',
    'llama_3_1_8b_fast',
    'llama_4_scout',
    'mistral_7b',
    'qwen_14b',
    'bge_base_en',
    'bge_large_en',
    'bge_small_en',
]
