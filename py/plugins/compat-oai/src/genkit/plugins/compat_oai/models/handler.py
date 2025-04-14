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


"""OpenAI Compatible Model handlers for Genkit."""

from collections.abc import Callable
from typing import Any

from openai import OpenAI

from genkit.ai import ActionRunContext, GenkitRegistry
from genkit.plugins.compat_oai.models.model import OpenAIModel
from genkit.plugins.compat_oai.models.model_info import (
    SUPPORTED_OPENAI_MODELS,
)
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
)


class OpenAIModelHandler:
    """Handles OpenAI API interactions for the Genkit plugin."""

    def __init__(self, model: Any) -> None:
        """Initializes the OpenAIModelHandler with a specified model.

        Args:
            model: An instance of a Model subclass representing the OpenAI model.
        """
        self._model = model

    @classmethod
    def get_model_handler(
        cls, model: str, client: OpenAI, registry: GenkitRegistry
    ) -> Callable[[GenerateRequest, ActionRunContext], GenerateResponse]:
        """Factory method to initialize the model handler for the specified OpenAI model.

        OpenAI models in this context are not instantiated as traditional
        classes but rather as Actions. This method returns a callable that
        serves as an action handler, conforming to the structure of:

            Action[GenerateRequest, GenerateResponse, GenerateResponseChunk]

        Args:
            model: The OpenAI model name.
            client: OpenAI client instance.
            registry: Genkit registry instance.

        Returns:
            A callable function that acts as an action handler.

        Raises:
            ValueError: If the specified model is not supported.
        """
        if model not in SUPPORTED_OPENAI_MODELS:
            raise ValueError(f"Model '{model}' is not supported.")

        openai_model = OpenAIModel(model, client, registry)
        return cls(openai_model).generate

    def _validate_version(self, version: str) -> None:
        """Validates whether the specified model version is supported.

        Args:
            version: The version of the model to be validated.

        Raises:
            ValueError: If the specified model version is not supported.
        """
        model_info = SUPPORTED_OPENAI_MODELS[self._model.name]
        if version not in model_info.versions:
            raise ValueError(f"Model version '{version}' is not supported.")

    def _normalize_config(self, config: Any) -> OpenAIConfig:
        """Ensures the config is an OpenAIConfig instance."""
        if isinstance(config, OpenAIConfig):
            return config

        if isinstance(config, dict):
            return OpenAIConfig(**config)

        raise ValueError(f'Expected request.config to be a dict or OpenAIConfig, got {type(config).__name__}.')

    def generate(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Processes the request using OpenAI's chat completion API.

        Args:
            request: The request containing messages and configurations.
            ctx: The context of the action run.

        Returns:
            A GenerateResponse containing the model's response.

        Raises:
            ValueError: If the specified model version is not supported.
        """
        request.config = self._normalize_config(request.config)

        if request.config.model:
            self._validate_version(request.config.model)

        if ctx.is_streaming:
            return self._model.generate_stream(request, ctx.send_chunk)
        else:
            return self._model.generate(request)
