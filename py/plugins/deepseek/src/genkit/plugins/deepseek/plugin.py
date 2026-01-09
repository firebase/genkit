# Copyright 2026 Google LLC
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

"""DeepSeek Plugin for Genkit."""

import os
from functools import cached_property

from genkit.ai import GenkitRegistry, Plugin
from genkit.blocks.model import model_action_metadata
from genkit.core.action import ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.error import GenkitError
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.plugins.deepseek.model_info import SUPPORTED_DEEPSEEK_MODELS
from genkit.plugins.deepseek.models import DEEPSEEK_PLUGIN_NAME, DeepSeekModel, deepseek_name


class DeepSeek(Plugin):
    """DeepSeek plugin for Genkit.

    This plugin provides integration with DeepSeek's OpenAI-compatible API,
    enabling the use of DeepSeek models within the Genkit framework.
    """

    name = DEEPSEEK_PLUGIN_NAME

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        **deepseek_params,
    ) -> None:
        """Initialize the plugin and set up its configuration.

        Args:
            api_key: The DeepSeek API key. If not provided, it attempts to load
                from the DEEPSEEK_API_KEY environment variable.
            models: An optional list of model names to register with the plugin.
                If None, all supported models will be registered.
            **deepseek_params: Additional parameters for the DeepSeek client.

        Raises:
            GenkitError: If no API key is provided via parameter or environment.
        """
        self.api_key = api_key if api_key is not None else os.getenv('DEEPSEEK_API_KEY')

        if not self.api_key:
            raise GenkitError(message='Please provide api_key or set DEEPSEEK_API_KEY environment variable.')

        self.models = models
        self.deepseek_params = deepseek_params

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering specified models.

        Args:
            ai: The Genkit registry where models will be registered.
        """
        models = self.models
        if models is None:
            models = list(SUPPORTED_DEEPSEEK_MODELS.keys())

        for model in models:
            deepseek_model = DeepSeekModel(
                model=model,
                api_key=self.api_key,
                registry=ai,
                **self.deepseek_params,
            )
            deepseek_model.define_model()

    def resolve_action(
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        """Resolve and register an action dynamically.

        Args:
            ai: The Genkit registry.
            kind: The kind of action to resolve.
            name: The name of the action to resolve.
        """
        if kind == ActionKind.MODEL:
            self._resolve_model(ai=ai, name=name)

    def _resolve_model(self, ai: GenkitRegistry, name: str) -> None:
        """Resolve and define a DeepSeek model within the Genkit registry.

        This internal method handles the logic for registering DeepSeek models
        dynamically based on the provided name. It extracts a clean name,
        instantiates the DeepSeek class, and registers it with the registry.

        Args:
            ai: The Genkit AI registry instance to define the model in.
            name: The name of the model to resolve. This name might include a
                prefix indicating it's from the DeepSeek plugin.
        """
        clean_name = name.replace(DEEPSEEK_PLUGIN_NAME + '/', '') if name.startswith(DEEPSEEK_PLUGIN_NAME) else name

        deepseek_model = DeepSeekModel(
            model=clean_name,
            api_key=self.api_key,
            registry=ai,
            **self.deepseek_params,
        )
        deepseek_model.define_model()

    @cached_property
    def list_actions(self) -> list[ActionMetadata]:
        """Generate a list of available DeepSeek models.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects for each
                supported DeepSeek model, including name, metadata, and config schema.
        """
        actions_list = []
        for model, model_info in SUPPORTED_DEEPSEEK_MODELS.items():
            actions_list.append(
                model_action_metadata(
                    name=deepseek_name(model), info=model_info.model_dump(), config_schema=OpenAIConfig
                )
            )

        return actions_list
