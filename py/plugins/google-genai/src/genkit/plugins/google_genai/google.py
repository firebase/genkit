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

import os
from functools import cached_property

from google import genai
from google.auth.credentials import Credentials
from google.genai.client import DebugConfig
from google.genai.types import HttpOptions, HttpOptionsDict

import genkit.plugins.google_genai.constants as const
from genkit.ai import GENKIT_CLIENT_HEADER, Plugin
from genkit.blocks.embedding import EmbedderOptions, EmbedderSupports, embedder, embedder_action_metadata
from genkit.blocks.model import model, model_action_metadata
from genkit.core.action import Action, ActionMetadata
from genkit.core.registry import ActionKind
from genkit.plugins.google_genai.models.embedder import (
    Embedder,
    GeminiEmbeddingModels,
    VertexEmbeddingModels,
    default_embedder_info,
)
from genkit.plugins.google_genai.models.gemini import (
    SUPPORTED_MODELS,
    GeminiModel,
    GoogleAIGeminiVersion,
    VertexAIGeminiVersion,
    google_model_info,
)
from genkit.plugins.google_genai.models.imagen import (
    SUPPORTED_MODELS as IMAGE_SUPPORTED_MODELS,
    ImagenModel,
    ImagenVersion,
    vertexai_image_model_info,
)

GOOGLEAI_PLUGIN_NAME = 'googleai'
VERTEXAI_PLUGIN_NAME = 'vertexai'


def googleai_name(name: str) -> str:
    """Create a GoogleAI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Google AI action name.
    """
    return f'{GOOGLEAI_PLUGIN_NAME}/{name}'


def vertexai_name(name: str) -> str:
    """Create a VertexAI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Google AI action name.
    """
    return f'{VERTEXAI_PLUGIN_NAME}/{name}'


