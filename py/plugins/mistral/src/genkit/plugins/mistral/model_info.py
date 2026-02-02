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

"""Mistral AI model information and metadata.

This module contains metadata for all supported Mistral AI models,
including capabilities and version information.

See: https://docs.mistral.ai/getting-started/models/models_overview/
"""

from genkit.types import ModelInfo, Supports

__all__ = ['SUPPORTED_MISTRAL_MODELS', 'get_default_model_info']

# Standard text model capabilities
_TEXT_MODEL_SUPPORTS = Supports(
    multiturn=True,
    tools=True,
    media=False,
    system_role=True,
    output=['text', 'json'],
)

# Vision model capabilities (Pixtral)
_VISION_MODEL_SUPPORTS = Supports(
    multiturn=True,
    tools=True,
    media=True,
    system_role=True,
    output=['text', 'json'],
)

# Code model capabilities (Codestral)
_CODE_MODEL_SUPPORTS = Supports(
    multiturn=True,
    tools=True,  # Codestral supports function calling
    media=False,
    system_role=True,
    output=['text', 'json'],
)

# Embedding model capabilities
_EMBEDDING_SUPPORTS = Supports(
    multiturn=False,
    tools=False,
    media=False,
    system_role=False,
    output=['text'],
)

SUPPORTED_MISTRAL_MODELS: dict[str, ModelInfo] = {
    # Premier Models
    'mistral-large-latest': ModelInfo(
        label='Mistral AI - Large (Latest)',
        versions=['mistral-large-latest', 'mistral-large-2411'],
        supports=_TEXT_MODEL_SUPPORTS,
    ),
    'mistral-small-latest': ModelInfo(
        label='Mistral AI - Small (Latest)',
        versions=['mistral-small-latest', 'mistral-small-2503'],
        supports=_TEXT_MODEL_SUPPORTS,
    ),
    'codestral-latest': ModelInfo(
        label='Mistral AI - Codestral (Latest)',
        versions=['codestral-latest', 'codestral-2501'],
        supports=_CODE_MODEL_SUPPORTS,
    ),
    'mistral-embed': ModelInfo(
        label='Mistral AI - Embed',
        versions=['mistral-embed'],
        supports=_EMBEDDING_SUPPORTS,
    ),
    # Vision Models
    'pixtral-large-latest': ModelInfo(
        label='Mistral AI - Pixtral Large (Vision)',
        versions=['pixtral-large-latest', 'pixtral-large-2411'],
        supports=_VISION_MODEL_SUPPORTS,
    ),
    'pixtral-12b-latest': ModelInfo(
        label='Mistral AI - Pixtral 12B (Vision)',
        versions=['pixtral-12b-latest', 'pixtral-12b-2409'],
        supports=_VISION_MODEL_SUPPORTS,
    ),
    # Ministral Models (Compact)
    'ministral-8b-latest': ModelInfo(
        label='Mistral AI - Ministral 8B',
        versions=['ministral-8b-latest', 'ministral-8b-2410'],
        supports=_TEXT_MODEL_SUPPORTS,
    ),
    'ministral-3b-latest': ModelInfo(
        label='Mistral AI - Ministral 3B',
        versions=['ministral-3b-latest', 'ministral-3b-2410'],
        supports=_TEXT_MODEL_SUPPORTS,
    ),
    # Research/Preview Models
    'mistral-saba-latest': ModelInfo(
        label='Mistral AI - Saba (Latest)',
        versions=['mistral-saba-latest'],
        supports=_TEXT_MODEL_SUPPORTS,
    ),
    # Legacy Models (still supported)
    'open-mistral-nemo': ModelInfo(
        label='Mistral AI - Nemo (Open)',
        versions=['open-mistral-nemo', 'open-mistral-nemo-2407'],
        supports=_TEXT_MODEL_SUPPORTS,
    ),
    'open-codestral-mamba': ModelInfo(
        label='Mistral AI - Codestral Mamba (Open)',
        versions=['open-codestral-mamba'],
        supports=_CODE_MODEL_SUPPORTS,
    ),
}


def get_default_model_info(name: str) -> ModelInfo:
    """Get default model information for unknown Mistral models.

    Args:
        name: Model name.

    Returns:
        Default ModelInfo with standard Mistral capabilities.
    """
    return ModelInfo(
        label=f'Mistral AI - {name}',
        supports=_TEXT_MODEL_SUPPORTS,
    )
