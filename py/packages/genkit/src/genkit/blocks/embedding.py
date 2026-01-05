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

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import get_func_description, to_json_schema
from genkit.core.typing import EmbedRequest, EmbedResponse


class EmbedderSupports(BaseModel):
    """Embedder capability support."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    input: list[str] | None = None
    multilingual: bool | None = None


class EmbedderOptions(BaseModel):
    """Configuration options for an embedder."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    config_schema: dict[str, Any] | None = Field(None, alias='configSchema')
    label: str | None = None
    supports: EmbedderSupports | None = None
    dimensions: int | None = None


class EmbedderRef(BaseModel):
    """Reference to an embedder with configuration."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str
    config: Any | None = None
    version: str | None = None


EmbedderFn = Callable[[EmbedRequest], EmbedResponse]


def embedder(
    name: str,
    fn: EmbedderFn,
    options: EmbedderOptions | None = None,
    metadata: dict[str, Any] | None = None,
    description: str | None = None,
) -> 'Action':
    """Create an embedder action WITHOUT registering it.

    This is the v2 API for creating embedders. Returns an Action instance
    that can be used standalone or registered by the framework.

    Args:
        name: Embedder name (without plugin prefix).
        fn: Function that implements embedding (takes EmbedRequest, returns EmbedResponse).
        options: Optional embedder options (dimensions, supports, etc.).
        metadata: Optional metadata dictionary.
        description: Optional human-readable description.

    Returns:
        Action instance (not registered).

    Example:
        >>> from genkit.blocks.embedding import embedder
        >>>
        >>> def my_embed(request: EmbedRequest) -> EmbedResponse:
        ...     return EmbedResponse(...)
        >>>
        >>> action = embedder(name="my-embedder", fn=my_embed)
        >>> response = await action.arun({"input": [...]})
    """
    embedder_meta = metadata if metadata else {}

    if 'embedder' not in embedder_meta:
        embedder_meta['embedder'] = {}

    if 'label' not in embedder_meta['embedder'] or not embedder_meta['embedder']['label']:
        embedder_meta['embedder']['label'] = name

    if options:
        if options.dimensions:
            embedder_meta['embedder']['dimensions'] = options.dimensions
        if options.config_schema:
            embedder_meta['embedder']['customOptions'] = options.config_schema
        if options.supports:
            embedder_meta['embedder']['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    final_description = description if description else get_func_description(fn)

    return Action(
        name=name,
        kind=ActionKind.EMBEDDER,
        fn=fn,
        metadata=embedder_meta,
        description=final_description,
    )


def embedder_action_metadata(
    name: str,
    options: EmbedderOptions | None = None,
) -> ActionMetadata:
    options = options if options is not None else EmbedderOptions()
    embedder_metadata_dict = {'embedder': {}}

    if options.label:
        embedder_metadata_dict['embedder']['label'] = options.label

    embedder_metadata_dict['embedder']['dimensions'] = options.dimensions

    if options.supports:
        embedder_metadata_dict['embedder']['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    embedder_metadata_dict['embedder']['customOptions'] = options.config_schema if options.config_schema else None

    return ActionMetadata(
        kind=ActionKind.EMBEDDER,
        name=name,
        input_json_schema=to_json_schema(EmbedRequest),
        output_json_schema=to_json_schema(EmbedResponse),
        metadata=embedder_metadata_dict,
    )


def create_embedder_ref(name: str, config: dict[str, Any] | None = None, version: str | None = None) -> EmbedderRef:
    """Creates an EmbedderRef instance."""
    return EmbedderRef(name=name, config=config, version=version)
