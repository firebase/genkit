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

"""DeepSeek model information and metadata."""

from genkit.types import ModelInfo, Supports

__all__ = ['SUPPORTED_DEEPSEEK_MODELS', 'get_default_model_info']

# Model capabilities matching JS implementation
_DEEPSEEK_SUPPORTS = Supports(
    multiturn=True,
    tools=True,
    media=False,
    system_role=True,
    output=['text', 'json'],
)

SUPPORTED_DEEPSEEK_MODELS: dict[str, ModelInfo] = {
    'deepseek-reasoner': ModelInfo(
        label='DeepSeek - Reasoner',
        versions=['deepseek-reasoner'],
        supports=_DEEPSEEK_SUPPORTS,
    ),
    'deepseek-chat': ModelInfo(
        label='DeepSeek - Chat',
        versions=['deepseek-chat'],
        supports=_DEEPSEEK_SUPPORTS,
    ),
}


def get_default_model_info(name: str) -> ModelInfo:
    """Get default model information for unknown DeepSeek models.

    Args:
        name: Model name.

    Returns:
        Default ModelInfo with standard DeepSeek capabilities.
    """
    return ModelInfo(
        label=f'DeepSeek - {name}',
        supports=_DEEPSEEK_SUPPORTS,
    )
