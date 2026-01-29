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


"""OpenAI OpenAI API Compatible Plugin for Genkit."""

from typing import Any

from openai import OpenAI as OpenAIClient
from openai.types import Model

from genkit.ai import Plugin
from genkit.blocks.embedding import EmbedderOptions, EmbedderSupports, embedder_action_metadata
from genkit.blocks.model import model_action_metadata
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
from genkit.core.typing import GenerationCommonConfig
from genkit.plugins.compat_oai.models import (
    SUPPORTED_EMBEDDING_MODELS,
    SUPPORTED_OPENAI_COMPAT_MODELS,
    SUPPORTED_OPENAI_MODELS,
    OpenAIModel,
    OpenAIModelHandler,
)
from genkit.plugins.compat_oai.models.model_info import get_default_openai_model_info
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.types import Embedding, EmbedRequest, EmbedResponse


def open_ai_name(name: str) -> str:
    """Create an OpenAI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified OpenAI action name.
    """
    return f'openai/{name}'


def default_openai_metadata(name: str) -> dict[str, Any]:
    return {
        'model': {'label': f'OpenAI - {name}', 'supports': {'multiturn': True}},
    }


class OpenAI(Plugin):
    """A plugin for integrating OpenAI compatible models with the Genkit framework.

    This class registers OpenAI model handlers within a registry, allowing
    interaction with supported OpenAI models.
    """

    name = 'openai'

    def __init__(self, **openai_params: Any) -> None:  # noqa: ANN401
        """Initializes the OpenAI plugin with the specified parameters.

        Args:
            openai_params: Additional parameters that will be passed to the OpenAI client constructor.
                           These parameters may include API keys, timeouts, organization IDs, and
                           other configuration settings required by OpenAI's API.
        """
        self._openai_params = openai_params
        self._openai_client = OpenAIClient(**openai_params)

    async def init(self) -> list[Action]:
        """Initialize plugin.

        Returns:
            Actions for built-in OpenAI models and embedders.
        """
        actions = []

        # Add known models
        for name in SUPPORTED_OPENAI_MODELS.keys():
            actions.append(self._create_model_action(open_ai_name(name)))

        # Add known embedders
        for name in SUPPORTED_EMBEDDING_MODELS.keys():
            actions.append(self._create_embedder_action(open_ai_name(name)))

        return actions

    def get_model_info(self, name: str) -> dict[str, Any] | None:
        """Retrieves metadata and supported features for the specified model.

        This method looks up the model's information from a predefined list
        of supported OpenAI-compatible models or provides default information.

        Returns:
            A dictionary containing the model's 'name' and 'supports' features,
            or None if no information can be found (though typically, a default
            is provided). The 'supports' key contains a dictionary representing
            the model's capabilities (e.g., tools, streaming).
        """
        if model_supported := SUPPORTED_OPENAI_MODELS.get(name):
            supports = model_supported.supports.model_dump(exclude_none=True) if model_supported.supports else {}
            return {
                'label': model_supported.label,
                'supports': supports,
            }

        model_info = SUPPORTED_OPENAI_COMPAT_MODELS.get(name, get_default_openai_model_info(name))
        supports = model_info.supports.model_dump(exclude_none=True) if model_info.supports else {}
        return {
            'label': model_info.label,
            'supports': supports,
        }

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action by creating and returning an Action object.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action to resolve.

        Returns:
            Action object if found, None otherwise.
        """
        if action_type == ActionKind.MODEL:
            return self._create_model_action(name)
        elif action_type == ActionKind.EMBEDDER:
            return self._create_embedder_action(name)

        return None

    def _create_model_action(self, name: str) -> Action:
        """Create an Action object for an OpenAI model.

        Args:
            name: The namespaced name of the model.

        Returns:
            Action object for the model.
        """
        # Extract local name (remove plugin prefix)
        clean_name = name.replace('openai/', '') if name.startswith('openai/') else name

        # Create the model handler
        openai_model = OpenAIModelHandler(OpenAIModel(clean_name, self._openai_client))
        model_info = self.get_model_info(clean_name) or {}

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=openai_model.generate,
            metadata={
                'model': {
                    **model_info,
                    'customOptions': to_json_schema(OpenAIConfig),
                },
            },
        )

    def _create_embedder_action(self, name: str) -> Action:
        """Create an Action object for an OpenAI embedder.

        Args:
            name: The namespaced name of the embedder.

        Returns:
            Action object for the embedder.
        """
        # Extract local name (remove plugin prefix)
        clean_name = name.replace('openai/', '') if name.startswith('openai/') else name

        # Get embedder info from known models or use default
        embedder_info = SUPPORTED_EMBEDDING_MODELS.get(
            clean_name,
            {
                'label': f'OpenAI Embedding - {clean_name}',
                'dimensions': 1536,
                'supports': {'input': ['text']},
            },
        )

        async def embed_fn(request: EmbedRequest) -> EmbedResponse:
            """Embedder function that calls OpenAI embeddings API."""
            # Extract text from document content
            texts = []
            for doc in request.input:
                doc_text = ''.join(  # type: ignore[arg-type]
                    part.root.text for part in doc.content if hasattr(part.root, 'text') and part.root.text
                )
                texts.append(doc_text)

            # Get optional parameters with proper types
            dimensions = None
            encoding_format = None
            if request.options:
                if dim_val := request.options.get('dimensions'):
                    dimensions = int(dim_val)
                if enc_val := request.options.get('encodingFormat'):
                    encoding_format = str(enc_val) if enc_val in ('float', 'base64') else None

            # Create embeddings for each document
            response = self._openai_client.embeddings.create(
                model=clean_name,
                input=texts,
                dimensions=dimensions,  # type: ignore[arg-type]
                encoding_format=encoding_format,  # type: ignore[arg-type]
            )

            # Convert OpenAI response to Genkit format
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
        """Generate a list of available actions or models.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects, each with the following attributes:
                - name (str): The name of the action or model.
                - kind (ActionKind): The type or category of the action.
                - info (dict): The metadata dictionary describing the model configuration and properties.
                - config_schema (type): The schema class used for validating the model's configuration.
        """
        actions = []
        models_ = self._openai_client.models.list()
        models: list[Model] = models_.data
        # Print each model
        for model in models:
            _name = model.id
            if 'embed' in _name:
                # Default embedder metadata for OpenAI embedding models
                actions.append(
                    embedder_action_metadata(
                        name=open_ai_name(_name),
                        options=EmbedderOptions(
                            label=f'OpenAI Embedding - {_name}',
                            supports=EmbedderSupports(input=['text']),
                        ),
                    )
                )
            else:
                actions.append(
                    model_action_metadata(
                        name=open_ai_name(_name),
                        config_schema=GenerationCommonConfig,
                        info={
                            'label': f'OpenAI - {_name}',
                            'multiturn': True,
                            'system_role': True,
                            'tools': False,
                        },
                    )
                )
        return actions


def openai_model(name: str) -> str:
    """Returns a string representing the OpenAI model name to use with Genkit.

    Args:
        name: The name of the OpenAI model to use.

    Returns:
        A string representing the OpenAI model name to use with Genkit.
    """
    return f'openai/{name}'


__all__ = ['OpenAI', 'openai_model']
