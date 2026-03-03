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

This module defines the type interfaces for retrievers and indexers in the
Genkit framework. Retrievers are used for fetching documents from a datastore
given a query, enabling Retrieval-Augmented Generation (RAG) patterns.

Overview:
    Retrievers are a core component of RAG (Retrieval-Augmented Generation)
    workflows. They search a document store and return relevant documents
    that can be used to ground model responses with factual information.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      RAG Data Flow                                      │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐    │
    │  │  User    │ ───► │ Embedder │ ───► │ Retriever│ ───► │  Model   │    │
    │  │  Query   │      │          │      │  Search  │      │ Generate │    │
    │  └──────────┘      └──────────┘      └──────────┘      └──────────┘    │
    │                                             │                          │
    │                                             ▼                          │
    │                                      ┌──────────┐                      │
    │                                      │ Document │                      │
    │                                      │   Store  │                      │
    │                                      └──────────┘                      │
    └─────────────────────────────────────────────────────────────────────────┘

Terminology:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Term              │ Description                                         │
    ├───────────────────┼─────────────────────────────────────────────────────┤
    │ Retriever         │ Action that searches a document store and returns   │
    │                   │ relevant documents based on a query.                │
    │ Indexer           │ Action that adds documents to a document store,     │
    │                   │ typically with embeddings for similarity search.    │
    │ RetrieverRef      │ Reference to a retriever with optional config.      │
    │ IndexerRef        │ Reference to an indexer with optional config.       │
    │ Document          │ A structured piece of content with text/media and   │
    │                   │ metadata. See genkit.ai.document.               │
    │ Query             │ The search query, typically as a Document object.   │
    └───────────────────┴─────────────────────────────────────────────────────┘

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component           │ Description                                       │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ Retriever[T]        │ Base class for retriever implementations          │
    │ RetrieverRequest    │ Input model with query and options                │
    │ RetrieverOptions    │ Configuration for defining retrievers             │
    │ RetrieverRef        │ Reference bundling name, config, version          │
    │ IndexerRequest      │ Input model for indexing documents                │
    │ IndexerOptions      │ Configuration for defining indexers               │
    │ define_retriever()  │ Factory function for creating retriever actions   │
    │ define_indexer()    │ Factory function for creating indexer actions     │
    └─────────────────────┴───────────────────────────────────────────────────┘

Example:
    Defining a simple retriever:

    ```python
    from genkit import Genkit, Document
    from genkit.ai.retriever import RetrieverOptions

    ai = Genkit()


    # Simple in-memory retriever
    @ai.retriever(name='my_retriever')
    async def my_retriever(query: Document, options: dict) -> list[Document]:
        # Search logic here (e.g., vector similarity search)
        results = search_documents(query.text(), top_k=options.get('k', 5))
        return [Document.from_text(r['text'], r['metadata']) for r in results]


    # Use the retriever
    docs = await ai.retrieve(retriever='my_retriever', query='What is Genkit?')
    ```

    Using simple_retriever for easier definition:

    ```python
    @ai.simple_retriever(name='docs_retriever', configSchema=MyConfigSchema)
    async def docs_retriever(query: str, options: MyConfigSchema) -> list[Document]:
        # The query is automatically converted to string
        return await search_docs(query, limit=options.limit)
    ```

Caveats:
    - Retriever functions receive a Document object, not a raw string
    - Use simple_retriever() for a more convenient string-based query API
    - Indexers are typically used during data ingestion, not query time

See Also:
    - genkit.ai.document: Document model
    - genkit.ai.embedding: Embedder for generating document embeddings
    - RAG documentation: https://genkit.dev/docs/rag
"""

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from genkit.ai.document import Document
from genkit.core._internal._registry import Registry
from genkit.core._internal._schema import to_json_schema
from genkit.core._internal._typing import DocumentData, DocumentPart, RetrieverResponse
from genkit.core.action import Action, ActionKind, ActionMetadata

R = TypeVar('R')

T = TypeVar('T')
# type RetrieverFn[T] = Callable[[Document, T], RetrieverResponse | Awaitable[RetrieverResponse]]
RetrieverFn = Callable[[Document, T], RetrieverResponse | Awaitable[RetrieverResponse]]
# type IndexerFn[T] = Callable[[list[Document], T], None | Awaitable[None]]
IndexerFn = Callable[[list[Document], T], None | Awaitable[None]]


class Retriever(Generic[T]):
    """Base class for retrievers in the Genkit framework."""

    def __init__(
        self,
        retriever_fn: RetrieverFn[T],
    ) -> None:
        """Initialize a Retriever.

        Args:
            retriever_fn: The function that performs the retrieval.
        """
        self.retriever_fn: RetrieverFn[T] = retriever_fn


class RetrieverRequest(BaseModel):
    """Request model for a retriever execution."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    query: DocumentData
    options: Any | None = None


class RetrieverSupports(BaseModel):
    """Retriever capability support."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    media: bool | None = None


class RetrieverInfo(BaseModel):
    """Information about a retriever."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    label: str | None = None
    supports: RetrieverSupports | None = None


