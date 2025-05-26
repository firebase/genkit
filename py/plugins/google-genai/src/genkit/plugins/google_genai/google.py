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
from google.genai.types import EmbedContentConfig, GenerateImagesConfigOrDict, HttpOptions, HttpOptionsDict

import genkit.plugins.google_genai.constants as const
from genkit.ai import GENKIT_CLIENT_HEADER, GenkitRegistry, Plugin
from genkit.blocks.embedding import embedder_action_metadata
from genkit.blocks.model import model_action_metadata
from genkit.core.registry import ActionKind
from genkit.plugins.google_genai.models.embedder import (
    Embedder,
    GeminiEmbeddingModels,
    VertexEmbeddingModels,
    default_embedder_info,
)
from genkit.plugins.google_genai.models.gemini import (
    SUPPORTED_MODELS,
    GeminiConfigSchema,
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

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions in the registry.

        Args:
            ai: the action registry.
        """
        for version in GoogleAIGeminiVersion:
            gemini_model = GeminiModel(version, self._client, ai)
            ai.define_model(
                name=googleai_name(version),
                fn=gemini_model.generate,
                metadata=gemini_model.metadata,
                config_schema=GeminiConfigSchema,
            )

        for version in GeminiEmbeddingModels:
            embedder = Embedder(version=version, client=self._client)
            ai.define_embedder(
                name=googleai_name(version),
                fn=embedder.generate,
                metadata=default_embedder_info(version),
                config_schema=EmbedContentConfig,
            )

    def resolve_action(
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        """Resolves and action.

        Args:
            ai: The Genkit registry.
            kind: The kind of action to resolve.
            name: The name of the action to resolve.
        """
        if kind == ActionKind.MODEL:
            self._resolve_model(ai, name)
        elif kind == ActionKind.EMBEDDER:
            self._resolve_embedder(ai, name)

    def _resolve_model(self, ai: GenkitRegistry, name: str) -> None:
        """Resolves and defines a Google AI model within the Genkit registry.

        This internal method handles the logic for registering different types of
        Google AI models (e.g., Gemini text models) based on the provided name.
        It extracts a clean name, determines the model type, instantiates the
        appropriate model class, and registers it with the Genkit AI registry.

        Args:
            ai: The Genkit AI registry instance to define the model in.
            name: The name of the model to resolve. This name might include a
                prefix indicating it's from a specific plugin (e.g., 'googleai/gemini-pro').
        """
        _clean_name = name.replace(GOOGLEAI_PLUGIN_NAME + '/', '') if name.startswith(GOOGLEAI_PLUGIN_NAME) else name
        model_ref = google_model_info(_clean_name)

        SUPPORTED_MODELS[_clean_name] = model_ref

        gemini_model = GeminiModel(_clean_name, self._client, ai)

        ai.define_model(
            name=googleai_name(_clean_name),
            fn=gemini_model.generate,
            metadata=gemini_model.metadata,
            config_schema=GeminiConfigSchema,
        )

    def _resolve_embedder(self, ai: GenkitRegistry, name: str) -> None:
        """Resolves and defines a Google AI embedder within the Genkit registry.

        This internal method handles the logic for registering Google AI embedder
        models. It extracts a clean name, instantiates the embedder class, and
        registers it with the Genkit AI registry.

        Args:
            ai: The Genkit AI registry instance to define the embedder in.
            name: The name of the embedder to resolve. This name might include a
                prefix indicating it's from a specific plugin (e.g., 'googleai/embedding-001').
        """
        _clean_name = name.replace(GOOGLEAI_PLUGIN_NAME + '/', '') if name.startswith(GOOGLEAI_PLUGIN_NAME) else name
        embedder = Embedder(version=_clean_name, client=self._client)

        ai.define_embedder(
            name=googleai_name(_clean_name),
            fn=embedder.generate,
            metadata=default_embedder_info(_clean_name),
            config_schema=EmbedContentConfig,
        )

    @cached_property
    def list_actions(self) -> list[dict[str, str]]:
        """Generate a list of available actions or models.

        Returns:
            list of actions dicts with the following shape:
            {
                'name': str,
                'kind': ActionKind,
            }
        """
        actions_list = list()
        for m in self._client.models.list():
            name = m.name.replace('models/', '')
            if 'generateContent' in m.supported_actions:
                actions_list.append(
                    model_action_metadata(
                        name=googleai_name(name),
                        info=google_model_info(name).model_dump(),
                        config_schema=GeminiConfigSchema,
                    ),
                )

            if 'embedContent' in m.supported_actions:
                actions_list.append(
                    embedder_action_metadata(
                        name=googleai_name(name),
                        info=default_embedder_info(name),
                        config_schema=EmbedContentConfig,
                    )
                )

        return actions_list


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

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions with the registry.

        This method registers the Vertex AI model actions with the provided
        registry, making them available for use in the Genkit framework.

        Args:
            ai: the action registry.
        """
        for version in VertexAIGeminiVersion:
            gemini_model = GeminiModel(version, self._client, ai)
            ai.define_model(
                name=vertexai_name(version),
                fn=gemini_model.generate,
                metadata=gemini_model.metadata,
                config_schema=GeminiConfigSchema,
            )

        for version in VertexEmbeddingModels:
            embedder = Embedder(version=version, client=self._client)
            ai.define_embedder(
                name=vertexai_name(version),
                fn=embedder.generate,
                metadata=default_embedder_info(version),
                config_schema=EmbedContentConfig,
            )

        for version in ImagenVersion:
            imagen_model = ImagenModel(version, self._client)
            ai.define_model(
                name=vertexai_name(version),
                fn=imagen_model.generate,
                metadata=imagen_model.metadata,
                config_schema=GenerateImagesConfigOrDict,
            )

    def resolve_action(
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        """Resolves and action.

        Args:
            ai: The Genkit registry.
            kind: The kind of action to resolve.
            name: The name of the action to resolve.
        """
        if kind == ActionKind.MODEL:
            self._resolve_model(ai, name)
        elif kind == ActionKind.EMBEDDER:
            self._resolve_embedder(ai, name)

    def _resolve_model(self, ai: GenkitRegistry, name: str) -> None:
        """Resolves and defines a Vertex AI model within the Genkit registry.

        This internal method handles the logic for registering different types of
        Vertex AI models (e.g., Gemini text models, Imagen image models) based on
        the provided name. It extracts a clean name, determines the model type,
        instantiates the appropriate model class, and registers it with the Genkit
        AI registry.

        Args:
            ai: The Genkit AI registry instance to define the model in.
            name: The name of the model to resolve. This name might include a
                prefix indicating it's from a specific plugin (e.g., 'vertexai/gemini-pro').
        """
        _clean_name = name.replace(VERTEXAI_PLUGIN_NAME + '/', '') if name.startswith(VERTEXAI_PLUGIN_NAME) else name

        if _clean_name.lower().startswith('image'):
            model_ref = vertexai_image_model_info(_clean_name)
            model = ImagenModel(_clean_name, self._client)
            IMAGE_SUPPORTED_MODELS[_clean_name] = model_ref
            config_schema = GenerateImagesConfigOrDict
        else:
            model_ref = google_model_info(_clean_name)
            model = GeminiModel(_clean_name, self._client, ai)
            SUPPORTED_MODELS[_clean_name] = model_ref
            config_schema = GeminiConfigSchema

        ai.define_model(
            name=vertexai_name(_clean_name),
            fn=model.generate,
            metadata=model.metadata,
            config_schema=config_schema,
        )

    def _resolve_embedder(self, ai: GenkitRegistry, name: str) -> None:
        """Resolves and defines a Vertex AI embedder within the Genkit registry.

        This internal method handles the logic for registering Google AI embedder
        models. It extracts a clean name, instantiates the embedder class, and
        registers it with the Genkit AI registry.

        Args:
            ai: The Genkit AI registry instance to define the embedder in.
            name: The name of the embedder to resolve. This name might include a
                prefix indicating it's from a specific plugin (e.g., 'vertexai/embedding-001').
        """
        _clean_name = name.replace(VERTEXAI_PLUGIN_NAME + '/', '') if name.startswith(VERTEXAI_PLUGIN_NAME) else name
        embedder = Embedder(version=_clean_name, client=self._client)

        ai.define_embedder(
            name=vertexai_name(_clean_name),
            fn=embedder.generate,
            metadata=default_embedder_info(_clean_name),
            config_schema=EmbedContentConfig,
        )

    @cached_property
    def list_actions(self) -> list[dict[str, str]]:
        """Generate a list of available actions or models.

        Returns:
            list of actions dicts with the following shape:
            {
                'name': str,
                'kind': ActionKind,
            }
        """
        actions_list = list()
        for m in self._client.models.list():
            name = m.name.replace('publishers/google/models/', '')
            if 'embed' in name.lower():
                actions_list.append(
                    embedder_action_metadata(
                        name=vertexai_name(name),
                        info=default_embedder_info(name),
                        config_schema=EmbedContentConfig,
                    )
                )
            # List all the vertexai models for generate actions
            actions_list.append(
                model_action_metadata(
                    name=vertexai_name(name),
                    info=google_model_info(name).model_dump(),
                    config_schema=GeminiConfigSchema,
                ),
            )

        return actions_list


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