class GoogleAI(Plugin):
    """GoogleAI plugin for Genkit.

    Attributes:
        name (str): The name of the plugin, typically `GOOGLEAI_PLUGIN_NAME`.
        _vertexai (bool): Internal flag indicating if Vertex AI is being used.
            Defaults to False.
    """

    name = GOOGLEAI_PLUGIN_NAME
    _vertexai = False

    def __init__(
        self,
        api_key: str | None = None,
        credentials: Credentials | None = None,
        debug_config: DebugConfig | None = None,
        http_options: HttpOptions | HttpOptionsDict | None = None,
    ) -> None:
        """Initializes the GoogleAI plugin.

        Args:
            api_key: The API key for authenticating with the Google AI service.
                If not provided, it defaults to reading from the 'GEMINI_API_KEY'
                environment variable.
            credentials: Google Cloud credentials for authentication.
                Defaults to None, in which case the client uses default authentication
                mechanisms (e.g., application default credentials or API key).
            debug_config: Configuration for debugging the client. Defaults to None.
            http_options: HTTP options for configuring the client's network requests.
                Can be an instance of HttpOptions or a dictionary. Defaults to None.

        Raises:
            ValueError: If `api_key` is not provided and the 'GEMINI_API_KEY'
                environment variable is not set.
        """
        api_key = api_key if api_key else os.getenv('GEMINI_API_KEY')
        if not api_key and credentials is None:
            raise ValueError(
                'Gemini api key should be passed in plugin params or as a GEMINI_API_KEY environment variable'
            )

        self._client = genai.client.Client(
            vertexai=self._vertexai,
            api_key=api_key,
            credentials=credentials,
            debug_config=debug_config,
            http_options=_inject_attribution_headers(http_options),
        )

    async def init(self) -> list[Action]:
        actions: list[Action] = []

        for version in GoogleAIGeminiVersion:
            gemini_model = GeminiModel(version, self._client)
            actions.append(
                model(
                    name=str(version),
                    fn=gemini_model.generate,
                    metadata=gemini_model.metadata,
                    # config_schema=GeminiConfigSchema,
                )
            )

        for version in GeminiEmbeddingModels:
            embedder_impl = Embedder(version=version, client=self._client)
            embedder_info = default_embedder_info(version)
            actions.append(
                embedder(
                    name=str(version),
                    fn=embedder_impl.generate,
                    options=EmbedderOptions(
                        label=embedder_info.get('label'),
                        dimensions=embedder_info.get('dimensions'),
                        supports=EmbedderSupports(**embedder_info['supports'])
                        if embedder_info.get('supports')
                        else None,
                    ),
                )
            )

        return actions

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        if action_type == ActionKind.MODEL:
            model_ref = google_model_info(name)
            SUPPORTED_MODELS[name] = model_ref
            gemini_model = GeminiModel(name, self._client)
            return model(
                name=name,
                fn=gemini_model.generate,
                metadata=gemini_model.metadata,
            )
        if action_type == ActionKind.EMBEDDER:
            embedder_impl = Embedder(version=name, client=self._client)
            embedder_info = default_embedder_info(name)
            return embedder(
                name=name,
                fn=embedder_impl.generate,
                options=EmbedderOptions(
                    label=embedder_info.get('label'),
                    dimensions=embedder_info.get('dimensions'),
                    supports=EmbedderSupports(**embedder_info['supports']) if embedder_info.get('supports') else None,
                ),
            )
        return None

    @cached_property
    def _list_actions_cache(self) -> list[ActionMetadata]:
        """Generate a list of available actions or models.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects, each with the following attributes:
                - name (str): The name of the action or model.
                - kind (ActionKind): The type or category of the action.
                - info (dict): The metadata dictionary describing the model configuration and properties.
                - config_schema (type): The schema class used for validating the model's configuration.
        """
        actions_list = list()
        for m in self._client.models.list():
            name = m.name.replace('models/', '')
            if 'generateContent' in m.supported_actions:
                actions_list.append(
                    model_action_metadata(
                        name=googleai_name(name),
                        info=google_model_info(name).model_dump(),
                    ),
                )

            if 'embedContent' in m.supported_actions:
                embed_info = default_embedder_info(name)
                actions_list.append(
                    embedder_action_metadata(
                        name=googleai_name(name),
                        options=EmbedderOptions(
                            label=embed_info.get('label'),
                            supports=EmbedderSupports(input=embed_info.get('supports', {}).get('input')),
                            dimensions=embed_info.get('dimensions'),
                        ),
                    )
                )

        return actions_list

    async def list_actions(self) -> list[ActionMetadata]:
        return list(self._list_actions_cache)


