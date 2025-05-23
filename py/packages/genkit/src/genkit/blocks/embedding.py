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

"""Embedding actions."""

from collections.abc import Callable
from typing import Any

from genkit.ai import ActionKind
from genkit.core.action import ActionMetadata
from genkit.core.schema import to_json_schema
from genkit.core.typing import EmbedRequest, EmbedResponse

# type EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
EmbedderFn = Callable[[EmbedRequest], EmbedResponse]


def embedder_action_metadata(
    name: str,
    info: dict[str, Any] | None = None,
    config_schema: Any | None = None,
) -> ActionMetadata:
    """Generates an ActionMetadata for embedders."""
    info = info if info is not None else {}
    return ActionMetadata(
        kind=ActionKind.EMBEDDER,
        name=name,
        input_json_schema=to_json_schema(EmbedRequest),
        output_json_schema=to_json_schema(EmbedResponse),
        metadata={'embedder': {**info, 'customOptions': to_json_schema(config_schema) if config_schema else None}},
    )
