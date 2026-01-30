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


"""Google AI and Vertex AI plugin implementations."""

import os

from google import genai
from google.auth.credentials import Credentials
from google.genai.client import DebugConfig
from google.genai.types import HttpOptions, HttpOptionsDict

import genkit.plugins.google_genai.constants as const
from genkit.ai import GENKIT_CLIENT_HEADER, Plugin
from genkit.blocks.embedding import EmbedderOptions, EmbedderSupports, embedder_action_metadata
from genkit.blocks.model import model_action_metadata
from genkit.core.action import Action, ActionMetadata
from genkit.core.registry import ActionKind
from genkit.plugins.google_genai.models.embedder import (
    Embedder,
    default_embedder_info,
)
from genkit.plugins.google_genai.models.gemini import (
    SUPPORTED_MODELS,
    GeminiConfigSchema,
    GeminiModel,
    get_model_config_schema,
    google_model_info,
)
from genkit.plugins.google_genai.models.imagen import (
    SUPPORTED_MODELS as IMAGE_SUPPORTED_MODELS,
    ImagenConfigSchema,
    ImagenModel,
    vertexai_image_model_info,
)
from genkit.plugins.google_genai.models.veo import (
    VeoConfigSchema,
    VeoModel,
    veo_model_info,
)


class GenaiModels:
    """Container for models discovered from the API."""

    gemini: list[str]
    imagen: list[str]
    embedders: list[str]
    veo: list[str]

    def __init__(self) -> None:
        """Initialize Google GenAI plugin."""
        self.gemini = []
        self.imagen = []
        self.embedders = []
        self.veo = []


