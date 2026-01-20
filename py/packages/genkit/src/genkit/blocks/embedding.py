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

from pydantic import BaseModel, ConfigDict, Field

from genkit.blocks.document import Document
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
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


class Embedder:
    """Runtime embedder wrapper around an embedder Action."""

    def __init__(self, name: str, action: Action) -> None:
        self.name = name
        self._action = action

    async def embed(
        self,
        documents: list[Document],
        options: dict[str, Any] | None = None,
    ) -> EmbedResponse:
        return (await self._action.arun(EmbedRequest(input=documents, options=options))).response


EmbedderFn = Callable[[EmbedRequest], EmbedResponse]


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
