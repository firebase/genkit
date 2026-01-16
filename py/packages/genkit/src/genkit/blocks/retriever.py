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

"""Retriever type definitions for the Genkit framework.

This module defines the type interfaces for retrievers in the Genkit framework.
Retrievers are used for fetching Genkit documents from a datastore, given a
query. These documents can then be used to provide additional context to models
to accomplish a task.
"""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from genkit.blocks.document import Document
from genkit.core.action import ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
from genkit.core.typing import DocumentData, RetrieverResponse

T = TypeVar('T')
# type RetrieverFn[T] = Callable[[Document, T], RetrieverResponse]
RetrieverFn = Callable[[Document, T], RetrieverResponse]


class Retriever(Generic[T]):
    def __init__(
        self,
        retriever_fn: RetrieverFn[T],
    ):
        self.retriever_fn = retriever_fn


class RetrieverRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    query: DocumentData
    options: Any | None = None


class RetrieverSupports(BaseModel):
    """Retriever capability support."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    media: bool | None = None


class RetrieverInfo(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    label: str | None = None
    supports: RetrieverSupports | None = None


class RetrieverOptions(BaseModel):
    """Configuration options for a retriever."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    config_schema: dict[str, Any] | None = Field(None, alias='configSchema')
    label: str | None = None
    supports: RetrieverSupports | None = None


class RetrieverRef(BaseModel):
    """Reference to a retriever with configuration."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str
    config: Any | None = None
    version: str | None = None
    info: RetrieverInfo | None = None


def retriever_action_metadata(
    name: str,
    options: RetrieverOptions | None = None,
) -> ActionMetadata:
    """Creates action metadata for a retriever."""
    options = options if options is not None else RetrieverOptions()
    retriever_metadata_dict = {'retriever': {}}

    if options.label:
        retriever_metadata_dict['retriever']['label'] = options.label

    if options.supports:
        retriever_metadata_dict['retriever']['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    retriever_metadata_dict['retriever']['customOptions'] = options.config_schema if options.config_schema else None

    return ActionMetadata(
        kind=ActionKind.RETRIEVER,
        name=name,
        input_json_schema=to_json_schema(RetrieverRequest),
        output_json_schema=to_json_schema(RetrieverResponse),
        metadata=retriever_metadata_dict,
    )


def create_retriever_ref(
    name: str,
    config: dict[str, Any] | None = None,
    version: str | None = None,
    info: RetrieverInfo | None = None,
) -> RetrieverRef:
    """Creates a RetrieverRef instance."""
    return RetrieverRef(name=name, config=config, version=version, info=info)


class IndexerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    documents: list[DocumentData]
    options: Any | None = None


class IndexerInfo(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    label: str | None = None
    supports: RetrieverSupports | None = None


class IndexerOptions(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    config_schema: dict[str, Any] | None = Field(None, alias='configSchema')
    label: str | None = None
    supports: RetrieverSupports | None = None


class IndexerRef(BaseModel):
    """Reference to an indexer with configuration."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str
    config: Any | None = None
    version: str | None = None
    info: IndexerInfo | None = None


def indexer_action_metadata(
    name: str,
    options: IndexerOptions | None = None,
) -> ActionMetadata:
    """Creates action metadata for an indexer."""
    options = options if options is not None else IndexerOptions()
    indexer_metadata_dict = {'indexer': {}}

    if options.label:
        indexer_metadata_dict['indexer']['label'] = options.label

    if options.supports:
        indexer_metadata_dict['indexer']['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    indexer_metadata_dict['indexer']['customOptions'] = options.config_schema if options.config_schema else None

    return ActionMetadata(
        kind=ActionKind.INDEXER,
        name=name,
        input_json_schema=to_json_schema(IndexerRequest),
        output_json_schema=to_json_schema(None),
        metadata=indexer_metadata_dict,
    )


def create_indexer_ref(
    name: str,
    config: dict[str, Any] | None = None,
    version: str | None = None,
    info: IndexerInfo | None = None,
) -> IndexerRef:
    """Creates a IndexerRef instance."""
    return IndexerRef(name=name, config=config, version=version, info=info)


def define_retriever(
    registry: Any,
    name: str,
    fn: RetrieverFn,
    options: RetrieverOptions | None = None,
) -> None:
    """Defines and registers a retriever action."""
    metadata = retriever_action_metadata(name, options)

    async def wrapper(
        request: RetrieverRequest,
        ctx: Any,
    ) -> RetrieverResponse:
        return await fn(request.query, request.options)

    registry.register_action(
        kind=ActionKind.RETRIEVER,
        name=name,
        fn=wrapper,
        metadata=metadata.metadata,
        span_metadata=metadata.metadata,
    )


IndexerFn = Callable[[list[Document], T], None]


def define_indexer(
    registry: Any,
    name: str,
    fn: IndexerFn,
    options: IndexerOptions | None = None,
) -> None:
    """Defines and registers an indexer action."""
    metadata = indexer_action_metadata(name, options)

    async def wrapper(
        request: IndexerRequest,
        ctx: Any,
    ) -> None:
        docs = [Document.from_data(d) for d in request.documents]
        await fn(docs, request.options)

    registry.register_action(
        kind=ActionKind.INDEXER,
        name=name,
        fn=wrapper,
        metadata=metadata.metadata,
        span_metadata=metadata.metadata,
    )
