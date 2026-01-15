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

from typing import Callable

from anthropic import AsyncAnthropicVertex
from genkit.ai import GenkitRegistry
from genkit.plugins.anthropic.models import AnthropicModel
from genkit.types import GenerationCommonConfig, ModelInfo

from .model_garden import model_garden_name


class AnthropicModelGarden:
    """Manages integration with Anthropic models on Vertex AI Model Garden."""

    def __init__(
        self,
        model: str,
        location: str,
        project_id: str,
        registry: GenkitRegistry,
    ) -> None:
        """Initializes the AnthropicModelGarden instance.

        Args:
            model: The name of the specific model to be used from Model Garden
                in the way <publisher>/<model> (e.g., 'anthropic/claude-3-5-sonnet-v2@20241022').
            location: The Google Cloud region where the Model Garden service
                is hosted (e.g., 'us-central1').
            project_id: The Google Cloud project ID where the Model Garden
                model is deployed.
            registry: An instance of `GenkitRegistry` to register the model with.
        """
        self.name = model
        self.ai = registry
        self.client = AsyncAnthropicVertex(region=location, project_id=project_id)

    def define_model(self) -> None:
        """Defines and registers the Anthropic model with the Genkit registry."""
        # Strip 'anthropic/' prefix if present for the model passed to Anthropic SDK
        # But for model definition in Genkit, use the full name format we want to expose
        clean_model_name = self.name.replace('anthropic/', '') if 'anthropic/' in self.name else self.name
        
        # AnthropicModel wrapper from genkit-anthropic expects the clean name (e.g. claude-3-5-sonnet...)
        anthropic_model = AnthropicModel(model_name=clean_model_name, client=self.client)
        
        self.ai.define_model(
            name=model_garden_name(self.name),
            fn=anthropic_model.generate,
            config_schema=GenerationCommonConfig,
            metadata={
                'model': ModelInfo(
                    label=f'ModelGarden - {self.name}',
                    supports={
                        'multiturn': True,
                        'media': True,
                        'tools': True,
                        'systemRole': True,
                        'output': ['text', 'json'],
                    },
                ).model_dump()
            },
        )
