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

"""Microsoft Foundry configuration types for Genkit.

This module defines configuration schemas that align with the Microsoft Foundry/
Azure OpenAI API.

See Also:
- Microsoft Foundry Docs: https://learn.microsoft.com/en-us/azure/ai-foundry/
- Model Catalog: https://ai.azure.com/catalog/models
- SDK Overview: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview
- OpenAI API Reference: https://platform.openai.com/docs/api-reference/chat/create
"""

import sys
from typing import ClassVar

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class VisualDetailLevel(StrEnum):
    """Visual detail level for image processing.

    Controls the level of visual detail when processing image embeddings.
    Lower detail levels decrease token usage.
    """

    AUTO = 'auto'
    LOW = 'low'
    HIGH = 'high'


class MSFoundryConfig(BaseModel):
    """Microsoft Foundry configuration for Genkit.

    This schema provides full control over Microsoft Foundry model parameters
    for OpenAI-compatible models.

    See: https://platform.openai.com/docs/api-reference/chat/create

    Attributes:
        model: Model version override for the request.
        temperature: Sampling temperature (0.0 to 2.0).
        max_tokens: Maximum number of tokens to generate.
        top_p: Nucleus sampling probability.
        stop: Stop sequences.
        frequency_penalty: Frequency penalty (-2.0 to 2.0).
        presence_penalty: Presence penalty (-2.0 to 2.0).
        logit_bias: Token ID to bias value mapping.
        log_probs: Whether to return log probabilities.
        top_log_probs: Number of top log probabilities to return.
        seed: Random seed for deterministic sampling.
        user: Unique user identifier for abuse monitoring.
        visual_detail_level: Detail level for image processing.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='allow',
        populate_by_name=True,
        alias_generator=to_camel,
    )

    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = None
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    stop: str | list[str] | None = None
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    logit_bias: dict[str, int] | None = None
    log_probs: bool | None = None
    top_log_probs: int | None = Field(default=None, ge=0, le=20)
    seed: int | None = None
    user: str | None = None
    visual_detail_level: VisualDetailLevel | None = None


class TextEmbeddingConfig(BaseModel):
    """Configuration for text embedding requests.

    Attributes:
        dimensions: Output embedding dimensions (model-dependent).
        encoding_format: Output encoding format ('float' or 'base64').
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='allow',
        populate_by_name=True,
        alias_generator=to_camel,
    )

    dimensions: int | None = None
    encoding_format: str | None = None
