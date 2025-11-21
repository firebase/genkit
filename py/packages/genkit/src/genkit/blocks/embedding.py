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
from genkit.core.typing import EmbedRequest, EmbedResponse, EmbedderOptions, EmbedderRef, EmbedderSupports,EmbedderFn
from pydantic import BaseModel
# type EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
# EmbedderFn = Callable[[EmbedRequest], EmbedResponse]


# def embedder_action_metadata(
#     name: str,
#     info: dict[str, Any] | None = None,
#     config_schema: Any | None = None,
# ) -> ActionMetadata:
#     """Generates an ActionMetadata for embedders."""
#     info = info if info is not None else {}
#     return ActionMetadata(
#         kind=ActionKind.EMBEDDER,
#         name=name,
#         input_json_schema=to_json_schema(EmbedRequest),
#         output_json_schema=to_json_schema(EmbedResponse),
#         metadata={'embedder': {**info, 'customOptions': to_json_schema(config_schema) if config_schema else None}},
#     )

def embedder_action_metadata(
    name: str,
    #info: dict[str, Any] | None = None,
    options: EmbedderOptions | None = None,
) -> ActionMetadata:

    options = options if options is not None else EmbedderOptions()
    embedder_metadata_dict = {'embedder': {}}

    if options.label:
        embedder_metadata_dict['embedder']['label'] = options.label

    embedder_metadata_dict['embedder']['dimensions'] = options.dimensions

    if options.supports:
        embedder_metadata_dict['embedder']['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    embedder_metadata_dict['embedder']['customOptions'] = to_json_schema(options.config_schema) if options.config_schema else None

    return ActionMetadata(
        kind=ActionKind.EMBEDDER,
        name=name,
        input_json_schema=to_json_schema(EmbedRequest),
        output_json_schema=to_json_schema(EmbedResponse),
        metadata=embedder_metadata_dict,

    )

# New helper function
def create_embedder_ref(name: str, config: dict[str, Any] | None = None, version: str | None = None) -> EmbedderRef:
    """Creates an EmbedderRef instance."""
    return EmbedderRef(name=name, config=config, version=version)
