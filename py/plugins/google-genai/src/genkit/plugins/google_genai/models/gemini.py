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

"""Gemini models for use with Genkit.

# Naming convention
Gemini models follow the following naming conventions:

                             +------- Tier/Variant (e.g., pro, flash)
                             |      +---------- Modifier (Optional, e.g., exp)
                             |      |         +--- Date/Snapshot ID (Optional)
                             v      v         v
        gemini - <VER> - <TIER> [-MOD] [-DATE]
          ^        ^           ^
          |        |           |
(Family)--+        |           +-- Size Specifier (Optional, e.g., -8b,
          |        |               often follows TIER like 'flash')
          |        |
          +--------+---------- Version (Major generation, e.g., 1.0, 1.5, 2.0)


## Examples

gemini - 1.5 - flash - 8b
  ^      ^      ^      ^
  |      |      |      +-- Size Specifier
  |      |      +--------- Tier/Variant
  |      +----------------- Version
  +------------------------ Family

gemini - 2.0 - pro - exp - 02-05
  ^      ^      ^     ^      ^
  |      |      |     |      +-- Date/Snapshot ID
  |      |      |     +--------- Modifier
  |      |      +---------------- Tier/Variant
  |      +------------------------ Version
  +------------------------------- Family

## Terminology

Family (`gemini`)
: The base name identifying the overarching group or brand of related AI models
  developed by Google (e.g., Gemini).

Version Number (e.g., `1.0`, `1.5`, `2.0`, `2.5`)
: Indicates the major generation or release cycle of the model within the
  family. Higher numbers typically denote newer iterations, often incorporating
  significant improvements, architectural changes, or new capabilities compared
  to previous versions.

Tier / Variant (e.g., `pro`, `flash`)
: Distinguishes models within the same generation based on specific
  characteristics like performance profile, size, speed, efficiency, or intended
  primary use case.

  * **`pro`**: Generally indicates a high-capability, powerful, and versatile
    model within its generation, suitable for a wide range of complex tasks.

  * **`flash`**: Often signifies a model optimized for speed, latency, and
    cost-efficiency, potentially offering a different balance of performance
    characteristics compared to the `pro` variant.

Size Specifier (e.g., `8b`)
: An optional component, frequently appended to a Tier/Variant (like `flash`),
  providing more specific detail about the model's scale. This often relates to
  the approximate number of parameters (e.g., `8b` likely suggests 8 billion
  parameters), influencing its performance and resource requirements.

Modifier (e.g., `exp`)
: An optional flag indicating the model's release status, stability, or intended
  audience.

  * **`exp`**: Stands for "Experimental". Models marked with `exp` are typically
    previews or early releases. They are subject to change, updates, or removal
    without the standard notice periods applied to stable models, and they lack
    long-term stability guarantees, making them generally unsuitable for
    production systems requiring stability.

Date / Snapshot ID (e.g., `02-05`, `03-25`)
: An optional identifier, commonly seen with experimental (`exp`) models. It
  likely represents a specific build date (often in MM-DD format) or a unique
  snapshot identifier, helping to distinguish between different iterations or
  releases within the experimental track.

# Model support

The following models are currently supported by GoogleAI API:

| Model                                | Description                          | Status     |
|--------------------------------------|--------------------------------------|------------|
| `gemini-1.5-pro`                     | Gemini 1.5 Pro                       | Deprecated |
| `gemini-1.5-flash`                   | Gemini 1.5 Flash                     | Deprecated |
| `gemini-1.5-flash-8b`                | Gemini 1.5 Flash 8B                  | Deprecated |
| `gemini-2.0-flash`                   | Gemini 2.0 Flash                     | Supported  |
| `gemini-2.0-flash-lite`              | Gemini 2.0 Flash Lite                | Supported  |
| `gemini-2.0-pro-exp-02-05`           | Gemini 2.0 Pro Exp 02-05             | Supported  |
| `gemini-2.5-pro-exp-03-25`           | Gemini 2.5 Pro Exp 03-25             | Supported  |
| `gemini-2.0-flash-exp`               | Gemini 2.0 Flash Experimental        | Supported  |
| `gemini-2.0-flash-thinking-exp-01-21`| Gemini 2.0 Flash Thinking Exp 01-21  | Supported  |
| `gemini-2.5-pro-preview-03-25`       | Gemini 2.5 Pro Preview 03-25         | Supported  |
| `gemini-2.5-pro-preview-05-06`       | Gemini 2.5 Pro Preview 05-06         | Supported  |


The following models are currently supported by VertexAI API:

| Model                                | Description                          | Status       |
|--------------------------------------|--------------------------------------|--------------|
| `gemini-1.5-pro`                     | Gemini 1.5 Pro                       | Deprecated   |
| `gemini-1.5-flash`                   | Gemini 1.5 Flash                     | Deprecated   |
| `gemini-1.5-flash-8b`                | Gemini 1.5 Flash 8B                  | Deprecated   |
| `gemini-2.0-flash`                   | Gemini 2.0 Flash                     | Supported    |
| `gemini-2.0-flash-lite`              | Gemini 2.0 Flash Lite                | Supported    |
| `gemini-2.0-pro-exp-02-05`           | Gemini 2.0 Pro Exp 02-05             | Supported    |
| `gemini-2.5-pro-exp-03-25`           | Gemini 2.5 Pro Exp 03-25             | Supported    |
| `gemini-2.0-flash-exp`               | Gemini 2.0 Flash Experimental        | Unavailable  |
| `gemini-2.0-flash-thinking-exp-01-21`| Gemini 2.0 Flash Thinking Exp 01-21  | Supported    |
| `gemini-2.5-pro-preview-03-25`       | Gemini 2.5 Pro Preview 03-25         | Supported    |
| `gemini-2.5-pro-preview-05-06`       | Gemini 2.5 Pro Preview 05-06         | Supported  |
"""

