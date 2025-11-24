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


"""OpenAI Compatible Models for Genkit."""

import sys

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

from genkit.plugins.compat_oai.typing import SupportedOutputFormat
from genkit.types import (
    ModelInfo,
    Supports,
)

OPENAI = 'openai'
MODEL_GARDEN = 'model-garden'


class PluginSource(StrEnum):
    OPENAI = 'openai'
    MODEL_GARDEN = 'model-garden'


GPT_3_5_TURBO = 'gpt-3.5-turbo'
GPT_4 = 'gpt-4'
GPT_4_TURBO = 'gpt-4-turbo'
GPT_4O = 'gpt-4o'
GPT_4O_MINI = 'gpt-4o-mini'
O1_MINI = 'o1-mini'

LLAMA_3_1 = 'meta/llama-3.1-405b-instruct-maas'
LLAMA_3_2 = 'meta/llama-3.2-90b-vision-instruct-maas'

SUPPORTED_OPENAI_MODELS: dict[str, ModelInfo] = {
    GPT_3_5_TURBO: ModelInfo(
        label='OpenAI - gpt-3.5-turbo',
        versions=[
            'gpt-3.5-turbo-1106',
            'gpt-3.5-turbo-0125',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
        ),
    ),
    GPT_4O: ModelInfo(
        label='OpenAI - gpt-4o',
        versions=[
            'gpt-4o-2024-11-20',
            'gpt-4o-2024-08-06',
            'gpt-4o-2024-05-13',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[
                SupportedOutputFormat.JSON_MODE,
                SupportedOutputFormat.STRUCTURED_OUTPUTS,
                SupportedOutputFormat.TEXT,
            ],
        ),
    ),
    GPT_4O_MINI: ModelInfo(
        label='OpenAI - gpt-4o-mini',
        versions=[
            'gpt-4o-mini-2024-07-18',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[
                SupportedOutputFormat.JSON_MODE,
                SupportedOutputFormat.STRUCTURED_OUTPUTS,
                SupportedOutputFormat.TEXT,
            ],
        ),
    ),
    O1_MINI: ModelInfo(
        label='OpenAI - o1-mini',
        versions=[
            'o1-mini-2024-09-12',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
        ),
    ),
    GPT_4: ModelInfo(
        label='OpenAI - GPT-4',
        versions=[
            'gpt-4-0613',
            'gpt-4-1106-preview',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
        ),
    ),
    GPT_4_TURBO: ModelInfo(
        label='OpenAI - GPT-4 Turbo',
        versions=[
            'gpt-4-turbo-2024-04-09',
            'gpt-4-turbo-preview',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
        ),
    ),
}

SUPPORTED_OPENAI_COMPAT_MODELS: dict[str, ModelInfo] = {
    LLAMA_3_1: ModelInfo(
        label='ModelGarden - Meta - llama-3.1',
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            longRunning=False,
            output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
        ),
    ),
    LLAMA_3_2: ModelInfo(
        label='ModelGarden - Meta - llama-3.2',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
        ),
    ),
}


DEFAULT_SUPPORTS = Supports(
    multiturn=True,
    media=True,
    tools=True,
    systemRole=True,
    output=[SupportedOutputFormat.JSON_MODE, SupportedOutputFormat.TEXT],
)


def get_default_model_info(name: str) -> ModelInfo:
    """Gets the default model info given a name."""
    return ModelInfo(
        label=f'ModelGarden - {name}',
        supports=DEFAULT_SUPPORTS,
    )


def get_default_openai_model_info(name: str) -> ModelInfo:
    """Gets the default model info given a name."""
    return ModelInfo(label=f'OpenAI - {name}', supports={'multiturn': True})
