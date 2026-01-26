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

"""Llama Models for VertexAI Model Garden."""

from genkit.plugins.compat_oai.typing import SupportedOutputFormat
from genkit.types import ModelInfo, Supports

SUPPORTED_LLAMA_MODELS: dict[str, ModelInfo] = {
    'meta/llama-4-maverick-17b-128e-instruct-maas': ModelInfo(
        label='ModelGarden - Meta - llama-4-maverick',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'meta/llama-4-scout-17b-16e-instruct-maas': ModelInfo(
        label='ModelGarden - Meta - llama-4-scout',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'meta/llama-3.3-70b-instruct-maas': ModelInfo(
        label='ModelGarden - Meta - llama-3.3-70b',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
    'meta/llama-3.2-90b-vision-instruct-maas': ModelInfo(
        label='ModelGarden - Meta - llama-3.2-90b-vision',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT, SupportedOutputFormat.JSON_MODE],
        ),
    ),
}