import sys  # noqa
from datetime import datetime, timezone, timedelta

from genkit.plugins.google_genai.models.context_caching.constants import DEFAULT_TTL
from genkit.plugins.google_genai.models.context_caching.utils import generate_cache_key, validate_context_cache_request

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from functools import cached_property
from typing import Any

from google import genai
from google.genai import types as genai_types  # type: ignore

from genkit.ai import (
    ActionKind,
    ActionRunContext,
    GenkitRegistry,
)
from genkit.blocks.model import get_basic_usage_stats
from genkit.codec import dump_dict, dump_json
from genkit.core.tracing import tracer
from genkit.lang.deprecations import (
    DeprecationInfo,
    DeprecationStatus,
    deprecated_enum_metafactory,
)
from genkit.plugins.google_genai.models.utils import PartConverter
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    GenerationUsage,
    Message,
    ModelInfo,
    Role,
    Stage,
    Supports,
    ToolDefinition,
)


class GeminiConfigSchema(genai_types.GenerateContentConfig):
    """Gemini Config Schema."""

    code_execution: bool | None = None
    response_modalities: list[str] | None = None


class GeminiTtsConfigSchema(GeminiConfigSchema):
    """Gemini TTS Config Schema."""

    speech_config: dict[str, Any] | None = None


class GeminiImageConfigSchema(GeminiConfigSchema):
    """Gemini Image Config Schema."""

    image_config: dict[str, Any] | None = None


class GemmaConfigSchema(GeminiConfigSchema):
    """Gemma Config Schema."""

    temperature: float | None = None