class RetrieverOptions(BaseModel):
    """Configuration options for a retriever."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=to_camel)

    config_schema: dict[str, Any] | None = None
    label: str | None = None
    supports: RetrieverSupports | None = None


class RetrieverRef(BaseModel):
    """Reference to a retriever with configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

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
    retriever_metadata_dict: dict[str, object] = {'retriever': {}}
    retriever_info = cast(dict[str, object], retriever_metadata_dict['retriever'])

    if options.label:
        retriever_info['label'] = options.label

    if options.supports:
        retriever_info['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    retriever_info['customOptions'] = options.config_schema if options.config_schema else None
    return ActionMetadata(
        kind=cast(ActionKind, ActionKind.RETRIEVER),
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
    """Request model for an indexer execution."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    documents: list[DocumentData]
    options: Any | None = None


class IndexerInfo(BaseModel):
    """Information about an indexer."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

    label: str | None = None
    supports: RetrieverSupports | None = None


class IndexerOptions(BaseModel):
    """Configuration options for an indexer."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=to_camel)

    config_schema: dict[str, Any] | None = None
    label: str | None = None
    supports: RetrieverSupports | None = None


class IndexerRef(BaseModel):
    """Reference to an indexer with configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True)

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
    indexer_metadata_dict: dict[str, object] = {'indexer': {}}
    indexer_info = cast(dict[str, object], indexer_metadata_dict['indexer'])

    if options.label:
        indexer_info['label'] = options.label

    if options.supports:
        indexer_info['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)

    indexer_info['customOptions'] = options.config_schema if options.config_schema else None

    return ActionMetadata(
        kind=cast(ActionKind, ActionKind.INDEXER),
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


class SimpleRetrieverOptions(BaseModel, Generic[R]):
    """Configuration options for `define_simple_retriever`.

    This class defines how items returned by a simple retriever handler are
    mapped into Genkit `DocumentData` objects.

    Attributes:
        name: The unique name of the retriever.
        content: Specifies how to extract content from the returned items.
            Can be a string key (for dict items) or a callable that transforms the item.
        metadata: Specifies how to extract metadata from the returned items.
            Can be a list of keys (for dict items) or a callable that transforms the item.
        config_schema: Optional Pydantic schema or JSON schema for retriever configuration.
    """

    name: str
    content: str | Callable[[R], str | list[DocumentPart]] | None = None
    metadata: list[str] | Callable[[R], dict[str, Any]] | None = None
    config_schema: type[BaseModel] | dict[str, Any] | None = None


def _item_to_document(item: R, options: SimpleRetrieverOptions[R]) -> DocumentData:
    """Internal helper to convert a raw item to a Genkit DocumentData."""
    if isinstance(item, (Document, DocumentData)):
        return item

    if isinstance(item, str):
        return Document.from_text(item)

    if callable(options.content):
        transformed = options.content(item)
        if isinstance(transformed, str):
            return Document.from_text(transformed)
        else:
            # transformed is list[DocumentPart]
            return DocumentData(content=transformed)

    if isinstance(options.content, str) and isinstance(item, dict):
        item_dict = cast(dict[str, object], item)
        return Document.from_text(str(item_dict[options.content]))

    if options.content is None and isinstance(item, str):
        return Document.from_text(item)

    raise ValueError(f'Cannot convert item to document without content option. Item: {item}')


def _item_to_metadata(item: R, options: SimpleRetrieverOptions[R]) -> dict[str, Any] | None:
    """Internal helper to extract metadata from a raw item for a Document."""
    if isinstance(item, str):
        return None

    if isinstance(options.metadata, list) and isinstance(item, dict):
        item_dict = cast(dict[str, object], item)
        result: dict[str, Any] = {}
        for key in options.metadata:
            str_key = str(key)
            value = item_dict.get(str_key)
            if value is not None:
                result[str_key] = value
        return result

    if callable(options.metadata):
        return options.metadata(item)

    if options.metadata is None and isinstance(item, dict):
        out = cast(dict[str, Any], item.copy())
        if isinstance(options.content, str) and options.content in out:
            del out[options.content]
        return out

    return None


def _get_func_description(func: Callable[..., Any], description: str | None = None) -> str:
    """Get the description of a function.

    Args:
        func: The function to get the description of.
        description: The description to use if the function docstring is
            empty.
    """
    if description is not None:
        return description
    if func.__doc__ is not None:
        return func.__doc__
    return ''


def define_retriever_action(
    registry: Registry,
    name: str,
    fn: RetrieverFn[Any],
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    description: str | None = None,
) -> Action:
    """Define a retriever action.

    This is the full-featured version used by GenkitRegistry.define_retriever.

    Args:
        registry: The registry to register the retriever in.
        name: Name of the retriever.
        fn: Function implementing the retriever behavior.
        config_schema: Optional schema for retriever configuration.
        metadata: Optional metadata for the retriever.
        description: Optional description for the retriever.

    Returns:
        The registered retriever Action.
    """
    retriever_meta: dict[str, object] = dict(metadata) if metadata else {}
    retriever_info: dict[str, object]
    existing_retriever = retriever_meta.get('retriever')
    if isinstance(existing_retriever, dict):
        retriever_info = {str(key): value for key, value in existing_retriever.items()}
    else:
        retriever_info = {}
    retriever_meta['retriever'] = retriever_info
    label_value = retriever_info.get('label')
    if not isinstance(label_value, str) or not label_value:
        retriever_info['label'] = name
    if config_schema:
        retriever_info['customOptions'] = to_json_schema(config_schema)

    retriever_description = _get_func_description(fn, description)
    return registry.register_action(
        name=name,
        kind=cast(ActionKind, ActionKind.RETRIEVER),
        fn=fn,
        metadata=retriever_meta,
        description=retriever_description,
    )


def define_simple_retriever(
    registry: Registry,
    options: SimpleRetrieverOptions[R] | str,
    handler: Callable[[DocumentData, Any], Awaitable[list[R]]],
    description: str | None = None,
) -> Action:
    """Define a simple retriever action.

    A simple retriever makes it easy to map existing data into documents
    that can be used for prompt augmentation.

    Args:
        registry: The registry to register the retriever in.
        options: Configuration options for the retriever, or just the name.
        handler: An async function that queries a datastore and returns items
            from which to extract documents.
        description: Optional description for the retriever.

    Returns:
        The registered Action for the retriever.

    Raises:
        TypeError: If handler is not an async function.
    """
    if not inspect.iscoroutinefunction(handler):
        raise TypeError('handler must be an async function')

    if isinstance(options, str):
        options = SimpleRetrieverOptions(name=options)

    async def retriever_fn(query: Document, options_obj: Any) -> RetrieverResponse:  # noqa: ANN401
        items = await handler(query, options_obj)
        docs = []
        for item in items:
            doc = _item_to_document(item, options)
            if not isinstance(item, str):
                doc.metadata = _item_to_metadata(item, options)
            docs.append(doc)
        return RetrieverResponse(documents=docs)

    return define_retriever_action(
        registry,
        name=options.name,
        fn=retriever_fn,
        config_schema=options.config_schema,
        description=description,
    )


def define_indexer_action(
    registry: Registry,
    name: str,
    fn: IndexerFn[Any],
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    description: str | None = None,
) -> Action:
    """Define an indexer action.

    This is the full-featured version used by GenkitRegistry.define_indexer.

    Args:
        registry: The registry to register the indexer in.
        name: Name of the indexer.
        fn: Function implementing the indexer behavior.
        config_schema: Optional schema for indexer configuration.
        metadata: Optional metadata for the indexer.
        description: Optional description for the indexer.

    Returns:
        The registered indexer Action.
    """
    indexer_meta: dict[str, object] = dict(metadata) if metadata else {}
    indexer_info: dict[str, object]
    existing_indexer = indexer_meta.get('indexer')
    if isinstance(existing_indexer, dict):
        indexer_info = {str(key): value for key, value in existing_indexer.items()}
    else:
        indexer_info = {}
    indexer_meta['indexer'] = indexer_info
    label_value = indexer_info.get('label')
    if not isinstance(label_value, str) or not label_value:
        indexer_info['label'] = name
    if config_schema:
        indexer_info['customOptions'] = to_json_schema(config_schema)

    indexer_description = _get_func_description(fn, description)
    return registry.register_action(
        name=name,
        kind=cast(ActionKind, ActionKind.INDEXER),
        fn=fn,
        metadata=indexer_meta,
        description=indexer_description,
    )


def define_retriever(
    registry: Registry,
    name: str,
    fn: RetrieverFn[Any],
    options: RetrieverOptions | None = None,
) -> None:
    """Defines and registers a retriever action."""
    metadata = retriever_action_metadata(name, options)

    async def wrapper(
        request: RetrieverRequest,
        _ctx: Any,  # noqa: ANN401
    ) -> RetrieverResponse:
        query = Document.from_document_data(request.query)
        res = fn(query, request.options)
        return await res if inspect.isawaitable(res) else res

    _ = registry.register_action(
        kind=cast(ActionKind, ActionKind.RETRIEVER),
        name=name,
        fn=wrapper,
        metadata=metadata.metadata,
        span_metadata={'genkit:metadata:retriever:name': name},
    )


def define_indexer(
    registry: Registry,
    name: str,
    fn: IndexerFn[Any],
    options: IndexerOptions | None = None,
) -> None:
    """Defines and registers an indexer action."""
    metadata = indexer_action_metadata(name, options)

    async def wrapper(
        request: IndexerRequest,
        _ctx: Any,  # noqa: ANN401
    ) -> None:
        docs = [Document.from_document_data(d) for d in request.documents]
        res = fn(docs, request.options)
        if inspect.isawaitable(res):
            await res

    _ = registry.register_action(
        kind=cast(ActionKind, ActionKind.INDEXER),
        name=name,
        fn=wrapper,
        metadata=metadata.metadata,
        span_metadata={'genkit:metadata:indexer:name': name},
    )
