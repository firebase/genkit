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


from collections.abc import Callable

from anthropic import AsyncAnthropicVertex

from genkit.ai import ActionRunContext
from genkit.plugins.anthropic.models import AnthropicModel
from genkit.types import GenerateRequest, GenerateResponse, GenerationCommonConfig, ModelInfo

from .model_garden import model_garden_name


class AnthropicModelGarden:
    """Manages integration with Anthropic models on Vertex AI Model Garden."""

    def __init__(
        self,
        model: str,
        location: str,
        project_id: str,
    ) -> None:
        """Initializes the AnthropicModelGarden instance.

        Args:
            model: The name of the specific model to be used from Model Garden
                in the way <publisher>/<model> (e.g., 'anthropic/claude-3-5-sonnet-v2@20241022').
            location: The Google Cloud region where the Model Garden service
                is hosted (e.g., 'us-central1').
            project_id: The Google Cloud project ID where the Model Garden
                model is deployed.
        """
        self.name = model
        self.client = AsyncAnthropicVertex(region=location, project_id=project_id)
        # Strip 'anthropic/' prefix for the model passed to Anthropic SDK
        clean_model_name = model.removeprefix('anthropic/')
        self._anthropic_model = AnthropicModel(model_name=clean_model_name, client=self.client)

    def get_handler(self) -> Callable[[GenerateRequest, ActionRunContext], GenerateResponse]:
        """Returns the generate handler function for this model.

        Returns:
            The handler function that can be used as an Action's fn parameter.
        """
        return self._anthropic_model.generate

    def get_model_info(self) -> ModelInfo:
        """Returns the model information/metadata for this model.

        Returns:
            ModelInfo with the model's capabilities.
        """
        return ModelInfo(
            label=f'ModelGarden - {self.name}',
            supports={
                'multiturn': True,
                'media': True,
                'tools': True,
                'systemRole': True,
                'output': ['text', 'json'],
            },
        )

    @staticmethod
    def get_config_schema():
        """Returns the config schema for this model type."""
        return GenerationCommonConfig