GEMINI_1_5_PRO = ModelInfo(
    label='Google AI - Gemini 1.5 Pro',
    stage=Stage.DEPRECATED,
    versions=[
        'gemini-1.5-pro-latest',
        'gemini-1.5-pro-001',
        'gemini-1.5-pro-002',
    ],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_1_5_FLASH = ModelInfo(
    label='Google AI - Gemini 1.5 Flash',
    stage=Stage.DEPRECATED,
    versions=[
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash-001',
        'gemini-1.5-flash-002',
    ],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_1_5_FLASH_8B = ModelInfo(
    label='Google AI - Gemini 1.5 Flash',
    stage=Stage.DEPRECATED,
    versions=['gemini-1.5-flash-8b-latest', 'gemini-1.5-flash-8b-001'],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_0_FLASH = ModelInfo(
    label='Google AI - Gemini 2.0 Flash',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_0_FLASH_LITE = ModelInfo(
    label='Google AI - Gemini 2.0 Flash Lite',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_0_PRO_EXP_02_05 = ModelInfo(
    label='Google AI - Gemini 2.0 Pro Exp 02-05',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_0_FLASH_EXP_IMAGEN = ModelInfo(
    label='Google AI - Gemini 2.0 Flash Experimental',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_0_FLASH_THINKING_EXP_01_21 = ModelInfo(
    label='Google AI - Gemini 2.0 Flash Thinking Exp 01-21',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_5_PRO_EXP_03_25 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Exp 03-25',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_5_PRO_PREVIEW_03_25 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Preview 03-25',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_5_PRO_PREVIEW_05_06 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Preview 05-06',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_5_FLASH_PREVIEW_04_17 = ModelInfo(
    label='Google AI - Gemini 2.5 Flash Preview 04-17',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GENERIC_GEMINI_MODEL = ModelInfo(
    label='Google AI - Gemini',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
        output=['text', 'json'],
    ),
)

GENERIC_TTS_MODEL = ModelInfo(
    label='Google AI - Gemini TTS',
    supports=Supports(
        multiturn=False,
        media=False,
        tools=False,
        tool_choice=False,
        system_role=False,
        constrained='no-tools',
    ),
)

GENERIC_IMAGE_MODEL = ModelInfo(
    label='Google AI - Gemini Image',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
        output=['text'],
    ),
)

GENERIC_GEMMA_MODEL = ModelInfo(
    label='Google AI - Gemma',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
        output=['text', 'json'],
    ),
)


Deprecations = deprecated_enum_metafactory({
    'GEMINI_1_0_PRO': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_PRO': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_FLASH': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_FLASH_8B': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
})


class VertexAIGeminiVersion(StrEnum, metaclass=Deprecations):
    """VertexAIGemini models.

    Model Support:

    | Model                                | Description                          | Status       |
    |--------------------------------------|--------------------------------------|--------------|
    | `gemini-1.5-flash-8b`                | Gemini 1.5 Flash 8B                  | Deprecated   |
    | `gemini-1.5-flash`                   | Gemini 1.5 Flash                     | Deprecated   |
    | `gemini-1.5-pro`                     | Gemini 1.5 Pro                       | Deprecated   |
    | `gemini-2.0-flash-exp`               | Gemini 2.0 Flash Exp                 | Supported    |
    | `gemini-2.0-flash-lite`              | Gemini 2.0 Flash Lite                | Supported    |
    | `gemini-2.0-flash-thinking-exp-01-21`| Gemini 2.0 Flash Thinking Exp 01-21  | Supported    |
    | `gemini-2.0-flash`                   | Gemini 2.0 Flash                     | Supported    |
    | `gemini-2.0-pro-exp-02-05`           | Gemini 2.0 Pro Exp 02-05             | Supported    |
    | `gemini-2.5-pro-exp-03-25`           | Gemini 2.5 Pro Exp 03-25             | Supported    |
    | `gemini-2.5-pro-preview-03-25`       | Gemini 2.5 Pro Preview 03-25         | Supported    |
    | `gemini-2.5-pro-preview-05-06`       | Gemini 2.5 Pro Preview 05-06         | Supported    |
    | `gemini-3-flash-preview`             | Gemini 3 Flash Preview               | Supported    |
    | `gemini-3-pro-preview`               | Gemini 3 Pro Preview                 | Supported    |
    | `gemini-2.5-pro`                     | Gemini 2.5 Pro                       | Supported    |
    | `gemini-2.5-flash`                   | Gemini 2.5 Flash                     | Supported    |
    | `gemini-2.5-flash-lite`              | Gemini 2.5 Flash Lite                | Supported    |
    | `gemini-2.5-flash-preview-tts`       | Gemini 2.5 Flash Preview TTS         | Supported    |
    | `gemini-2.5-pro-preview-tts`         | Gemini 2.5 Pro Preview TTS           | Supported    |
    | `gemini-3-pro-image-preview`         | Gemini 3 Pro Image Preview           | Supported    |
    | `gemini-2.5-flash-image-preview`     | Gemini 2.5 Flash Image Preview       | Supported    |
    | `gemini-2.5-flash-image`             | Gemini 2.5 Flash Image               | Supported    |
    | `gemma-3-12b-it`                     | Gemma 3 12B IT                       | Supported    |
    | `gemma-3-1b-it`                      | Gemma 3 1B IT                        | Supported    |
    | `gemma-3-27b-it`                     | Gemma 3 27B IT                       | Supported    |
    | `gemma-3-4b-it`                      | Gemma 3 4B IT                        | Supported    |
    | `gemma-3n-e4b-it`                    | Gemma 3n E4B IT                      | Supported    |
    """

    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_FLASH_EXP = 'gemini-2.0-flash-exp'
    GEMINI_2_0_FLASH_LITE = 'gemini-2.0-flash-lite'
    GEMINI_2_0_FLASH_THINKING_EXP_01_21 = 'gemini-2.0-flash-thinking-exp-01-21'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'
    GEMINI_2_5_PRO_EXP_03_25 = 'gemini-2.5-pro-exp-03-25'
    GEMINI_2_5_PRO_PREVIEW_03_25 = 'gemini-2.5-pro-preview-03-25'
    GEMINI_2_5_PRO_PREVIEW_05_06 = 'gemini-2.5-pro-preview-05-06'
    GEMINI_3_FLASH_PREVIEW = 'gemini-3-flash-preview'
    GEMINI_3_PRO_PREVIEW = 'gemini-3-pro-preview'
    GEMINI_2_5_PRO = 'gemini-2.5-pro'
    GEMINI_2_5_FLASH = 'gemini-2.5-flash'
    GEMINI_2_5_FLASH_LITE = 'gemini-2.5-flash-lite'
    GEMINI_2_5_FLASH_PREVIEW_TTS = 'gemini-2.5-flash-preview-tts'
    GEMINI_2_5_PRO_PREVIEW_TTS = 'gemini-2.5-pro-preview-tts'
    GEMINI_3_PRO_IMAGE_PREVIEW = 'gemini-3-pro-image-preview'
    GEMINI_2_5_FLASH_IMAGE_PREVIEW = 'gemini-2.5-flash-image-preview'
    GEMINI_2_5_FLASH_IMAGE = 'gemini-2.5-flash-image'
    GEMMA_3_12B_IT = 'gemma-3-12b-it'
    GEMMA_3_1B_IT = 'gemma-3-1b-it'
    GEMMA_3_27B_IT = 'gemma-3-27b-it'
    GEMMA_3_4B_IT = 'gemma-3-4b-it'
    GEMMA_3N_E4B_IT = 'gemma-3n-e4b-it'


class GoogleAIGeminiVersion(StrEnum, metaclass=Deprecations):
    """GoogleAI Gemini models.

    Model Support:

    | Model                                | Description                          | Status     |
    |--------------------------------------|--------------------------------------|------------|
    | `gemini-1.5-flash-8b`                | Gemini 1.5 Flash 8B                  | Deprecated |
    | `gemini-1.5-flash`                   | Gemini 1.5 Flash                     | Deprecated |
    | `gemini-1.5-pro`                     | Gemini 1.5 Pro                       | Deprecated |
    | `gemini-2.0-flash-exp`               | Gemini 2.0 Flash Exp                 | Supported  |
    | `gemini-2.0-flash-lite`              | Gemini 2.0 Flash Lite                | Supported  |
    | `gemini-2.0-flash-thinking-exp-01-21`| Gemini 2.0 Flash Thinking Exp 01-21  | Supported  |
    | `gemini-2.0-flash`                   | Gemini 2.0 Flash                     | Supported  |
    | `gemini-2.0-pro-exp-02-05`           | Gemini 2.0 Pro Exp 02-05             | Supported  |
    | `gemini-2.5-pro-exp-03-25`           | Gemini 2.5 Pro Exp 03-25             | Supported  |
    | `gemini-2.5-pro-preview-03-25`       | Gemini 2.5 Pro Preview 03-25         | Supported  |
    | `gemini-2.5-pro-preview-05-06`       | Gemini 2.5 Pro Preview 05-06         | Supported  |
    | `gemini-3-flash-preview`             | Gemini 3 Flash Preview               | Supported  |
    | `gemini-3-pro-preview`               | Gemini 3 Pro Preview                 | Supported  |
    | `gemini-2.5-pro`                     | Gemini 2.5 Pro                       | Supported  |
    | `gemini-2.5-flash`                   | Gemini 2.5 Flash                     | Supported  |
    | `gemini-2.5-flash-lite`              | Gemini 2.5 Flash Lite                | Supported  |
    | `gemini-2.5-flash-preview-tts`       | Gemini 2.5 Flash Preview TTS         | Supported  |
    | `gemini-2.5-pro-preview-tts`         | Gemini 2.5 Pro Preview TTS           | Supported  |
    | `gemini-3-pro-image-preview`         | Gemini 3 Pro Image Preview           | Supported  |
    | `gemini-2.5-flash-image-preview`     | Gemini 2.5 Flash Image Preview       | Supported  |
    | `gemini-2.5-flash-image`             | Gemini 2.5 Flash Image               | Supported  |
    | `gemma-3-12b-it`                     | Gemma 3 12B IT                       | Supported  |
    | `gemma-3-1b-it`                      | Gemma 3 1B IT                        | Supported  |
    | `gemma-3-27b-it`                     | Gemma 3 27B IT                       | Supported  |
    | `gemma-3-4b-it`                      | Gemma 3 4B IT                        | Supported  |
    | `gemma-3n-e4b-it`                    | Gemma 3n E4B IT                      | Supported  |
    """

    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_FLASH_EXP = 'gemini-2.0-flash-exp'
    GEMINI_2_0_FLASH_LITE = 'gemini-2.0-flash-lite'
    GEMINI_2_0_FLASH_THINKING_EXP_01_21 = 'gemini-2.0-flash-thinking-exp-01-21'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'
    GEMINI_2_5_PRO_EXP_03_25 = 'gemini-2.5-pro-exp-03-25'
    GEMINI_2_5_PRO_PREVIEW_03_25 = 'gemini-2.5-pro-preview-03-25'
    GEMINI_2_5_PRO_PREVIEW_05_06 = 'gemini-2.5-pro-preview-05-06'
    GEMINI_3_FLASH_PREVIEW = 'gemini-3-flash-preview'
    GEMINI_3_PRO_PREVIEW = 'gemini-3-pro-preview'
    GEMINI_2_5_PRO = 'gemini-2.5-pro'
    GEMINI_2_5_FLASH = 'gemini-2.5-flash'
    GEMINI_2_5_FLASH_LITE = 'gemini-2.5-flash-lite'
    GEMINI_2_5_FLASH_PREVIEW_TTS = 'gemini-2.5-flash-preview-tts'
    GEMINI_2_5_PRO_PREVIEW_TTS = 'gemini-2.5-pro-preview-tts'
    GEMINI_3_PRO_IMAGE_PREVIEW = 'gemini-3-pro-image-preview'
    GEMINI_2_5_FLASH_IMAGE_PREVIEW = 'gemini-2.5-flash-image-preview'
    GEMINI_2_5_FLASH_IMAGE = 'gemini-2.5-flash-image'
    GEMMA_3_12B_IT = 'gemma-3-12b-it'
    GEMMA_3_1B_IT = 'gemma-3-1b-it'
    GEMMA_3_27B_IT = 'gemma-3-27b-it'
    GEMMA_3_4B_IT = 'gemma-3-4b-it'
    GEMMA_3N_E4B_IT = 'gemma-3n-e4b-it'


SUPPORTED_MODELS = {
    GoogleAIGeminiVersion.GEMINI_1_5_FLASH: GEMINI_1_5_FLASH,
    GoogleAIGeminiVersion.GEMINI_1_5_FLASH_8B: GEMINI_1_5_FLASH_8B,
    GoogleAIGeminiVersion.GEMINI_1_5_PRO: GEMINI_1_5_PRO,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH: GEMINI_2_0_FLASH,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH_EXP: GEMINI_2_0_FLASH_EXP_IMAGEN,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH_LITE: GEMINI_2_0_FLASH_LITE,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH_THINKING_EXP_01_21: GEMINI_2_0_FLASH_THINKING_EXP_01_21,
    GoogleAIGeminiVersion.GEMINI_2_0_PRO_EXP_02_05: GEMINI_2_0_PRO_EXP_02_05,
    GoogleAIGeminiVersion.GEMINI_2_5_PRO_EXP_03_25: GEMINI_2_5_PRO_EXP_03_25,
    GoogleAIGeminiVersion.GEMINI_2_5_PRO_PREVIEW_03_25: GEMINI_2_5_PRO_PREVIEW_03_25,
    GoogleAIGeminiVersion.GEMINI_2_5_PRO_PREVIEW_05_06: GEMINI_2_5_PRO_PREVIEW_05_06,
    GoogleAIGeminiVersion.GEMINI_3_FLASH_PREVIEW: GENERIC_GEMINI_MODEL,
    GoogleAIGeminiVersion.GEMINI_3_PRO_PREVIEW: GENERIC_GEMINI_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_PRO: GENERIC_GEMINI_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_FLASH: GENERIC_GEMINI_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_FLASH_LITE: GENERIC_GEMINI_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_FLASH_PREVIEW_TTS: GENERIC_TTS_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_PRO_PREVIEW_TTS: GENERIC_TTS_MODEL,
    GoogleAIGeminiVersion.GEMINI_3_PRO_IMAGE_PREVIEW: GENERIC_IMAGE_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_FLASH_IMAGE_PREVIEW: GENERIC_IMAGE_MODEL,
    GoogleAIGeminiVersion.GEMINI_2_5_FLASH_IMAGE: GENERIC_IMAGE_MODEL,
    GoogleAIGeminiVersion.GEMMA_3_12B_IT: GENERIC_GEMMA_MODEL,
    GoogleAIGeminiVersion.GEMMA_3_1B_IT: GENERIC_GEMMA_MODEL,
    GoogleAIGeminiVersion.GEMMA_3_27B_IT: GENERIC_GEMMA_MODEL,
    GoogleAIGeminiVersion.GEMMA_3_4B_IT: GENERIC_GEMMA_MODEL,
    GoogleAIGeminiVersion.GEMMA_3N_E4B_IT: GENERIC_GEMMA_MODEL,
    VertexAIGeminiVersion.GEMINI_1_5_FLASH: GEMINI_1_5_FLASH,
    VertexAIGeminiVersion.GEMINI_1_5_FLASH_8B: GEMINI_1_5_FLASH_8B,
    VertexAIGeminiVersion.GEMINI_1_5_PRO: GEMINI_1_5_PRO,
    VertexAIGeminiVersion.GEMINI_2_0_FLASH: GEMINI_2_0_FLASH,
    VertexAIGeminiVersion.GEMINI_2_0_FLASH_EXP: GEMINI_2_0_FLASH_EXP_IMAGEN,
    VertexAIGeminiVersion.GEMINI_2_0_FLASH_LITE: GEMINI_2_0_FLASH_LITE,
    VertexAIGeminiVersion.GEMINI_2_0_FLASH_THINKING_EXP_01_21: GEMINI_2_0_FLASH_THINKING_EXP_01_21,
    VertexAIGeminiVersion.GEMINI_2_0_PRO_EXP_02_05: GEMINI_2_0_PRO_EXP_02_05,
    VertexAIGeminiVersion.GEMINI_2_5_PRO_EXP_03_25: GEMINI_2_5_PRO_EXP_03_25,
    VertexAIGeminiVersion.GEMINI_2_5_PRO_PREVIEW_03_25: GEMINI_2_5_PRO_PREVIEW_03_25,
    VertexAIGeminiVersion.GEMINI_2_5_PRO_PREVIEW_05_06: GEMINI_2_5_PRO_PREVIEW_05_06,
    VertexAIGeminiVersion.GEMINI_3_FLASH_PREVIEW: GENERIC_GEMINI_MODEL,
    VertexAIGeminiVersion.GEMINI_3_PRO_PREVIEW: GENERIC_GEMINI_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_PRO: GENERIC_GEMINI_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_FLASH: GENERIC_GEMINI_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_FLASH_LITE: GENERIC_GEMINI_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_FLASH_PREVIEW_TTS: GENERIC_TTS_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_PRO_PREVIEW_TTS: GENERIC_TTS_MODEL,
    VertexAIGeminiVersion.GEMINI_3_PRO_IMAGE_PREVIEW: GENERIC_IMAGE_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_FLASH_IMAGE_PREVIEW: GENERIC_IMAGE_MODEL,
    VertexAIGeminiVersion.GEMINI_2_5_FLASH_IMAGE: GENERIC_IMAGE_MODEL,
    VertexAIGeminiVersion.GEMMA_3_12B_IT: GENERIC_GEMMA_MODEL,
    VertexAIGeminiVersion.GEMMA_3_1B_IT: GENERIC_GEMMA_MODEL,
    VertexAIGeminiVersion.GEMMA_3_27B_IT: GENERIC_GEMMA_MODEL,
    VertexAIGeminiVersion.GEMMA_3_4B_IT: GENERIC_GEMMA_MODEL,
    VertexAIGeminiVersion.GEMMA_3N_E4B_IT: GENERIC_GEMMA_MODEL,
}


DEFAULT_SUPPORTS_MODEL = Supports(
    multiturn=True,
    media=True,
    tools=True,
    tool_choice=True,
    system_role=True,
    constrained='no-tools',
)


def google_model_info(
    version: str,
) -> ModelInfo:
    """Generates a ModelInfo object.

    This function tries to get the best ModelInfo Supports
    for the given version.

    Args:
        version: Version of the model.

    Returns:
        ModelInfo object.
    """
    return ModelInfo(
        label=f'Google AI - {version}',
        supports=DEFAULT_SUPPORTS_MODEL,
    )


class GeminiModel:
    """Gemini model."""

    def __init__(
        self,
        version: str | GoogleAIGeminiVersion | VertexAIGeminiVersion,
        client: genai.Client,
        registry: GenkitRegistry,
    ):
        """Initialize Gemini model.

        Args:
            version: Gemini version
            client: Google AI client
            registry: Genkit registry
        """
        self._version = version
        self._client = client
        self._registry = registry

    def _get_tools(self, request: GenerateRequest) -> list[genai_types.Tool]:
        """Generates VertexAI Gemini compatible tool definitions.

        Args:
            request: The generation request.

        Returns:
             list of Gemini tools
        """
        tools = []
        for tool in request.tools:
            genai_tool = self._create_tool(tool)
            tools.append(genai_tool)

        return tools

    def _create_tool(self, tool: ToolDefinition) -> genai_types.Tool:
        """Create a tool that is compatible with Google Genai API.

        Args:
            tool: Genkit Tool Definition

        Returns:
            Genai tool compatible with Gemini API.
        """
        params = self._convert_schema_property(tool.input_schema)
        function = genai_types.FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=params,
            response=self._convert_schema_property(tool.output_schema) if tool.output_schema else None,
        )
        return genai_types.Tool(function_declarations=[function])

    def _convert_schema_property(
        self, input_schema: dict[str, Any], defs: dict[str, Any] | None = None
    ) -> genai_types.Schema | None:
        """Sanitizes a schema to be compatible with Gemini API.

        Args:
            input_schema: A dictionary with input parameters
            defs: Dictionary with definitions. Optional.

        Returns:
            Schema or None
        """
        if input_schema is None:
            return None

        if defs is None:
            defs = input_schema.get('$defs') if '$defs' in input_schema else {}

        if '$ref' in input_schema:
            ref_path = input_schema['$ref']
            ref_tokens = ref_path.split('/')
            ref_name = ref_tokens[-1]

            if ref_name not in defs:
                raise ValueError(f'Failed to resolve schema for {ref_name}')

            schema = self._convert_schema_property(defs[ref_name], defs)

            if input_schema.get('description'):
                schema.description = input_schema['description']

            return schema

        if 'type' not in input_schema:
            return None

        schema = genai_types.Schema()
        if input_schema.get('description'):
            schema.description = input_schema['description']

        if 'required' in input_schema:
            schema.required = input_schema['required']

        if 'type' in input_schema:
            schema_type = genai_types.Type(input_schema['type'])
            schema.type = schema_type

            if 'enum' in input_schema:
                schema.enum = input_schema['enum']

            if schema_type == genai_types.Type.ARRAY:
                schema.items = self._convert_schema_property(input_schema['items'], defs)

            if schema_type == genai_types.Type.OBJECT:
                schema.properties = {}
                properties = input_schema['properties']
                for key in properties:
                    nested_schema = self._convert_schema_property(properties[key], defs)
                    schema.properties[key] = nested_schema

        return schema

    def _call_tool(self, call: genai_types.FunctionCall) -> genai_types.Content:
        """Calls tool's function from the registry.

        Args:
            call: FunctionCall from Gemini response

        Returns:
            Gemini message content to add to the message
        """
        tool_function = self._registry.registry.lookup_action(ActionKind.TOOL, call.name)
        if tool_function is None:
            raise LookupError(f'Tool {call.name} not found')

        args = tool_function.input_type.validate_python(call.args)
        tool_answer = tool_function.run(args)
        return genai_types.Content(
            parts=[
                genai_types.Part.from_function_response(
                    name=call.name,
                    response={
                        'content': tool_answer.response,
                    },
                )
            ]
        )

    async def _retrieve_cached_content(
        self, request: GenerateRequest, model_name: str, cache_config: dict, contents: list[genai_types.Content]
    ) -> genai_types.CachedContent:
        """Retrieves cached content from the Google API if exists.

        If content is present - increases storage ttl based on the configured `ttl_seconds`
        If content is not present - creates it and returns creates instance.

        Args:
            request: incoming generation instance
            model_name: name of the generation model to use
            cache_config: user-defined cache configuration (e.g. ttl_seconds)
            contents: content to submit for cached context creation

        Returns:
            Cached Content instance based on provided params
        """
        validate_context_cache_request(request=request, model_name=model_name)

        ttl = cache_config.get('ttl_seconds', DEFAULT_TTL)
        cache_key = generate_cache_key(request=request)

        iterator_config = genai_types.ListCachedContentsConfig()
        cache = None
        pages = await self._client.aio.caches.list(config=iterator_config)

        async for item in pages:
            if item.display_name == cache_key:
                cache = item
                break
        if cache:
            updated_expiration_time = datetime.now(timezone.UTC) + timedelta(seconds=ttl)
            cache = await self._client.aio.caches.update(
                name=cache.name, config=genai_types.UpdateCachedContentConfig(expireTime=updated_expiration_time)
            )
        else:
            cache = await self._client.aio.caches.create(
                model=model_name,
                config=genai_types.CreateCachedContentConfig(
                    contents=contents,
                    display_name=cache_key,
                    ttl=f'{ttl}s',
                ),
            )
        return cache

    async def generate(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Handle a generation request.

        Args:
            request: The generation request containing messages and parameters.
            ctx: action context

        Returns:
            The model's response to the generation request.
        """
        model_name = self._version
        if request.config:
            version = getattr(request.config, 'version', None)
            if version:
                model_name = version

        # TODO: do not move - this method mutates `request` by extracting system prompts into configuration object
        request_cfg = self._genkit_to_googleai_cfg(request=request)

        request_contents, cached_content = await self._build_messages(request=request, model_name=model_name)

        if cached_content:
            request_cfg.cached_content = cached_content.name

        if ctx.is_streaming:
            response = await self._streaming_generate(
                request_contents=request_contents, request_cfg=request_cfg, ctx=ctx, model_name=model_name
            )
        else:
            response = await self._generate(
                request_contents=request_contents, request_cfg=request_cfg, model_name=model_name
            )

        response.usage = self._create_usage_stats(request=request, response=response)

        return response

    async def _generate(
        self,
        request_contents: list[genai_types.Content],
        request_cfg: genai_types.GenerateContentConfig,
        model_name: str,
    ) -> GenerateResponse:
        """Call google-genai generate.

        Args:
            request_contents: request contents
            request_cfg: request configuration
            model_name: name of generation model to use

        Returns:
            genai response.
        """
        with tracer.start_as_current_span('generate_content') as span:
            span.set_attribute(
                'genkit:input',
                dump_json(
                    {
                        'config': dump_dict(request_cfg),
                        'contents': [dump_dict(c) for c in request_contents],
                        'model': model_name,
                    },
                    fallback=lambda _: '[!! failed to serialize !!]',
                ),
            )
            response = await self._client.aio.models.generate_content(
                model=model_name, contents=request_contents, config=request_cfg
            )
            span.set_attribute('genkit:output', dump_json(response))

        content = self._contents_from_response(response)

        return GenerateResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            )
        )

    async def _streaming_generate(
        self,
        request_contents: list[genai_types.Content],
        request_cfg: genai_types.GenerateContentConfig | None,
        ctx: ActionRunContext,
        model_name: str,
    ) -> GenerateResponse:
        """Call google-genai generate for streaming.

        Args:
            request_contents: request contents
            request_cfg: request configuration
            ctx: action context
            model_name: name of generation model to use

        Returns:
            empty genai response
        """
        with tracer.start_as_current_span('generate_content_stream') as span:
            span.set_attribute(
                'genkit:input',
                dump_json({
                    'config': dump_dict(request_cfg),
                    'contents': [dump_dict(c) for c in request_contents],
                    'model': model_name,
                }),
            )
            generator = self._client.aio.models.generate_content_stream(
                model=model_name, contents=request_contents, config=request_cfg
            )
        accumulated_content = []
        async for response_chunk in await generator:
            content = self._contents_from_response(response_chunk)
            accumulated_content.append(*content)
            ctx.send_chunk(
                chunk=GenerateResponseChunk(
                    content=content,
                    role=Role.MODEL,
                )
            )

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=accumulated_content,
            )
        )

    @cached_property
    def metadata(self) -> dict:
        """Get model metadata.

        Returns:
            model metadata.
        """
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }

    def is_multimode(self):
        """Check if the model supports media.

        Returns:
            True if the model supports media, False otherwise.
        """
        return SUPPORTED_MODELS[self._version].supports.media

    async def _build_messages(
        self, request: GenerateRequest, model_name: str
    ) -> tuple[list[genai_types.Content], genai_types.CachedContent]:
        """Build google-genai request contents from Genkit request.

        Args:
            request: Genkit request.
            model_name: name of generation model to use

        Returns:
            list of google-genai contents.
        """
        request_contents: list[genai_types.Content] = []
        cache = None

        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                continue
            content_parts: list[genai_types.Part] = []
            for p in msg.content:
                content_parts.append(PartConverter.to_gemini(p))
            request_contents.append(genai_types.Content(parts=content_parts, role=msg.role))

            if msg.metadata and msg.metadata.get('cache'):
                cache = await self._retrieve_cached_content(
                    request=request,
                    model_name=model_name,
                    cache_config=msg.metadata['cache'],
                    contents=request_contents,
                )

        if not request_contents:
            request_contents.append(genai_types.Content(parts=[genai_types.Part(text=' ')], role='user'))

        return request_contents, cache

    def _contents_from_response(self, response: genai_types.GenerateContentResponse) -> list:
        """Retrieve contents from google-genai response.

        Args:
            response: google-genai response.

        Returns:
            list of generated contents.
        """
        content = []
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content:
                    for i, part in enumerate(candidate.content.parts):
                        content.append(PartConverter.from_gemini(part=part, ref=str(i)))

        return content

    def _genkit_to_googleai_cfg(self, request: GenerateRequest) -> genai_types.GenerateContentConfig | None:
        """Translate GenerationCommonConfig to Google Ai GenerateContentConfig.

        Args:
            request: Genkit request.

        Returns:
            Google Ai request config or None.
        """
        cfg = None
        tools = []

        if request.config:
            request_config = request.config
            if isinstance(request_config, GenerationCommonConfig):
                cfg = genai_types.GenerateContentConfig(
                    max_output_tokens=request_config.max_output_tokens,
                    top_k=request_config.top_k,
                    top_p=request_config.top_p,
                    temperature=request_config.temperature,
                    stop_sequences=request_config.stop_sequences,
                )
            elif isinstance(request_config, GeminiConfigSchema):
                cfg = request_config
                if request_config.code_execution:
                    tools.extend([genai_types.Tool(code_execution=genai_types.ToolCodeExecution())])
            elif isinstance(request_config, dict):
                cfg = genai_types.GenerateContentConfig(**request_config)

        if request.output:
            if not cfg:
                cfg = genai_types.GenerateContentConfig()

            response_mime_type = 'application/json' if request.output.format == 'json' and not request.tools else None
            cfg.response_mime_type = response_mime_type

            if request.output.schema_ and request.output.constrained:
                cfg.response_schema = self._convert_schema_property(request.output.schema_)

        if request.tools:
            if not cfg:
                cfg = genai_types.GenerateContentConfig()

            tools.extend(self._get_tools(request))

        if tools:
            cfg.tools = tools

        system_messages = list(filter(lambda m: m.role == Role.SYSTEM, request.messages))
        if system_messages:
            system_parts = []
            if not cfg:
                cfg = genai.types.GenerateContentConfig()

            for msg in system_messages:
                for p in msg.content:
                    system_parts.append(PartConverter.to_gemini(p))
            cfg.system_instruction = genai.types.Content(parts=system_parts)

        return cfg

    def _create_usage_stats(self, request: GenerateRequest, response: GenerateResponse) -> GenerationUsage:
        """Create usage statistics.

        Args:
            request: Genkit request
            response: Genkit response

        Returns:
            usage statistics
        """
        usage = get_basic_usage_stats(input_=request.messages, response=response.message)
        if response.usage:
            usage.input_tokens = response.usage.input_tokens
            usage.output_tokens = response.usage.output_tokens
            usage.total_tokens = response.usage.total_tokens

        return usage
