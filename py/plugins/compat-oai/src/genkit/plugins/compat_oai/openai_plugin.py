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


"""OpenAI OpenAI API Compatible Plugin for Genkit."""
from typing import Any

from openai import Client, OpenAI as OpenAIClient

from genkit.ai._plugin import Plugin
from genkit.ai._registry import GenkitRegistry
from genkit.core.action.types import ActionKind
from genkit.plugins.compat_oai.models import (
    SUPPORTED_OPENAI_MODELS,
    OpenAIModel,
    OpenAIModelHandler,
)
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.plugins.ollama.models import ModelDefinition

OPENAI_PLUGIN_NAME = 'openai'

def default_openai_metadata(name: str) -> dict[str, Any]:
    return {
                'model': {
                    'label': f"OpenAI - {name}",
                    'supports': {'multiturn': True}
                },
            }


class OpenAI(Plugin):
    """A plugin for integrating OpenAI compatible models with the Genkit framework.

    This class registers OpenAI model handlers within a registry, allowing
    interaction with supported OpenAI models.
    """

    name = 'openai-compat'

    def __init__(self, **openai_params: str) -> None:
        """Initializes the OpenAI plugin with the specified parameters.

        Args:
            openai_params: Additional parameters that will be passed to the OpenAI client constructor.
                           These parameters may include API keys, timeouts, organization IDs, and
                           other configuration settings required by OpenAI's API.
        """
        self._openai_params = openai_params
        self._openai_client = OpenAIClient(**openai_params)

    def initialize(self, ai: GenkitRegistry) -> None:
        """Registers supported OpenAI models in the given registry.

        Args:
            ai: The registry where OpenAI models will be registered.
        """
        for model_name, model_info in SUPPORTED_OPENAI_MODELS.items():
            handler = OpenAIModelHandler.get_model_handler(model=model_name, client=self._openai_client, registry=ai)

            ai.define_model(
                name=f'openai/{model_name}',
                fn=handler,
                config_schema=OpenAIConfig,
                metadata={
                    'model': {
                        'label': model_info.label,
                        'supports': {'multiturn': model_info.supports.multiturn} if model_info.supports else {},
                    },
                },
            )

    def resolve_action(  # noqa: B027
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:

        if kind is not ActionKind.MODEL:
            return None

        self._define_openai_model(ai, name)
        return None

    def _define_openai_model(self, ai: GenkitRegistry, name: str) -> None:
        """Defines and registers an OpenAI model with Genkit.

        Cleans the model name, instantiates an OpenAI, and registers it
        with the provided Genkit AI registry, including metadata about its capabilities.

        Args:
            ai: The Genkit AI registry instance.
            name: The name of the model to be registered.
        """

        handler = OpenAIModelHandler(OpenAIModel(name, self._openai_client, ai)).generate
        ai.define_model(
            name=f'openai/{name}',
            fn=handler,
            config_schema=OpenAIConfig,
            metadata=default_openai_metadata(name)
        )




def openai_model(name: str) -> str:
    """Returns a string representing the OpenAI model name to use with Genkit.

    Args:
        name: The name of the OpenAI model to use.

    Returns:
        A string representing the OpenAI model name to use with Genkit.
    """
    return f'openai/{name}'


__all__ = ['OpenAI', 'openai_model']