class VertexAI(Plugin):
    """Vertex AI plugin for Genkit.

    This plugin provides integration with Google Cloud's Vertex AI platform,
    enabling the use of Vertex AI models and services within the Genkit
    framework. It handles initialization of the Vertex AI client and
    registration of model actions.
    """

    _vertexai = True

    name = VERTEXAI_PLUGIN_NAME

    def __init__(
        self,
        credentials: Credentials | None = None,
        project: str | None = None,
        location: str | None = 'us-central1',
        debug_config: DebugConfig | None = None,
        http_options: HttpOptions | HttpOptionsDict | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initializes the GoogleAI plugin.

        Args:
            credentials: Google Cloud credentials for authentication.
                Defaults to None, in which case the client uses default authentication
                mechanisms (e.g., application default credentials or API key).
            project: Name of the Google Cloud project.
            location: Location of the Google Cloud project.
            debug_config: Configuration for debugging the client. Defaults to None.
            http_options: HTTP options for configuring the client's network requests.
                Can be an instance of HttpOptions or a dictionary. Defaults to None.
            api_key: The API key for authenticating with the Google AI service.
                If not provided, it defaults to reading from the 'GEMINI_API_KEY'
                environment variable.
        """
        project = project if project else os.getenv(const.GCLOUD_PROJECT)
        location = location if location else const.DEFAULT_REGION

        self._client = genai.client.Client(
            vertexai=self._vertexai,
            api_key=api_key,
            credentials=credentials,
            project=project,
            location=location,
            debug_config=debug_config,
            http_options=_inject_attribution_headers(http_options),
        )

    async def init(self) -> list[Action]:
        actions: list[Action] = []

        for version in VertexAIGeminiVersion:
            gemini_model = GeminiModel(version, self._client)
            actions.append(
                model(
                    name=str(version),
                    fn=gemini_model.generate,
                    metadata=gemini_model.metadata,
                )
            )

        for version in VertexEmbeddingModels:
            embedder_impl = Embedder(version=version, client=self._client)
            embedder_info = default_embedder_info(version)
            actions.append(
                embedder(
                    name=str(version),
                    fn=embedder_impl.generate,
                    options=EmbedderOptions(
                        label=embedder_info.get('label'),
                        dimensions=embedder_info.get('dimensions'),
                        supports=EmbedderSupports(**embedder_info['supports'])
                        if embedder_info.get('supports')
                        else None,
                    ),
                )
            )

        for version in ImagenVersion:
            imagen_model = ImagenModel(version, self._client)
            actions.append(
                model(
                    name=str(version),
                    fn=imagen_model.generate,
                    metadata=imagen_model.metadata,
                )
            )

        return actions

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        if action_type == ActionKind.MODEL:
            if name.lower().startswith('image'):
                model_ref = vertexai_image_model_info(name)
                model_impl = ImagenModel(name, self._client)
                IMAGE_SUPPORTED_MODELS[name] = model_ref
            else:
                model_ref = google_model_info(name)
                model_impl = GeminiModel(name, self._client)
                SUPPORTED_MODELS[name] = model_ref
            return model(
                name=name,
                fn=model_impl.generate,
                metadata=model_impl.metadata,
            )

        if action_type == ActionKind.EMBEDDER:
            embedder_impl = Embedder(version=name, client=self._client)
            embedder_info = default_embedder_info(name)
            return embedder(
                name=name,
                fn=embedder_impl.generate,
                options=EmbedderOptions(
                    label=embedder_info.get('label'),
                    dimensions=embedder_info.get('dimensions'),
                    supports=EmbedderSupports(**embedder_info['supports']) if embedder_info.get('supports') else None,
                ),
            )

        return None

    @cached_property
    def _list_actions_cache(self) -> list[ActionMetadata]:
        """Generate a list of available actions or models.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects, each with the following attributes:
                - name (str): The name of the action or model.
                - kind (ActionKind): The type or category of the action.
                - info (dict): The metadata dictionary describing the model configuration and properties.
                - config_schema (type): The schema class used for validating the model's configuration.
        """
        actions_list = list()
        for m in self._client.models.list():
            name = m.name.replace('publishers/google/models/', '')
            if 'embed' in name.lower():
                embed_info = default_embedder_info(name)
                actions_list.append(
                    embedder_action_metadata(
                        name=vertexai_name(name),
                        options=EmbedderOptions(
                            label=embed_info.get('label'),
                            supports=EmbedderSupports(input=embed_info.get('supports', {}).get('input')),
                            dimensions=embed_info.get('dimensions'),
                        ),
                    )
                )
            # List all the vertexai models for generate actions
            actions_list.append(
                model_action_metadata(
                    name=vertexai_name(name),
                    info=google_model_info(name).model_dump(),
                    # config_schema=GeminiConfigSchema,
                ),
            )

        return actions_list

    async def list_actions(self) -> list[ActionMetadata]:
        return list(self._list_actions_cache)


def _inject_attribution_headers(http_options: HttpOptions | dict | None = None):
    """Adds genkit client info to the appropriate http headers."""
    if not http_options:
        http_options = HttpOptions()
    else:
        if isinstance(http_options, dict):
            http_options = HttpOptions(**http_options)

    if not http_options.headers:
        http_options.headers = {}

    if 'x-goog-api-client' not in http_options.headers:
        http_options.headers['x-goog-api-client'] = GENKIT_CLIENT_HEADER
    else:
        http_options.headers['x-goog-api-client'] += f' {GENKIT_CLIENT_HEADER}'

    if 'user-agent' not in http_options.headers:
        http_options.headers['user-agent'] = GENKIT_CLIENT_HEADER
    else:
        http_options.headers['user-agent'] += f' {GENKIT_CLIENT_HEADER}'

    return http_options
