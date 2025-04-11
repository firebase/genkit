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


"""OpenAI configuration for Genkit."""

import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from pydantic import BaseModel, ConfigDict


class OpenAIConfig(BaseModel):
    """OpenAI configuration for Genkit."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    model: str | None = None
    top_p: float | None = None
    temperature: float | None = None
    stop: str | list[str] | None = None
    max_tokens: int | None = None
    stream: bool | None = None


class SupportedOutputFormat(StrEnum):
    """Model Output Formats"""

    JSON_MODE = 'json_mode'
    STRUCTURED_OUTPUTS = 'structured_outputs'
    TEXT = 'text'