def _list_genai_models(client: genai.Client, is_vertex: bool) -> GenaiModels:
    """Lists supported models and embedders from the Google GenAI SDK.

    Mirrors logic from Go plugin's listGenaiModels.
    """
    models = GenaiModels()

    for m in client.models.list():
        name = m.name
        if not name:
            continue

        # Cleanup prefix
        if is_vertex:
            if name.startswith('publishers/google/models/'):
                name = name[25:]
        elif name.startswith('models/'):
            name = name[7:]

        description = (m.description or '').lower()
        if 'deprecated' in description:
            continue

        if not m.supported_actions:
            continue

        # Embedders
        if 'embedContent' in m.supported_actions:
            models.embedders.append(name)

        # Imagen (Vertex mostly)
        if 'predict' in m.supported_actions and 'imagen' in name.lower():
            models.imagen.append(name)

        # Veo
        if 'generateVideos' in m.supported_actions or 'veo' in name.lower():
            models.veo.append(name)

        # Gemini / Gemma
        if 'generateContent' in m.supported_actions:
            lower_name = name.lower()
            if 'gemini' in lower_name or 'gemma' in lower_name:
                models.gemini.append(name)

    return models


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
        api_version: str | None = None,
        base_url: str | None = None,
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
            api_version: The API version to use (e.g., 'v1beta'). Defaults to None.
            base_url: The base URL for the API. Defaults to None.

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
            http_options=_inject_attribution_headers(http_options, base_url, api_version),
        )

    async def init(self) -> list[Action]:
        """Initialize the plugin.

        Returns:
            List of Action objects for known/supported models.
        """
        genai_models = _list_genai_models(self._client, is_vertex=False)

        actions = []
        # Gemini Models
        for name in genai_models.gemini:
            actions.append(self._resolve_model(googleai_name(name)))

        # Embedders
        for name in genai_models.embedders:
            actions.append(self._resolve_embedder(googleai_name(name)))

        return actions

    def _list_known_models(self) -> list[Action]:
        """List known models as Action objects.

        Deprecated: Used only for internal testing if needed, but 'init' should be source of truth.
        Keeping for compatibility but redirecting to dynamic list logic if accessed directly?
        The interface defines init(), this helper was internal.
        """
        # Re-use init logic synchronously? init is async.
        # Let's implementation just mimic init logic but sync call to client.models.list is fine (it is iterator)
        genai_models = _list_genai_models(self._client, is_vertex=False)
        actions = []
        for name in genai_models.gemini:
            actions.append(self._resolve_model(googleai_name(name)))
        return actions

    def _list_known_embedders(self) -> list[Action]:
        """List known embedders as Action objects."""
        genai_models = _list_genai_models(self._client, is_vertex=False)
        actions = []
        for name in genai_models.embedders:
            actions.append(self._resolve_embedder(googleai_name(name)))
        return actions

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action by creating and returning an Action object.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action to resolve.

        Returns:
            Action object if found, None otherwise.
        """
        if action_type == ActionKind.MODEL:
            return self._resolve_model(name)
        elif action_type == ActionKind.EMBEDDER:
            return self._resolve_embedder(name)
        return None

    def _resolve_model(self, name: str) -> Action:
        """Create an Action object for a Google AI model.

        Args:
            name: The namespaced name of the model.

        Returns:
            Action object for the model.
        """
        # Extract local name (remove plugin prefix)
        _clean_name = name.replace(GOOGLEAI_PLUGIN_NAME + '/', '') if name.startswith(GOOGLEAI_PLUGIN_NAME) else name
        model_ref = google_model_info(_clean_name)

        SUPPORTED_MODELS[_clean_name] = model_ref

        gemini_model = GeminiModel(_clean_name, self._client)

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=gemini_model.generate,
            metadata=model_action_metadata(
                name=name,
                info=gemini_model.metadata['model']['supports'],
                config_schema=GeminiConfigSchema,
            ).metadata,
        )

    def _resolve_embedder(self, name: str) -> Action:
        """Create an Action object for a Google AI embedder.

        Args:
            name: The namespaced name of the embedder.

        Returns:
            Action object for the embedder.
        """
        # Extract local name (remove plugin prefix)
        _clean_name = name.replace(GOOGLEAI_PLUGIN_NAME + '/', '') if name.startswith(GOOGLEAI_PLUGIN_NAME) else name
        embedder = Embedder(version=_clean_name, client=self._client)

        embedder_info = default_embedder_info(_clean_name)

        return Action(
            kind=ActionKind.EMBEDDER,
            name=name,
            fn=embedder.generate,
            metadata=embedder_action_metadata(
                name=name,
                options=EmbedderOptions(
                    label=embedder_info.get('label'),
                    supports=EmbedderSupports(input=embedder_info.get('supports', {}).get('input')),
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
        genai_models = _list_genai_models(self._client, is_vertex=False)
        actions_list = []

        for name in genai_models.gemini:
            actions_list.append(
                model_action_metadata(
                    name=googleai_name(name),
                    info=google_model_info(name).model_dump(by_alias=True),
                    config_schema=get_model_config_schema(name),
                )
            )

        for name in genai_models.embedders:
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
        api_version: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initializes the VertexAI plugin.

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
            api_version: The API version to use. Defaults to None.
            base_url: The base URL for the API. Defaults to None.
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
            http_options=_inject_attribution_headers(http_options, base_url, api_version),
        )

    async def init(self) -> list[Action]:
        """Initialize the plugin.

        Returns:
            List of Action objects for known/supported models.
        """
        genai_models = _list_genai_models(self._client, is_vertex=True)
        actions = []

        for name in genai_models.gemini:
            actions.append(self._resolve_model(vertexai_name(name)))

        for name in genai_models.imagen:
            actions.append(self._resolve_model(vertexai_name(name)))

        for name in genai_models.veo:
            actions.append(self._resolve_model(vertexai_name(name)))

        for name in genai_models.embedders:
            actions.append(self._resolve_embedder(vertexai_name(name)))

        return actions

    def _list_known_models(self) -> list[Action]:
        """List known models as Action objects."""
        genai_models = _list_genai_models(self._client, is_vertex=True)
        actions = []
        for name in genai_models.gemini:
            actions.append(self._resolve_model(vertexai_name(name)))
        for name in genai_models.imagen:
            actions.append(self._resolve_model(vertexai_name(name)))
        for name in genai_models.veo:
            actions.append(self._resolve_model(vertexai_name(name)))
        return actions

    def _list_known_embedders(self) -> list[Action]:
        """List known embedders as Action objects."""
        genai_models = _list_genai_models(self._client, is_vertex=True)
        actions = []
        for name in genai_models.embedders:
            actions.append(self._resolve_embedder(vertexai_name(name)))
        return actions

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action by creating and returning an Action object.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action to resolve.

        Returns:
            Action object if found, None otherwise.
        """
        if action_type == ActionKind.MODEL:
            return self._resolve_model(name)
        elif action_type == ActionKind.EMBEDDER:
            return self._resolve_embedder(name)
        return None

    def _resolve_model(self, name: str) -> Action:
        """Create an Action object for a Vertex AI model.

        Args:
            name: The namespaced name of the model.

        Returns:
            Action object for the model.
        """
        # Extract local name (remove plugin prefix)
        _clean_name = name.replace(VERTEXAI_PLUGIN_NAME + '/', '') if name.startswith(VERTEXAI_PLUGIN_NAME) else name

        if _clean_name.lower().startswith('image'):
            model_ref = vertexai_image_model_info(_clean_name)
            model = ImagenModel(_clean_name, self._client)
            IMAGE_SUPPORTED_MODELS[_clean_name] = model_ref
        elif _clean_name.lower().startswith('veo'):
            model_ref = veo_model_info(_clean_name)
            model = VeoModel(_clean_name, self._client)
        else:
            model_ref = google_model_info(_clean_name)
            model = GeminiModel(_clean_name, self._client)
            SUPPORTED_MODELS[_clean_name] = model_ref

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=model.generate,
            metadata=model_action_metadata(
                name=name,
                info=model.metadata['model']['supports'],
                config_schema=GeminiConfigSchema
                if not _clean_name.lower().startswith('image')
                else None,  # TODO: Add ImagenConfigSchema if available
            ).metadata,
        )

    def _resolve_embedder(self, name: str) -> Action:
        """Create an Action object for a Vertex AI embedder.

        Args:
            name: The namespaced name of the embedder.

        Returns:
            Action object for the embedder.
        """
        # Extract local name (remove plugin prefix)
        _clean_name = name.replace(VERTEXAI_PLUGIN_NAME + '/', '') if name.startswith(VERTEXAI_PLUGIN_NAME) else name
        embedder = Embedder(version=_clean_name, client=self._client)

        embedder_info = default_embedder_info(_clean_name)

        return Action(
            kind=ActionKind.EMBEDDER,
            name=name,
            fn=embedder.generate,
            metadata=embedder_action_metadata(
                name=name,
                options=EmbedderOptions(
                    label=embedder_info.get('label'),
                    supports=EmbedderSupports(input=embedder_info.get('supports', {}).get('input')),
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
        genai_models = _list_genai_models(self._client, is_vertex=True)
        actions_list = []

        for name in genai_models.gemini:
            actions_list.append(
                model_action_metadata(
                    name=vertexai_name(name),
                    info=google_model_info(name).model_dump(by_alias=True),
                    config_schema=get_model_config_schema(name),
                )
            )

        for name in genai_models.imagen:
            actions_list.append(
                model_action_metadata(
                    name=vertexai_name(name),
                    info=vertexai_image_model_info(name).model_dump(by_alias=True),
                    config_schema=ImagenConfigSchema,
                )
            )

        for name in genai_models.veo:
            actions_list.append(
                model_action_metadata(
                    name=vertexai_name(name),
                    info=veo_model_info(name).model_dump(),
                    config_schema=VeoConfigSchema,
                )
            )

        for name in genai_models.embedders:
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

        return actions_list


def _inject_attribution_headers(
    http_options: HttpOptions | HttpOptionsDict | None = None,
    base_url: str | None = None,
    api_version: str | None = None,
) -> HttpOptions:
    """Adds genkit client info to the appropriate http headers."""
    if not http_options:
        opts = HttpOptions()
    elif isinstance(http_options, HttpOptions):
        opts = http_options
    else:
        opts = HttpOptions.model_validate(http_options)

    if base_url:
        opts.base_url = base_url
    if api_version:
        opts.api_version = api_version

    if not opts.headers:
        opts.headers = {}

    if 'x-goog-api-client' not in opts.headers:
        opts.headers['x-goog-api-client'] = GENKIT_CLIENT_HEADER
    else:
        opts.headers['x-goog-api-client'] += f' {GENKIT_CLIENT_HEADER}'

    if 'user-agent' not in opts.headers:
        opts.headers['user-agent'] = GENKIT_CLIENT_HEADER
    else:
        opts.headers['user-agent'] += f' {GENKIT_CLIENT_HEADER}'

    return opts
