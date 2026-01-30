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
Microsoft Foundry (formerly Azure AI Foundry) provides access to 11,000+ AI models
from multiple providers.

Documentation:
- Microsoft Foundry Portal: https://ai.azure.com/
- Model Catalog: https://ai.azure.com/catalog/models
- SDK Overview: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview
- Models: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models

The plugin supports:
- Chat completion models (GPT-4o, GPT-5, o-series, Claude, DeepSeek, Grok, Llama, Mistral)
- Text embedding models (text-embedding-3-small, text-embedding-3-large, embed-v-4-0)
- Tool/function calling
- Streaming responses
- Multimodal inputs (images)
- JSON output mode

Authentication
==============
The plugin supports two authentication methods:

1. **API Key** (simpler):
   Set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` environment variables,
   or pass them directly to the plugin constructor.

2. **Azure AD / Managed Identity** (recommended for production):
   Use `azure_ad_token_provider` with Azure Identity credentials.

Example::

    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, 'https://cognitiveservices.azure.com/.default')

    ai = Genkit(
        plugins=[
            MSFoundry(
                azure_ad_token_provider=token_provider,
                endpoint='https://your-resource.openai.azure.com/',
                api_version='2024-10-21',
            )
        ]
    )

Example Usage
=============
```python
from genkit import Genkit
from genkit.plugins.msfoundry import MSFoundry, msfoundry_model

ai = Genkit(
    plugins=[
        MSFoundry(
            api_key='your-api-key',
            endpoint='https://your-resource.openai.azure.com/',
            api_version='2024-10-21',
        )
    ],
    model=msfoundry_model('gpt-4o'),
)

