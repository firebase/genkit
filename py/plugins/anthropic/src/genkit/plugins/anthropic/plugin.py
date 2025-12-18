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

"""Anthropic plugin for Genkit."""

from anthropic import AsyncAnthropic
from genkit.ai import GenkitRegistry, Plugin
from genkit.core.registry import ActionKind
from genkit.plugins.anthropic.model_info import SUPPORTED_ANTHROPIC_MODELS, get_model_info
from genkit.plugins.anthropic.models import AnthropicModel
from genkit.types import GenerationCommonConfig

ANTHROPIC_PLUGIN_NAME = 'anthropic'


def anthropic_name(name: str) -> str:
    """Get Anthropic model name.

    Args:
        name: The name of Anthropic model.

    Returns:
        Fully qualified Anthropic model name.
    """
    return f'{ANTHROPIC_PLUGIN_NAME}/{name}'


class Anthropic(Plugin):
    """Anthropic plugin for Genkit.

    This plugin adds Anthropic models to Genkit for generative AI applications.
    """

    name = ANTHROPIC_PLUGIN_NAME

    def __init__(
        self,
        models: list[str] | None = None,
        **anthropic_params: str,
    ) -> None:
        """Initializes Anthropic plugin with given configuration.

        Args:
            models: List of model names to register. Defaults to all supported models.
            **anthropic_params: Additional parameters passed to the AsyncAnthropic client.
                This may include api_key, base_url, timeout, and other configuration
                settings required by Anthropic's API.
        """
        self.models = models or list(SUPPORTED_ANTHROPIC_MODELS.keys())
        self._anthropic_params = anthropic_params
        self._anthropic_client = AsyncAnthropic(**anthropic_params)

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize plugin by registering models.

        Args:
            ai: The AI registry to initialize the plugin with.
        """
        for model_name in self.models:
            self._define_model(ai, model_name)

    def resolve_action(
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        """Resolve an action.

        Args:
            ai: Genkit registry.
            kind: Action kind.
            name: Action name.
        """
        if kind == ActionKind.MODEL:
            self._resolve_model(ai=ai, name=name)

    def _resolve_model(self, ai: GenkitRegistry, name: str) -> None:
        """Resolve and define an Anthropic model.

        Args:
            ai: Genkit registry.
            name: Model name (may include plugin prefix).
        """
        clean_name = name.replace(f'{ANTHROPIC_PLUGIN_NAME}/', '') if name.startswith(ANTHROPIC_PLUGIN_NAME) else name
        self._define_model(ai, clean_name)

    def _define_model(self, ai: GenkitRegistry, model_name: str) -> None:
        """Define and register a model.

        Args:
            ai: Genkit registry.
            model_name: Model name.
        """
        model = AnthropicModel(model_name=model_name, client=self._anthropic_client)
        model_info = get_model_info(model_name)

        metadata = {
            'model': {
                'supports': model_info.supports.model_dump(),
            }
        }

        ai.define_model(
            name=anthropic_name(model_name),
            fn=model.generate,
            config_schema=GenerationCommonConfig,
            metadata=metadata,
        )
