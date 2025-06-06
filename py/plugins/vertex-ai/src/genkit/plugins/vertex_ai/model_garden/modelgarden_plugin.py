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
from functools import cached_property

from genkit.ai import GenkitRegistry, Plugin
from genkit.blocks.model import model_action_metadata
from genkit.core.action.types import ActionKind
from genkit.plugins.compat_oai.models import SUPPORTED_OPENAI_COMPAT_MODELS
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
    ):
        """Initialize the plugin by registering actions with the registry."""
        self.project_id = project_id if project_id is not None else os.getenv(const.GCLOUD_PROJECT)
        self.location = location if location is not None else const.DEFAULT_REGION
        self.models = models

    def initialize(self, ai: GenkitRegistry) -> None:
        """Handles actions for various openaicompatible models."""
        models = self.models
        if models is None:
            return

        for model in models:
            model_proxy = ModelGarden(
                model=model,
                location=self.location,
                project_id=self.project_id,
                registry=ai,
            )
            model_proxy.define_model()

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
            self._resolve_model(ai=ai, name=name)

    def _resolve_model(self, ai: GenkitRegistry, name: str) -> None:
        """Resolves and defines a Model Garden Vertex AI model within the Genkit registry.

        This internal method handles the logic for registering new models
        of Vertex AI Model Garden that are compatible with OpenaI
        based on the provided name.
        It extracts a clean name, determines the model type, instantiates the
        appropriate model class, and registers it with the Genkit AI registry.

        Args:
            ai: The Genkit AI registry instance to define the model in.
            name: The name of the model to resolve. This name might include a
                prefix indicating it's from a specific plugin.
        """
        clean_name = (
            name.replace(MODELGARDEN_PLUGIN_NAME + '/', '') if name.startswith(MODELGARDEN_PLUGIN_NAME) else name
        )

        model_proxy = ModelGarden(
            model=clean_name,
            location=self.location,
            project_id=self.project_id,
            registry=ai,
        )
        model_proxy.define_model()

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
        actions_list = []
        for model, model_info in SUPPORTED_OPENAI_COMPAT_MODELS.items():
            actions_list.append(
                model_action_metadata(
                    name=model_garden_name(model), info=model_info.model_dump(), config_schema=OpenAIConfig
                )
            )

        return actions_list
