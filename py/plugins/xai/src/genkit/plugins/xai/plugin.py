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

"""xAI plugin for Genkit."""

import os

from xai_sdk import Client as XAIClient

from genkit.ai import GenkitRegistry, Plugin
from genkit.core.error import GenkitError
from genkit.core.registry import ActionKind
from genkit.plugins.xai.model_info import SUPPORTED_XAI_MODELS, get_model_info
from genkit.plugins.xai.models import XAIModel
from genkit.types import GenerationCommonConfig

__all__ = ['XAI', 'xai_name']

XAI_PLUGIN_NAME = 'xai'


def xai_name(name: str) -> str:
    return f'{XAI_PLUGIN_NAME}/{name}'


class XAI(Plugin):
    """xAI plugin for Genkit."""

    name = XAI_PLUGIN_NAME

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        **xai_params: str,
    ) -> None:
        api_key = api_key or os.getenv('XAI_API_KEY')

        if not api_key:
            raise GenkitError(message='Please provide api_key or set XAI_API_KEY environment variable.')

        self.models = models or list(SUPPORTED_XAI_MODELS.keys())
        self._xai_params = xai_params
        self._xai_client = XAIClient(api_key=api_key, **xai_params)

    def initialize(self, ai: GenkitRegistry) -> None:
        for model_name in self.models:
            self._define_model(ai, model_name)

    def resolve_action(
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        if kind == ActionKind.MODEL:
            self._resolve_model(ai=ai, name=name)

    def _resolve_model(self, ai: GenkitRegistry, name: str) -> None:
        clean_name = name.replace(f'{XAI_PLUGIN_NAME}/', '') if name.startswith(XAI_PLUGIN_NAME) else name
        self._define_model(ai, clean_name)

    def _define_model(self, ai: GenkitRegistry, model_name: str) -> None:
        model = XAIModel(model_name=model_name, client=self._xai_client)
        model_info = get_model_info(model_name)

        ai.define_model(
            name=xai_name(model_name),
            fn=model.generate,
            config_schema=GenerationCommonConfig,
            metadata={'model': {'supports': model_info.supports.model_dump()}},
        )