response = await ai.generate(prompt='Tell me a joke.')
print(response.text)
```

See Also:
    - Microsoft Foundry Documentation: https://learn.microsoft.com/en-us/azure/ai-foundry/
    - Model Catalog: https://ai.azure.com/catalog/models
"""

import os
from collections.abc import Callable
from typing import Any

from openai import AsyncAzureOpenAI

from genkit.ai import Plugin
from genkit.blocks.embedding import EmbedderOptions, EmbedderSupports, embedder_action_metadata
from genkit.blocks.model import model_action_metadata
from genkit.core.action import Action, ActionMetadata
from genkit.core.registry import ActionKind
from genkit.plugins.msfoundry.models.model import MSFoundryModel
from genkit.plugins.msfoundry.models.model_info import (
    SUPPORTED_EMBEDDING_MODELS,
    SUPPORTED_MSFOUNDRY_MODELS,
    get_model_info,
)
from genkit.plugins.msfoundry.typing import MSFoundryConfig
from genkit.types import Embedding, EmbedRequest, EmbedResponse

# Plugin name
MSFOUNDRY_PLUGIN_NAME = 'msfoundry'


def msfoundry_name(name: str) -> str:
    """Get fully qualified Microsoft Foundry model name.

    Args:
        name: The base model name (e.g., 'gpt-4o', 'DeepSeek-V3.2').

    Returns:
        Fully qualified model name (e.g., 'msfoundry/gpt-4o').
    """
    return f'{MSFOUNDRY_PLUGIN_NAME}/{name}'


class MSFoundry(Plugin):
    """Microsoft Foundry plugin for Genkit.

    This plugin provides access to Microsoft Foundry models including:
    - OpenAI: GPT-4o, GPT-4, GPT-5, o-series reasoning models
    - Anthropic: Claude Opus, Sonnet, Haiku
    - DeepSeek: V3.2, R1 reasoning models
    - xAI: Grok 3, Grok 4
    - Meta: Llama 4 Maverick
    - Mistral: Mistral Large 3
    - Cohere: Command, Embed, Rerank
    - And 11,000+ more models in the catalog

    See: https://ai.azure.com/catalog/models

    Attributes:
        name: Plugin name ('msfoundry').
    """

    name = MSFOUNDRY_PLUGIN_NAME

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
        azure_ad_token_provider: Callable[[], str] | None = None,
        discover_models: bool = False,
        **openai_params: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the Microsoft Foundry plugin.

        Args:
            api_key: Azure OpenAI API key. Falls back to AZURE_OPENAI_API_KEY env var.
            endpoint: Azure OpenAI endpoint URL. Falls back to AZURE_OPENAI_ENDPOINT env var.
            deployment: Default deployment name for models.
            api_version: API version (e.g., '2024-10-21'). Falls back to OPENAI_API_VERSION env var.
            azure_ad_token_provider: Token provider for Azure AD authentication.
                Use with `azure.identity.get_bearer_token_provider()` for managed identity.
            discover_models: If True, dynamically discover models from the Azure API.
                This queries the /openai/models endpoint to list available models.
                Default is False (uses the predefined model list).
            **openai_params: Additional parameters passed to AsyncAzureOpenAI client.

        Example:
            # Using API key:
            plugin = MSFoundry(
                api_key="your-key",
                endpoint="https://your-resource.openai.azure.com/",
                api_version="2024-10-21",
            )

            # Using Azure AD:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            plugin = MSFoundry(
                azure_ad_token_provider=token_provider,
                endpoint="https://your-resource.openai.azure.com/",
            )

            # With dynamic model discovery:
            plugin = MSFoundry(
                api_key="your-key",
                endpoint="https://your-resource.openai.azure.com/",
                discover_models=True,  # Fetches models from API
            )
        """
        # Resolve configuration from environment variables
        api_key = api_key or os.environ.get('AZURE_OPENAI_API_KEY')
        resolved_endpoint = endpoint or os.environ.get('AZURE_OPENAI_ENDPOINT')
        api_version = api_version or os.environ.get('OPENAI_API_VERSION', '2024-10-21')

        if not resolved_endpoint:
            raise ValueError(
                'Azure OpenAI endpoint is required. '
                'Set AZURE_OPENAI_ENDPOINT environment variable or pass endpoint parameter.'
            )

        self._deployment = deployment
        self._discover_models = discover_models
        self._discovered_models: dict[str, dict[str, Any]] | None = None
        self._openai_client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=resolved_endpoint,
            api_version=api_version,
            azure_ad_token_provider=azure_ad_token_provider,
            **openai_params,
        )

    async def _discover_models_from_api(self) -> dict[str, dict[str, Any]]:
        """Discover available models from the Azure OpenAI API.

        Uses the /openai/models endpoint to list all models accessible
        by the Azure OpenAI resource, including base models and fine-tuned models.

        See: https://learn.microsoft.com/en-us/rest/api/azureopenai/models/list

        Returns:
            Dictionary mapping model IDs to their capabilities and metadata.
        """
        if self._discovered_models is not None:
            return self._discovered_models

        discovered: dict[str, dict[str, Any]] = {}
        try:
            models_response = await self._openai_client.models.list()
            for model in models_response.data:
                model_id = model.id
                # Extract capabilities from the model response
                capabilities = getattr(model, 'capabilities', None)
                discovered[model_id] = {
                    'id': model_id,
                    'capabilities': {
                        'chat_completion': getattr(capabilities, 'chat_completion', False) if capabilities else True,
                        'completion': getattr(capabilities, 'completion', False) if capabilities else False,
                        'embeddings': getattr(capabilities, 'embeddings', False) if capabilities else False,
                        'fine_tune': getattr(capabilities, 'fine_tune', False) if capabilities else False,
                        'inference': getattr(capabilities, 'inference', True) if capabilities else True,
                    },
                    'lifecycle_status': getattr(model, 'lifecycle_status', 'generally-available'),
                }
            self._discovered_models = discovered
        except Exception:
            # If discovery fails, fall back to predefined models
            self._discovered_models = {}

        return self._discovered_models

    async def init(self) -> list[Action]:
        """Initialize plugin and register supported models.

        If discover_models is True, fetches the list of available models
        from the Azure OpenAI API. Otherwise, uses the predefined model list.

        Returns:
            List of Action objects for supported models and embedders.
        """
        actions: list[Action] = []

        if self._discover_models:
            # Discover models dynamically from the API
            discovered = await self._discover_models_from_api()
            for model_id, info in discovered.items():
                caps = info.get('capabilities', {})
                if caps.get('chat_completion') or caps.get('completion'):
                    actions.append(self._create_model_action(msfoundry_name(model_id)))
                if caps.get('embeddings'):
                    actions.append(self._create_embedder_action(msfoundry_name(model_id)))
        else:
            # Register all supported models from predefined list
            for name in SUPPORTED_MSFOUNDRY_MODELS:
                actions.append(self._create_model_action(msfoundry_name(name)))

            # Register all supported embedding models
            for name in SUPPORTED_EMBEDDING_MODELS:
                actions.append(self._create_embedder_action(msfoundry_name(name)))

        return actions

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action by type and name.

        This enables lazy loading of models not pre-registered during init().

        Args:
            action_type: The kind of action to resolve (MODEL or EMBEDDER).
            name: The namespaced name of the action.

        Returns:
            Action object if resolvable, None otherwise.
        """
        if action_type == ActionKind.MODEL:
            return self._create_model_action(name)
        elif action_type == ActionKind.EMBEDDER:
            return self._create_embedder_action(name)
        return None

    def _create_model_action(self, name: str) -> Action:
        """Create an Action object for a chat completion model.

        Args:
            name: The namespaced model name (e.g., 'msfoundry/gpt-4o').

        Returns:
            Action object for the model.
        """
        # Extract local name (remove plugin prefix)
        prefix = f'{MSFOUNDRY_PLUGIN_NAME}/'
        clean_name = name[len(prefix) :] if name.startswith(prefix) else name

        model = MSFoundryModel(
            model_name=clean_name,
            client=self._openai_client,
            deployment=self._deployment,
        )
        model_info = get_model_info(clean_name)

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=model.generate,
            metadata=model_action_metadata(
                name=name,
                info=model_info.supports.model_dump() if model_info.supports else {},
                config_schema=MSFoundryConfig,
            ).metadata,
        )

    def _create_embedder_action(self, name: str) -> Action:
        """Create an Action object for an embedding model.

        Args:
            name: The namespaced embedder name.

        Returns:
            Action object for the embedder.
        """
        prefix = f'{MSFOUNDRY_PLUGIN_NAME}/'
        clean_name = name[len(prefix) :] if name.startswith(prefix) else name

        # Get embedder info
        embedder_info = SUPPORTED_EMBEDDING_MODELS.get(
            clean_name,
            {
                'label': f'Microsoft Foundry - {clean_name}',
                'dimensions': 1536,
                'supports': {'input': ['text']},
            },
        )

        async def embed_fn(request: EmbedRequest) -> EmbedResponse:
            """Generate embeddings using Azure OpenAI."""
            # Extract text from document content
            texts: list[str] = []
            for doc in request.input:
                text_parts: list[str] = []
                for part in doc.content:
                    if hasattr(part.root, 'text') and part.root.text:
                        text_parts.append(str(part.root.text))
                doc_text = ''.join(text_parts)
                texts.append(doc_text)

            # Get optional parameters from request
            dimensions: int | None = None
            encoding_format: str | None = None
            if request.options:
                if dim_val := request.options.get('dimensions'):
                    dimensions = int(dim_val)
                if enc_val := request.options.get('encodingFormat'):
                    encoding_format = str(enc_val) if enc_val in ('float', 'base64') else None

            # Build API call kwargs - only include non-None optional params
            api_kwargs: dict[str, Any] = {
                'model': clean_name,
                'input': texts,
            }
            if dimensions is not None:
                api_kwargs['dimensions'] = dimensions
            if encoding_format is not None:
                api_kwargs['encoding_format'] = encoding_format

            # Call Azure OpenAI embeddings API
            response = await self._openai_client.embeddings.create(**api_kwargs)

            # Convert to Genkit format
            embeddings = [Embedding(embedding=item.embedding) for item in response.data]
            return EmbedResponse(embeddings=embeddings)

        return Action(
            kind=ActionKind.EMBEDDER,
            name=name,
            fn=embed_fn,
            metadata=embedder_action_metadata(
                name=name,
                options=EmbedderOptions(
                    label=embedder_info['label'],
                    supports=EmbedderSupports(input=embedder_info['supports']['input']),
                    dimensions=embedder_info.get('dimensions'),
                ),
            ).metadata,
        )

    async def list_actions(self) -> list[ActionMetadata]:
        """List all available models and embedders.

        If discover_models is True, includes dynamically discovered models
        from the Azure OpenAI API alongside the predefined models.

        Returns:
            List of ActionMetadata for all supported models and embedders.
        """
        actions: list[ActionMetadata] = []

        if self._discover_models:
            # Include dynamically discovered models
            discovered = await self._discover_models_from_api()
            for model_id, info in discovered.items():
                caps = info.get('capabilities', {})
                model_info = get_model_info(model_id)

                if caps.get('chat_completion') or caps.get('completion'):
                    actions.append(
                        model_action_metadata(
                            name=msfoundry_name(model_id),
                            info=model_info.supports.model_dump() if model_info.supports else {},
                            config_schema=MSFoundryConfig,
                        )
                    )
                if caps.get('embeddings'):
                    embed_info = SUPPORTED_EMBEDDING_MODELS.get(
                        model_id,
                        {
                            'label': f'Microsoft Foundry - {model_id}',
                            'dimensions': 1536,
                            'supports': {'input': ['text']},
                        },
                    )
                    actions.append(
                        embedder_action_metadata(
                            name=msfoundry_name(model_id),
                            options=EmbedderOptions(
                                label=embed_info['label'],
                                supports=EmbedderSupports(input=embed_info['supports']['input']),
                                dimensions=embed_info.get('dimensions'),
                            ),
                        )
                    )
        else:
            # Add model metadata from predefined list
            for model_name, model_info in SUPPORTED_MSFOUNDRY_MODELS.items():
                actions.append(
                    model_action_metadata(
                        name=msfoundry_name(model_name),
                        info=model_info.supports.model_dump() if model_info.supports else {},
                        config_schema=MSFoundryConfig,
                    )
                )

            # Add embedder metadata from predefined list
            for embed_name, embed_info in SUPPORTED_EMBEDDING_MODELS.items():
                actions.append(
                    embedder_action_metadata(
                        name=msfoundry_name(embed_name),
                        options=EmbedderOptions(
                            label=embed_info['label'],
                            supports=EmbedderSupports(input=embed_info['supports']['input']),
                            dimensions=embed_info.get('dimensions'),
                        ),
                    )
                )

        return actions


def msfoundry_model(name: str) -> str:
    """Get fully qualified Microsoft Foundry model name.

    Convenience function for specifying models. Can be used with any model
    from the catalog (11,000+ models).

    See: https://ai.azure.com/catalog/models

    Args:
        name: The base model name (e.g., 'gpt-4o', 'DeepSeek-V3.2', 'claude-opus-4-5').

    Returns:
        Fully qualified model name (e.g., 'msfoundry/gpt-4o').

    Example:
        ai = Genkit(
            plugins=[MSFoundry(...)],
            model=msfoundry_model("gpt-4o"),
        )

        # Or with other providers:
        response = await ai.generate(
            model=msfoundry_model("DeepSeek-V3.2"),
            prompt="Explain quantum computing.",
        )
    """
    return msfoundry_name(name)


# Pre-defined model references for convenience
gpt4o = msfoundry_name('gpt-4o')
gpt4o_mini = msfoundry_name('gpt-4o-mini')
gpt4 = msfoundry_name('gpt-4')
gpt35_turbo = msfoundry_name('gpt-3.5-turbo')
