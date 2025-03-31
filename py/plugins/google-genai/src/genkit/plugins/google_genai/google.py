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

from google import genai
from google.auth.credentials import Credentials
from google.genai.client import DebugConfig
from google.genai.types import HttpOptions, HttpOptionsDict

from genkit.ai import GENKIT_CLIENT_HEADER, Plugin
from genkit.ai.registry import GenkitRegistry
from genkit.plugins.google_genai.models.embedder import (
    Embedder,
    GeminiEmbeddingModels,
    VertexEmbeddingModels,
)
from genkit.plugins.google_genai.models.gemini import (
    GeminiApiOnlyVersion,
    GeminiConfigSchema,
    GeminiModel,
    GeminiVersion,
)

PLUGIN_NAME = 'google_genai'


def google_genai_name(name: str) -> str:
    """Create a Google AI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Google AI action name.
    """
    return f'{PLUGIN_NAME}/{name}'


class GoogleGenai(Plugin):
    """Google Ai plugin for Genkit"""

    name = PLUGIN_NAME

    def __init__(
        self,
        vertexai: bool | None = None,
        api_key: str | None = None,
        credentials: Credentials | None = None,
        project: str | None = None,
        location: str | None = None,
        debug_config: DebugConfig | None = None,
        http_options: HttpOptions | HttpOptionsDict | None = None,
    ):
        """Initialize the GoogleGenai plugin.

        Args:
            vertexai: Whether to use Vertex AI.
            api_key: The API key to use.
            credentials: The credentials to use.
        """
        api_key = api_key if api_key else os.getenv('GEMINI_API_KEY')
        if not vertexai and not api_key:
            raise ValueError(
                'Gemini api key should be passed in plugin params or as a GEMINI_API_KEY environment variable'
            )
        self._vertexai = vertexai

        self._client = genai.client.Client(
            vertexai=vertexai,
            api_key=api_key if not vertexai else None,
            credentials=credentials,
            project=project,
            location=location,
            debug_config=debug_config,
            http_options=_inject_attribution_headers(http_options),
        )

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions in the registry.

        Args:
            ai: the action registry.

        Returns:
            None
        """
        supported_gemini_models = list(GeminiVersion)
        if not self._client.vertexai:
            supported_gemini_models.extend(list(GeminiApiOnlyVersion))

        for version in supported_gemini_models:
            gemini_model = GeminiModel(version, self._client, ai)
            ai.define_model(
                name=google_genai_name(version),
                fn=gemini_model.generate,
                metadata=gemini_model.metadata,
                config_schema=GeminiConfigSchema,
            )

        embeding_models = VertexEmbeddingModels if self._client.vertexai else GeminiEmbeddingModels
        for version in embeding_models:
            embedder = Embedder(version=version, client=self._client)
            ai.define_embedder(name=google_genai_name(version), fn=embedder.generate)


def _inject_attribution_headers(http_options):
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
