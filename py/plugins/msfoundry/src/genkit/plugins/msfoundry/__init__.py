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

"""Microsoft Foundry plugin for Genkit.

This plugin provides access to Microsoft Foundry models through the Genkit framework.
Microsoft Foundry is Microsoft's unified AI platform (formerly Azure AI Foundry) that
provides access to 11,000+ AI models from multiple providers including:

- **OpenAI**: GPT-4o, GPT-5, o-series reasoning models
- **Anthropic**: Claude Opus, Sonnet, Haiku
- **DeepSeek**: V3.2, R1 reasoning models
- **xAI**: Grok 3, Grok 4
- **Meta**: Llama 4 Maverick
- **Mistral**: Mistral Large 3
- **Cohere**: Command, Embed, Rerank
- **And many more...**

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Microsoft Foundry   │ Microsoft's AI supermarket. One place to access   │
    │                     │ models from OpenAI, Anthropic, Meta, and more.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Azure               │ Microsoft's cloud platform. Where the models      │
    │                     │ actually run and your data stays secure.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ GPT-4o              │ OpenAI's multimodal model. Can see images,        │
    │                     │ hear audio, and chat - all in one model.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ o-series (o1, o3)   │ OpenAI's reasoning models. Think longer and       │
    │                     │ harder on complex problems before answering.      │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Endpoint            │ The web address where your AI models live.        │
    │                     │ Like your-resource.openai.azure.com.              │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ API Version         │ Which version of the API to use. Different        │
    │                     │ versions have different features.                 │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Deployment          │ A specific instance of a model you've set up.     │
    │                     │ Like having your own copy of GPT-4o.              │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                HOW MICROSOFT FOUNDRY PROCESSES YOUR REQUEST             │
    │                                                                         │
    │    Your Code                                                            │
    │    ai.generate(prompt="Analyze this data...")                           │
    │         │                                                               │
    │         │  (1) Request goes to MSFoundry plugin                         │
    │         ▼                                                               │
    │    ┌─────────────────┐                                                  │
    │    │  MSFoundry      │   Adds API key, endpoint, version                │
    │    │  Plugin         │   Selects provider-specific config               │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (2) Azure OpenAI-style request                           │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  FoundryModel   │   Converts Genkit format to Azure format         │
    │    │                 │   Handles streaming, tools, etc.                 │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (3) HTTPS to your-resource.openai.azure.com              │
    │             ▼                                                           │
    │    ════════════════════════════════════════════════════                 │
    │             │  Internet                                                 │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Azure AI       │   Routes to the right model                      │
    │    │  Foundry        │   (GPT-4o, Claude, Llama, etc.)                  │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (4) Response from chosen model                           │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Your App       │   response.text = "Here's my analysis..."        │
    │    └─────────────────┘                                                  │
    └─────────────────────────────────────────────────────────────────────────┘

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      Microsoft Foundry Plugin                           │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  ├── MSFoundry - Plugin class                                           │
    │  ├── Model References (gpt4o, gpt4o_mini, o1, o3_mini, etc.)            │
    │  ├── Helper Functions (msfoundry_name, msfoundry_model)                 │
    │  └── get_config_schema_for_model() - Dynamic config selection           │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  typing.py - Type-Safe Configuration Classes                            │
    │  ├── MSFoundryConfig (base), OpenAIConfig                               │
    │  ├── AnthropicConfig, LlamaConfig, MistralConfig, ...                   │
    │  └── Model-specific enums (ReasoningEffort, CohereSafetyMode, ...)      │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  plugin.py - Plugin Implementation                                      │
    │  ├── MSFoundry class (registers models/embedders)                       │
    │  └── Azure OpenAI client initialization                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models/model.py - Model Implementation                                 │
    │  ├── FoundryModel (chat completions API)                                │
    │  ├── Request/response conversion                                        │
    │  └── Streaming support                                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  models/model_info.py - Model Registry                                  │
    │  ├── SUPPORTED_MODELS (30+ model families)                              │
    │  └── SUPPORTED_EMBEDDING_MODELS                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Documentation Links:
    - Microsoft Foundry Portal: https://ai.azure.com/
    - Model Catalog: https://ai.azure.com/catalog/models
    - SDK Overview: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview
    - Models Documentation: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models
    - Deployment Types: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types
    - Python SDK: https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.msfoundry import MSFoundry, gpt4o

    ai = Genkit(
        plugins=[
            MSFoundry(
                api_key='your-api-key',
                endpoint='https://your-resource.openai.azure.com/',
                api_version='2024-10-21',
            )
        ],
        model=gpt4o,
    )

    response = await ai.generate(prompt='Tell me a joke.')
    print(response.text)
    ```

Note:
    This is a community plugin and is not officially endorsed by Microsoft.
    "Microsoft", "Azure", and "Microsoft Foundry" are trademarks of Microsoft Corporation.
"""

