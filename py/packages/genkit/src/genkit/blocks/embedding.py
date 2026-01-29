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

"""Embedding types and utilities for Genkit.

This module provides types and utilities for working with text embeddings
in Genkit. Embeddings are numerical vector representations of text that
capture semantic meaning, enabling similarity search, clustering, and
other AI applications.

Terminology:

    +-------------------+------------------------------------------------------+
    | Term              | Description                                          |
    +===================+======================================================+
    | Embedding         | A numerical vector (list of floats) representing     |
    |                   | semantic meaning. Similar texts produce similar      |
    |                   | vectors. Contains 'embedding' field and metadata.    |
    +-------------------+------------------------------------------------------+
    | Embedder          | A model/service that converts text to embeddings.    |
    |                   | Examples: 'googleai/text-embedding-004'. Registered  |
    |                   | as actions, invoked via embed() and embed_many().    |
    +-------------------+------------------------------------------------------+
    | EmbedderRef       | Reference bundling embedder name with optional       |
    |                   | config and version. Useful for reusing settings.     |
    +-------------------+------------------------------------------------------+
    | Document          | Structured content to embed. Create via              |
    |                   | Document.from_text(). Can include metadata.          |
    +-------------------+------------------------------------------------------+
    | Dimensions        | Size of embedding vector (e.g., 768 or 1536 floats). |
    |                   | Higher dimensions = more nuance but more storage.    |
    +-------------------+------------------------------------------------------+

Key Components:

    +-------------------+------------------------------------------------------+
    | Component         | Description                                          |
    +===================+======================================================+
    | EmbedderRef       | Reference to an embedder with optional configuration |
    +-------------------+------------------------------------------------------+
    | EmbedderOptions   | Configuration options for defining embedders         |
    +-------------------+------------------------------------------------------+
    | EmbedderSupports  | Declares what input types an embedder supports       |
    +-------------------+------------------------------------------------------+
    | Embedder          | Runtime wrapper around an embedder action            |
    +-------------------+------------------------------------------------------+
    | create_embedder   | Factory function for creating embedder references    |
    | _ref              |                                                      |
    +-------------------+------------------------------------------------------+

Usage with Genkit:
    The primary way to use embeddings is through the Genkit class methods:

    - ai.embed(): Embed a single piece of content
    - ai.embed_many(): Embed multiple pieces of content in batch

Example - Single embedding:
    >>> embeddings = await ai.embed(embedder='googleai/text-embedding-004', content='Hello, world!')
    >>> vector = embeddings[0].embedding

Example - Batch embedding:
    >>> embeddings = await ai.embed_many(embedder='googleai/text-embedding-004', content=['Doc 1', 'Doc 2', 'Doc 3'])

Example - Using EmbedderRef with configuration:
    >>> ref = create_embedder_ref('googleai/text-embedding-004', config={'task_type': 'CLUSTERING'}, version='v1')
    >>> embeddings = await ai.embed(embedder=ref, content='My text')

Note on embed() vs embed_many():
    - embed() extracts config/version from EmbedderRef and merges with options
    - embed_many() does NOT extract config from EmbedderRef - pass options directly

See Also:
    - genkit.ai.Genkit.embed: Single content embedding method
    - genkit.ai.Genkit.embed_many: Batch embedding method
    - genkit.core.typing.Embedding: The embedding result type
"""

from collections.abc import Callable
from typing import Any, ClassVar, cast

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from genkit.blocks.document import Document
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
from genkit.core.typing import DocumentData, EmbedRequest, EmbedResponse


class EmbedderSupports(BaseModel):
    """Embedder capability support."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    input: list[str] | None = None
    multilingual: bool | None = None


class EmbedderOptions(BaseModel):
    """Configuration options for an embedder."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=to_camel)

    config_schema: dict[str, Any] | None = None
    label: str | None = None
    supports: EmbedderSupports | None = None
    dimensions: int | None = None


class EmbedderRef(BaseModel):
    """Reference to an embedder with configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    name: str
    config: Any | None = None
    version: str | None = None


class Embedder:
    """Runtime embedder wrapper around an embedder Action."""

    def __init__(self, name: str, action: Action) -> None:
        """Initialize the Embedder.

        Args:
            name: The name of the embedder.
            action: The underlying action to execute.
        """
        self.name: str = name
        self._action: Action = action

    async def embed(
        self,
        documents: list[Document],
        options: dict[str, Any] | None = None,
    ) -> EmbedResponse:
        """Embed a list of documents.

        Args:
            documents: The documents to embed.
            options: Optional configuration for the embedding request.

        Returns:
            The generated embedding response.
        """
        # NOTE: Document subclasses DocumentData, so this is type-safe at runtime.
        # NOTE: Document subclasses DocumentData, so this is type-safe at runtime.
        return (
            await self._action.arun(EmbedRequest(input=cast(list['DocumentData'], documents), options=options))
        ).response


EmbedderFn = Callable[[EmbedRequest], EmbedResponse]


def embedder_action_metadata(
    name: str,
    options: EmbedderOptions | None = None,
) -> ActionMetadata:
    """Creates metadata for an embedder action.

    Args:
        name: The name of the embedder.
        options: Configuration options for the embedder.

    Returns:
        The action metadata for the embedder.
    """
    options = options if options is not None else EmbedderOptions()
    embedder_metadata_dict: dict[str, object] = {'embedder': {}}
    embedder_info = cast(dict[str, object], embedder_metadata_dict['embedder'])

    if options.label:
        embedder_info['label'] = options.label

    embedder_info['dimensions'] = options.dimensions

    if options.supports:
        embedder_info['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    embedder_info['customOptions'] = options.config_schema if options.config_schema else None

    return ActionMetadata(
        kind=cast(ActionKind, ActionKind.EMBEDDER),
        name=name,
        input_json_schema=to_json_schema(EmbedRequest),
        output_json_schema=to_json_schema(EmbedResponse),
        metadata=embedder_metadata_dict,
    )


def create_embedder_ref(name: str, config: dict[str, Any] | None = None, version: str | None = None) -> EmbedderRef:
    """Creates an EmbedderRef instance."""
    return EmbedderRef(name=name, config=config, version=version)
