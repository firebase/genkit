# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI OpenAI API Compatible Plugin for Genkit.
"""

from genkit.plugins.compat_oai.models import (
    SUPPORTED_OPENAI_MODELS,
    OpenAIModelHandler,
)
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.veneer.plugin import Plugin
from genkit.veneer.registry import GenkitRegistry
from openai import OpenAI as OpenAIClient


class OpenAI(Plugin):
    """
    A plugin for integrating OpenAI compatible models with the Genkit framework.

    This class registers OpenAI model handlers within a registry, allowing
    interaction with supported OpenAI models.
    """

    name = 'openai-compat'

    def __init__(self, **openai_params):
        """
        Initializes the OpenAI plugin with the specified parameters.

        :param openai_params: Additional parameters that will be passed to the OpenAI client constructor.
                              These parameters may include API keys, timeouts, organization IDs, and
                              other configuration settings required by OpenAI's API.
        """
        self._openai_params = openai_params
        self._openai_client = OpenAIClient(**openai_params)

    def initialize(self, ai: GenkitRegistry) -> None:
        """
        Registers supported OpenAI models in the given registry.

        :param registry: The registry where OpenAI models will be registered.
        """
        for model_name, model_info in SUPPORTED_OPENAI_MODELS.items():
            handler = OpenAIModelHandler.get_model_handler(
                model=model_name, client=self._openai_client
            )

            ai.define_model(
                name=f'openai/{model_name}',
                fn=handler,
                config_schema=OpenAIConfig,
                metadata={
                    'model': {
                        'label': model_info.label,
                        'supports': {
                            'multiturn': model_info.supports.multiturn
                        },
                    },
                },
            )


def openai_model(name: str) -> str:
    """
    Returns a string representing the OpenAI model name to use with Genkit.
    """
    return f'openai/{name}'


__all__ = ['OpenAI', 'openai_model']
