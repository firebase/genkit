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

"""xAI model information."""

from genkit.types import ModelInfo, Supports

__all__ = ['SUPPORTED_XAI_MODELS', 'get_model_info']

_LANGUAGE_MODEL_SUPPORTS = Supports(
    multiturn=True,
    tools=True,
    media=False,
    system_role=True,
    output=['text', 'json'],
)

_VISION_MODEL_SUPPORTS = Supports(
    multiturn=False,
    tools=True,
    media=True,
    system_role=False,
    output=['text', 'json'],
)

SUPPORTED_XAI_MODELS: dict[str, ModelInfo] = {
    'grok-3': ModelInfo(
        label='xAI - Grok 3',
        versions=['grok-3'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-3-fast': ModelInfo(
        label='xAI - Grok 3 Fast',
        versions=['grok-3-fast'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-3-mini': ModelInfo(
        label='xAI - Grok 3 Mini',
        versions=['grok-3-mini'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-3-mini-fast': ModelInfo(
        label='xAI - Grok 3 Mini Fast',
        versions=['grok-3-mini-fast'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-2-vision-1212': ModelInfo(
        label='xAI - Grok 2 Vision',
        versions=['grok-2-vision-1212'],
        supports=_VISION_MODEL_SUPPORTS,
    ),
    'grok-4': ModelInfo(
        label='xAI - Grok 4',
        versions=['grok-4'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-4.1': ModelInfo(
        label='xAI - Grok 4.1',
        versions=['grok-4.1'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-2-1212': ModelInfo(
        label='xAI - Grok 2',
        versions=['grok-2-1212'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
    'grok-2-latest': ModelInfo(
        label='xAI - Grok 2 Latest',
        versions=['grok-2-latest'],
        supports=_LANGUAGE_MODEL_SUPPORTS,
    ),
}


def get_model_info(name: str) -> ModelInfo:
    """Get information for a specific model."""
    return SUPPORTED_XAI_MODELS.get(
        name,
        ModelInfo(
            label=f'xAI - {name}',
            supports=_LANGUAGE_MODEL_SUPPORTS,
        ),
    )
