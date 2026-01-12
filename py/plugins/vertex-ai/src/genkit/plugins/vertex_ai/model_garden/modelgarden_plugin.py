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

"""ModelGarden API Compatible Plugin for Genkit."""

import os

from genkit.ai import Plugin
from genkit.blocks.model import model, model_action_metadata
from genkit.core.action import ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.plugins.compat_oai.models import SUPPORTED_OPENAI_COMPAT_MODELS, OpenAIModelHandler
from genkit.plugins.compat_oai.models.model_info import PluginSource
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.plugins.vertex_ai import constants as const

from .model_garden import MODELGARDEN_PLUGIN_NAME, ModelGarden, model_garden_name


class VertexAIModelGarden(Plugin):
    """Model Garden plugin for Genkit.

    This plugin provides integration with Google Cloud's Vertex AI platform,
    enabling the use of Vertex AI models and services within the Genkit
    framework. It handles initialization of the Model Garden client and
    registration of model actions.
    """

    name = MODELGARDEN_PLUGIN_NAME

    def __init__(
        self,
        project_id: str | None = None,
        location: str | None = None,
        models: list[str] | None = None,
    ) -> None:
        """Initializes the plugin and sets up its configuration.

        This constructor prepares the plugin by assigning the Google Cloud project ID,
        location, and a list of models to be used.

        Args:
            project_id: The Google Cloud project ID to use. If not provided, it attempts
                to load from the `GCLOUD_PROJECT` environment variable.
            location: The Google Cloud region to use for services. If not provided,
                it defaults to `DEFAULT_REGION`.
            models: An optional list of model names to register with the plugin.
        """
        self.project_id = project_id if project_id is not None else os.getenv(const.GCLOUD_PROJECT)
        self.location = location if location is not None else const.DEFAULT_REGION
        self.models = models or []

    async def init(self):
        """Return eagerly-initialized model actions."""
        return [self._create_model_action(m) for m in self.models]

    async def resolve(self, action_type: ActionKind, name: str):
        if action_type != ActionKind.MODEL:
            return None
        clean_name = (
            name.replace(MODELGARDEN_PLUGIN_NAME + '/', '') if name.startswith(MODELGARDEN_PLUGIN_NAME) else name
        )
        if clean_name not in SUPPORTED_OPENAI_COMPAT_MODELS:
            return None
        return self._create_model_action(clean_name)

    async def list_actions(self) -> list[ActionMetadata]:
        return [
            model_action_metadata(
                name=model_garden_name(model_name),
                info=model_info.model_dump(),
                config_schema=OpenAIConfig,
            )
            for model_name, model_info in SUPPORTED_OPENAI_COMPAT_MODELS.items()
        ]

    def _create_model_action(self, model_name: str):
        model_proxy = ModelGarden(
            model=model_name,
            location=self.location,
            project_id=self.project_id,
            registry=None,
        )
        handler = OpenAIModelHandler.get_model_handler(
            model=model_name,
            client=model_proxy.client,  # Vertex Model Garden OpenAI-compatible client
            source=PluginSource.MODEL_GARDEN,
        )
        model_info = model_proxy.get_model_info()
        return model(
            name=model_name,
            fn=handler,
            config_schema=OpenAIConfig,
            metadata={'model': model_info},
        )
