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

"""DeepSeek model integration for Genkit."""

from collections.abc import Callable
from typing import Any

from genkit.ai import GenkitRegistry
from genkit.plugins.compat_oai.models.model import OpenAIModel
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.plugins.deepseek.client import DeepSeekClient
from genkit.plugins.deepseek.model_info import (
    SUPPORTED_DEEPSEEK_MODELS,
    get_default_model_info,
)

DEEPSEEK_PLUGIN_NAME = 'deepseek'


def deepseek_name(name: str) -> str:
    """Create a DeepSeek action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified DeepSeek action name.
    """
    return f'{DEEPSEEK_PLUGIN_NAME}/{name}'


class DeepSeekModel:
    """Manages DeepSeek model integration for Genkit.

    This class provides integration with DeepSeek's OpenAI-compatible API,
    allowing DeepSeek models to be exposed as Genkit models. It handles
    client initialization, model information retrieval, and dynamic model
    definition within the Genkit registry.

    Follows the Model Garden pattern for implementation consistency.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        registry: GenkitRegistry,
        **deepseek_params,
    ) -> None:
        """Initialize the DeepSeek instance.

        Args:
            model: The name of the specific DeepSeek model (e.g., 'deepseek-chat').
            api_key: DeepSeek API key for authentication.
            registry: An instance of GenkitRegistry to register the model.
            **deepseek_params: Additional parameters for the DeepSeek client.
        """
        self.name = model
        self.ai = registry
        client_params = {'api_key': api_key, **deepseek_params}
        self.client = DeepSeekClient(**client_params)

    def get_model_info(self) -> dict[str, Any] | None:
        """Retrieve metadata and supported features for the specified model.

        This method looks up the model's information from a predefined list
        of supported DeepSeek models or provides default information.

        Returns:
            A dictionary containing the model's 'name' and 'supports' features.
            The 'supports' key contains a dictionary representing the model's
            capabilities (e.g., tools, streaming).
        """
        model_info = SUPPORTED_DEEPSEEK_MODELS.get(self.name, get_default_model_info(self.name))
        return {
            'name': model_info.label,
            'supports': model_info.supports.model_dump(),
        }

    def to_deepseek_model(self) -> Callable:
        """Convert the DeepSeek model into a Genkit-compatible model function.

        This method wraps the underlying DeepSeek client and its generation
        logic into a callable that adheres to the OpenAI model interface
        expected by Genkit.

        Returns:
            A callable function (the generate method of an OpenAIModel instance)
            that can be used by Genkit.
        """
        deepseek_model = OpenAIModel(self.name, self.client, self.ai)
        return deepseek_model.generate

    def define_model(self) -> None:
        """Define and register the DeepSeek model with the Genkit registry.

        This method orchestrates the retrieval of model metadata and the
        creation of the generation function, then registers this model
        within the Genkit framework using self.ai.define_model.
        """
        model_info = self.get_model_info()
        generate_fn = self.to_deepseek_model()
        self.ai.define_model(
            name=deepseek_name(self.name),
            fn=generate_fn,
            config_schema=OpenAIConfig,
            metadata={
                'model': model_info,
            },
        )
