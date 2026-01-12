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

import os

from anthropic import AsyncAnthropic
from genkit.ai import Plugin
from genkit.blocks.model import model
from genkit.core.action import Action, ActionMetadata
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
    Can be used standalone (without framework) or with Genkit framework.

    Example (standalone):
        >>> plugin = Anthropic(api_key='...')
        >>> claude = await plugin.model('claude-3-5-sonnet')
        >>> response = await claude.arun({'messages': [...]})

    Example (with framework):
        >>> ai = Genkit(plugins=[Anthropic(api_key='...')])
        >>> response = await ai.generate('anthropic/claude-3-5-sonnet', prompt='Hi')
    """

    name = ANTHROPIC_PLUGIN_NAME

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        **anthropic_params: str,
    ) -> None:
        """Initializes Anthropic plugin with given configuration.

        Args:
            api_key: Optional Anthropic API key. If not provided, uses `ANTHROPIC_API_KEY`
                from the environment (or lets the Anthropic client handle defaults).
            models: Optional list of supported Anthropic models to expose via this plugin.
            **anthropic_params: Additional parameters passed to the AsyncAnthropic client.
                This may include api_key, base_url, timeout, and other configuration
                settings required by Anthropic's API.
        """
        if api_key is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')

        self.models = models or list(SUPPORTED_ANTHROPIC_MODELS.keys())
        self._anthropic_params = anthropic_params
        self._anthropic_client = (
            AsyncAnthropic(api_key=api_key, **anthropic_params) if api_key else AsyncAnthropic(**anthropic_params)
        )

    async def init(self) -> list[Action]:
        """Return eagerly-initialized model actions.

        Called once during Genkit initialization. Loads ALL supported
        Anthropic models (same behavior as JavaScript).

        Returns:
            List of Action objects for all supported models.
        """
        return [self._create_model_action(model_name) for model_name in self.models]

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve a specific model action on-demand.

        Called when framework needs an action not from init().
        Enables lazy loading of Anthropic models.

        Args:
            action_type: Type of action requested.
            name: Name of action (unprefixed - framework strips plugin prefix).

        Returns:
            Action if this plugin can provide it, None otherwise.
        """
        if action_type == ActionKind.MODEL:
            # Check if we support this model
            if name in self.models:
                return self._create_model_action(name)

        return None

    async def list_actions(self) -> list[ActionMetadata]:
        """Return metadata for all supported Anthropic models.

        Used for discovery and developer tools.

        Returns:
            List of ActionMetadata for all supported models.
        """
        return [
            ActionMetadata(
                name=model_name,
                kind=ActionKind.MODEL,
                info=get_model_info(model_name).model_dump(),
            )
            for model_name in self.models
        ]

    def _create_model_action(self, model_name: str) -> Action:
        """Create an Action for an Anthropic model (doesn't register).

        Args:
            model_name: Name of the Anthropic model (without plugin prefix).

        Returns:
            Action instance.
        """
        model_info = get_model_info(model_name)
        anthropic_model = AnthropicModel(model_name=model_name, client=self._anthropic_client)

        metadata = {'model': {'supports': model_info.supports.model_dump()}}

        return model(
            name=model_name,
            fn=anthropic_model.generate,
            config_schema=GenerationCommonConfig,
            metadata=metadata,
        )
