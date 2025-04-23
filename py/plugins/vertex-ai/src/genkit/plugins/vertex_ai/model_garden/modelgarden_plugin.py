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

from genkit.ai import GenkitRegistry, Plugin
from genkit.plugins.vertex_ai import constants as const

from .model_garden import OPENAI_COMPAT, ModelGarden


class VertexAIModelGarden(Plugin):
    """Model Garden plugin for Genkit.

    This plugin provides integration with Google Cloud's Vertex AI platform,
    enabling the use of Vertex AI models and services within the Genkit
    framework. It handles initialization of the Model Garden client and
    registration of model actions.
    """

    name = 'modelgarden'

    def __init__(self, project_id: str | None = None, location: str | None = None, models: list[str] | None = None):
        """Initialize the plugin by registering actions with the registry."""
        self.project_id = project_id if project_id is not None else os.getenv(const.GCLOUD_PROJECT)
        self.location = location if location is not None else const.DEFAULT_REGION
        self.models = models

    def initialize(self, ai: GenkitRegistry) -> None:
        """Handles actions for various openaicompatible models."""
        models = self.models
        if models:
            for model in models:
                model_info = ModelGarden.get_model_info(model)
                if model_info:
                    if model_info['type'] == OPENAI_COMPAT:
                        ModelGarden.to_openai_compatible_model(
                            ai,
                            model=model_info['name'],
                            location=self.location,
                            project_id=self.project_id,
                        )