from .plugin import (
    MSFOUNDRY_PLUGIN_NAME,
    MSFoundry,
    get_config_schema_for_model,
    gpt4,
    gpt4o,
    gpt4o_mini,
    gpt35_turbo,
    msfoundry_model,
    msfoundry_name,
    o1,
    o1_mini,
    o3_mini,
)
from .typing import (
    # Model-Specific Configs (Top 30)
    AI21JambaConfig,
    AnthropicConfig,
    # Enums
    AnthropicServiceTier,
    ArcticConfig,
    BaichuanConfig,
    CohereConfig,
    CohereSafetyMode,
    CohereToolChoice,
    DbrxConfig,
    DeepSeekConfig,
    DeepSeekThinkingType,
    FalconConfig,
    GemmaConfig,
    # Mixins
    GenkitCommonConfigMixin,
    GlmConfig,
    GraniteConfig,
    GrokConfig,
    InflectionConfig,
    InternLMConfig,
    JaisConfig,
    LlamaConfig,
    MiniCPMConfig,
    MistralConfig,
    MptConfig,
    # Base/OpenAI Configs
    MSFoundryConfig,
    NvidiaConfig,
    OpenAIConfig,
    PhiConfig,
    QwenConfig,
    ReasoningEffort,
    RekaConfig,
    StableLMConfig,
    StarCoderConfig,
    TextEmbeddingConfig,
    TimeSeriesConfig,
    Verbosity,
    VisualDetailLevel,
    WriterConfig,
    XGenConfig,
    YiConfig,
)

__all__ = [
    # Plugin
    'MSFoundry',
    'MSFOUNDRY_PLUGIN_NAME',
    # Helper functions
    'get_config_schema_for_model',
    'msfoundry_model',
    'msfoundry_name',
    # Pre-defined model references
    'gpt4o',
    'gpt4o_mini',
    'gpt4',
    'gpt35_turbo',
    'o1',
    'o1_mini',
    'o3_mini',
    # Enums
    'AnthropicServiceTier',
    'CohereSafetyMode',
    'CohereToolChoice',
    'DeepSeekThinkingType',
    'ReasoningEffort',
    'Verbosity',
    'VisualDetailLevel',
    # Mixins
    'GenkitCommonConfigMixin',
    # Base/OpenAI Configs
    'MSFoundryConfig',
    'OpenAIConfig',
    # Model-Specific Configs (Top 30)
    'AI21JambaConfig',
    'AnthropicConfig',
    'ArcticConfig',
    'BaichuanConfig',
    'CohereConfig',
    'DbrxConfig',
    'DeepSeekConfig',
    'FalconConfig',
    'GemmaConfig',
    'GlmConfig',
    'GraniteConfig',
    'GrokConfig',
    'InflectionConfig',
    'InternLMConfig',
    'JaisConfig',
    'LlamaConfig',
    'MiniCPMConfig',
    'MistralConfig',
    'MptConfig',
    'NvidiaConfig',
    'PhiConfig',
    'QwenConfig',
    'RekaConfig',
    'StableLMConfig',
    'StarCoderConfig',
    'TextEmbeddingConfig',
    'TimeSeriesConfig',
    'WriterConfig',
    'XGenConfig',
    'YiConfig',
]
