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


from typing import cast
from anthropic import AsyncAnthropic, AsyncAnthropicVertex

from genkit.ai import GenkitRegistry
from genkit.plugins.anthropic.models import AnthropicModel
from genkit.plugins.compat_oai.typing import SupportedOutputFormat
from genkit.types import GenerationCommonConfig, ModelInfo, Supports

from genkit.ai import ActionRunContext
from genkit.core.typing import Supports
from genkit.plugins.anthropic.models import AnthropicModel
from genkit.types import GenerateRequest, GenerateResponse, GenerationCommonConfig, ModelInfo


SUPPORTED_ANTHROPIC_MODELS: dict[str, ModelInfo] = {
    'anthropic/claude-3-5-sonnet-v2@20241022': ModelInfo(
        label='ModelGarden - Anthropic - claude-3-5-sonnet-v2',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-3-5-sonnet@20240620': ModelInfo(
        label='ModelGarden - Anthropic - claude-3-5-sonnet',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-3-sonnet@20240229': ModelInfo(
        label='ModelGarden - Anthropic - claude-3-sonnet',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-3-haiku@20240307': ModelInfo(
        label='ModelGarden - Anthropic - claude-3-haiku',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-3-opus@20240229': ModelInfo(
        label='ModelGarden - Anthropic - claude-3-opus',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-3-7-sonnet@20250219': ModelInfo(
        label='ModelGarden - Anthropic - claude-3-7-sonnet',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-opus-4@20250514': ModelInfo(
        label='ModelGarden - Anthropic - claude-opus-4',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-sonnet-4@20250514': ModelInfo(
        label='ModelGarden - Anthropic - claude-sonnet-4',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'anthropic/claude-opus-4-1-20250805': ModelInfo(
        label='ModelGarden - Anthropic - claude-opus-4-1',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
    'anthropic/claude-sonnet-4-5-20250929': ModelInfo(
        label='ModelGarden - Anthropic - claude-sonnet-4-5',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
    'anthropic/claude-haiku-4-5-20251001': ModelInfo(
        label='ModelGarden - Anthropic - claude-haiku-4-5',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
}


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
        self._anthropic_model = AnthropicModel(model_name=clean_model_name, client=cast(AsyncAnthropic, self.client))

    def get_handler(self) -> Callable[[GenerateRequest, ActionRunContext], Awaitable[GenerateResponse]]:
        """Returns the generate handler function for this model.

        # AnthropicModel wrapper from genkit-anthropic expects the clean name (e.g. claude-3-5-sonnet...)
        anthropic_model = AnthropicModel(model_name=clean_model_name, client=cast(AsyncAnthropic, self.client))

        self.ai.define_model(
            name=model_garden_name(self.name),
            fn=lambda r, c: anthropic_model.generate(r, c),
            config_schema=GenerationCommonConfig,
            metadata={
                'model': ModelInfo(
                    label=f'ModelGarden - {self.name}',
                    supports=Supports(
                        multiturn=True,
                        media=True,
                        tools=True,
                        systemRole=True,
                        output=['text', 'json'],
                    ),
                ).model_dump()
            },
        )

    @staticmethod
    def get_config_schema():
        """Returns the config schema for this model type."""
        return GenerationCommonConfig
