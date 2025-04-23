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

from genkit.ai import GenkitRegistry
from genkit.plugins.compat_oai.models import (
    SUPPORTED_OPENAI_COMPAT_MODELS,
    OpenAIModelHandler,
    PluginSource,
)
from genkit.plugins.compat_oai.models.model_info import PluginSource
from genkit.plugins.compat_oai.typing import OpenAIConfig

from .client import OpenAIClient

OPENAI_COMPAT = 'openai-compat'


def model_garden_name(name: str) -> str:
    """Create a Model Garden action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Model Garden action name.
    """
    return f'modelgarden/{name}'


class ModelGarden:
    @staticmethod
    def get_model_info(name: str) -> dict[str, str] | None:
        """Returns model type and name for a given model.

        Args:
            name: Name of the model for which type and name are to be returned

        """
        if SUPPORTED_OPENAI_COMPAT_MODELS.get(name):
            return {'name': SUPPORTED_OPENAI_COMPAT_MODELS.get(name).label, 'type': OPENAI_COMPAT}

    @classmethod
    def to_openai_compatible_model(cls, ai: GenkitRegistry, model: str, location: str, project_id: str):
        if model not in SUPPORTED_OPENAI_COMPAT_MODELS:
            raise ValueError(f"Model '{model}' is not supported.")
        openai_params = {'location': location, 'project_id': project_id}
        openai_client = OpenAIClient(**openai_params)
        handler = OpenAIModelHandler.get_model_handler(
            model=model, client=openai_client, registry=ai, source=PluginSource.MODEL_GARDEN
        )

        supports = SUPPORTED_OPENAI_COMPAT_MODELS[model].supports.model_dump()

        ai.define_model(
            name=model_garden_name(model),
            fn=handler,
            config_schema=OpenAIConfig,
            metadata={'model': {'supports': supports}},
        )
