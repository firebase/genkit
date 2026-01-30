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

"""ChromaDB plugin implementation for Genkit.

This module provides the core plugin functionality for integrating ChromaDB
with Genkit applications, including retriever and indexer implementations.

Key Components
==============

┌───────────────────────────────────────────────────────────────────────────┐
│                         Plugin Components                                   │
├───────────────────────┬───────────────────────────────────────────────────┤
│ Component             │ Purpose                                           │
├───────────────────────┼───────────────────────────────────────────────────┤
│ Chroma                │ Main plugin class - registers retrievers/indexers │
│ ChromaRetriever       │ Similarity search against ChromaDB collections    │
│ ChromaIndexer         │ Store documents with embeddings in ChromaDB       │
│ chroma_retriever_ref  │ Create retriever reference by collection name     │
│ chroma_indexer_ref    │ Create indexer reference by collection name       │
└───────────────────────┴───────────────────────────────────────────────────┘

See Also:
    - JS Implementation: js/plugins/chroma/src/index.ts
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, cast

import chromadb
import structlog
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Embeddings, Include, Metadatas
from pydantic import BaseModel, Field

from genkit.blocks.document import Document
from genkit.blocks.retriever import (
    IndexerOptions,
    IndexerRequest,
    RetrieverOptions,
    RetrieverRequest,
    RetrieverResponse,
    indexer_action_metadata,
    retriever_action_metadata,
)
from genkit.core.action import Action, ActionMetadata, ActionRunContext
from genkit.core.plugin import Plugin
from genkit.core.registry import ActionKind, Registry
from genkit.core.schema import to_json_schema
from genkit.types import DocumentData, EmbedRequest

logger = structlog.get_logger(__name__)

CHROMA_PLUGIN_NAME = 'chroma'


class ChromaRetrieverOptions(BaseModel):
    """Options for ChromaDB retriever queries.

    Attributes:
        k: Number of results to return (default: 10).
        where: Metadata filter using ChromaDB where syntax.
        where_document: Document content filter.
        include: Fields to include in results.
    """

    k: int = Field(default=10, description='Number of results to return')
    where: dict[str, Any] | None = Field(default=None, description='Metadata filter')
    where_document: dict[str, Any] | None = Field(default=None, description='Document content filter')
    include: list[str] | None = Field(
        default=None,
        description='Fields to include: documents, embeddings, metadatas, distances',
    )


class ChromaIndexerOptions(BaseModel):
    """Options for ChromaDB indexer operations.

    Currently no additional options are supported.
    """

    pass


@dataclass
class ChromaCollectionConfig:
    """Configuration for a ChromaDB collection.

    Attributes:
        collection_name: Name of the ChromaDB collection.
        embedder: Genkit embedder reference (e.g., 'googleai/text-embedding-004').
        embedder_options: Optional embedder-specific configuration.
        client_params: ChromaDB client configuration.
        create_collection_if_missing: Create collection if it doesn't exist.
        metadata: Optional collection metadata.
    """

    collection_name: str
    embedder: str
    embedder_options: dict[str, Any] | None = None
    client_params: dict[str, Any] | Callable[[], Awaitable[dict[str, Any]]] | None = None
    create_collection_if_missing: bool = False
    metadata: dict[str, Any] | None = None


@dataclass
class ChromaPluginConfig:
    """Configuration for the Chroma plugin.

    Attributes:
        collections: List of collection configurations.
    """

    collections: list[ChromaCollectionConfig] = field(default_factory=list)


def _md5_hash(content: str) -> str:
    """Generate MD5 hash of content for document ID."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _get_client(client_params: dict[str, Any] | None) -> chromadb.ClientAPI:
    """Create a ChromaDB client from configuration.

    Args:
        client_params: Client configuration. If None, uses ephemeral client.

    Returns:
        ChromaDB client instance.
    """
    if client_params is None:
        return chromadb.Client()

    if 'path' in client_params:
        # Persistent local client
        return chromadb.PersistentClient(path=client_params['path'])
    elif 'host' in client_params:
        # HTTP client for remote Chroma
        return chromadb.HttpClient(
            host=client_params.get('host', 'localhost'),
            port=client_params.get('port', 8000),
            headers=client_params.get('headers'),
        )
    else:
        return chromadb.Client()


async def _get_client_async(
    client_params: dict[str, Any] | Callable[[], Awaitable[dict[str, Any]]] | None,
) -> chromadb.ClientAPI:
    """Get ChromaDB client, resolving async config if needed."""
    if callable(client_params):
        resolved_params = await client_params()
        return _get_client(resolved_params)
    return _get_client(client_params)


class ChromaRetriever:
    """ChromaDB retriever implementation.

    Performs similarity search against a ChromaDB collection using
    embeddings generated by a Genkit embedder.
    """

    def __init__(
        self,
        registry: Registry,
        collection_name: str,
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
        client_params: dict[str, Any] | Callable[[], Awaitable[dict[str, Any]]] | None = None,
        create_collection_if_missing: bool = False,
    ) -> None:
        """Initialize the ChromaDB retriever.

        Args:
            registry: Registry for resolving embedders.
            collection_name: Name of the ChromaDB collection.
            embedder: Embedder reference string.
            embedder_options: Optional embedder configuration.
            client_params: ChromaDB client configuration.
            create_collection_if_missing: Create collection if missing.
        """
        self._registry = registry
        self._collection_name = collection_name
        self._embedder = embedder
        self._embedder_options = embedder_options
        self._client_params = client_params
        self._create_collection_if_missing = create_collection_if_missing

    async def _get_collection(self) -> Collection:
        """Get or create the ChromaDB collection."""
        client = await _get_client_async(self._client_params)
        if self._create_collection_if_missing:
            return client.get_or_create_collection(name=self._collection_name)
        return client.get_collection(name=self._collection_name)

    async def _embed_content(self, content: list[Document]) -> list[list[float]]:
        """Generate embeddings using the registry-resolved embedder."""
        embedder_action = await self._registry.resolve_embedder(self._embedder)
        if embedder_action is None:
            raise ValueError(f'Embedder "{self._embedder}" not found')

        # Document is a subclass of DocumentData; cast for type checker variance
        request = EmbedRequest(input=cast(list[DocumentData], content), options=self._embedder_options)
        response = await embedder_action.arun(request)
        return [e.embedding for e in response.response.embeddings]

    async def retrieve(
        self,
        request: RetrieverRequest,
        _ctx: ActionRunContext,
    ) -> RetrieverResponse:
        """Retrieve documents similar to the query.

        Args:
            request: Retriever request with query and options.
            _ctx: Action run context (unused).

        Returns:
            Response containing matching documents.
        """
        # Generate query embedding
        query_doc = Document.from_document_data(document_data=request.query)
        embeddings = await self._embed_content([query_doc])
        if not embeddings:
            raise ValueError('Embedder returned no embeddings for query')

        query_embedding = embeddings[0]

        # Parse options
        k = 10
        where = None
        where_document = None
        include_fields: list[str] = ['documents', 'metadatas']

        if request.options:
            opts = request.options if isinstance(request.options, dict) else request.options.model_dump()
            k = opts.get('k', 10)
            where = opts.get('where')
            where_document = opts.get('where_document')
            if opts.get('include'):
                include_fields = list(set(opts['include']) | {'documents'})

        # Query ChromaDB
        collection = await self._get_collection()
        # Cast to chromadb types - our list types are compatible at runtime
        results = collection.query(
            query_embeddings=cast(Embeddings, [query_embedding]),
            n_results=k,
            where=where,
            where_document=where_document,
            include=cast(Include, include_fields),
        )

        # Convert results to Documents
        documents: list[DocumentData] = []
        result_docs = results.get('documents')
        result_metadatas = results.get('metadatas')
        result_distances = results.get('distances')
        result_embeddings = results.get('embeddings')

        if result_docs and result_docs[0]:
            for i, doc_content in enumerate(result_docs[0]):
                # Parse stored metadata
                metadata: dict[str, Any] = {}
                if result_metadatas and result_metadatas[0]:
                    stored_meta = result_metadatas[0][i]
                    if stored_meta:
                        if 'doc_metadata' in stored_meta:
                            try:
                                metadata = json.loads(str(stored_meta['doc_metadata']))
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning('Failed to parse document metadata', error=str(e))
                        # Add distance/embedding info if requested
                        if result_distances and result_distances[0]:
                            metadata['_distance'] = result_distances[0][i]
                        if result_embeddings and result_embeddings[0]:
                            metadata['_embedding'] = result_embeddings[0][i]

                # Reconstruct document
                data_type = 'text'
                if result_metadatas and result_metadatas[0]:
                    stored = result_metadatas[0][i]
                    if stored and 'data_type' in stored:
                        data_type = str(stored['data_type'])

                doc = Document.from_data(
                    data=doc_content,
                    data_type=data_type,
                    metadata=metadata,
                )
                # Document extends DocumentData, so it can be used directly
                documents.append(doc)

        return RetrieverResponse(documents=documents)


class ChromaIndexer:
    """ChromaDB indexer implementation.

    Stores documents with their embeddings in a ChromaDB collection.
    """

    def __init__(
        self,
        registry: Registry,
        collection_name: str,
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
        client_params: dict[str, Any] | Callable[[], Awaitable[dict[str, Any]]] | None = None,
        create_collection_if_missing: bool = False,
    ) -> None:
        """Initialize the ChromaDB indexer.

        Args:
            registry: Registry for resolving embedders.
            collection_name: Name of the ChromaDB collection.
            embedder: Embedder reference string.
            embedder_options: Optional embedder configuration.
            client_params: ChromaDB client configuration.
            create_collection_if_missing: Create collection if missing.
        """
        self._registry = registry
        self._collection_name = collection_name
        self._embedder = embedder
        self._embedder_options = embedder_options
        self._client_params = client_params
        self._create_collection_if_missing = create_collection_if_missing

    async def _get_collection(self) -> Collection:
        """Get or create the ChromaDB collection."""
        client = await _get_client_async(self._client_params)
        if self._create_collection_if_missing:
            return client.get_or_create_collection(name=self._collection_name)
        return client.get_collection(name=self._collection_name)

    async def _embed_content(self, content: list[Document]) -> list[list[float]]:
        """Generate embeddings using the registry-resolved embedder."""
        embedder_action = await self._registry.resolve_embedder(self._embedder)
        if embedder_action is None:
            raise ValueError(f'Embedder "{self._embedder}" not found')

        # Document is a subclass of DocumentData; cast for type checker variance
        request = EmbedRequest(input=cast(list[DocumentData], content), options=self._embedder_options)
        response = await embedder_action.arun(request)
        return [e.embedding for e in response.response.embeddings]

    async def index(self, request: IndexerRequest) -> None:
        """Index documents into the ChromaDB collection.

        Args:
            request: Indexer request containing documents to index.
        """
        if not request.documents:
            return

        # Generate embeddings for all documents
        docs = [Document.from_document_data(doc) for doc in request.documents]
        embeddings = await self._embed_content(docs)
        if not embeddings:
            raise ValueError('Embedder returned no embeddings for documents')

        # Prepare data for ChromaDB
        ids: list[str] = []
        embedding_vectors: list[list[float]] = []
        documents_list: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for doc, embedding in zip(docs, embeddings, strict=True):
            # Get embedding documents (handles multi-part documents)
            from genkit.types import Embedding

            emb_obj = Embedding(embedding=embedding)
            embedding_docs = doc.get_embedding_documents([emb_obj])

            for emb_doc in embedding_docs:
                # Generate unique ID from content
                content = emb_doc.text() or json.dumps(emb_doc.data())
                doc_id = _md5_hash(content)

                ids.append(doc_id)
                embedding_vectors.append(embedding)
                documents_list.append(content)

                # Store metadata
                meta: dict[str, Any] = {
                    'data_type': emb_doc.data_type() or 'text',
                }
                if emb_doc.metadata:
                    meta['doc_metadata'] = json.dumps(emb_doc.metadata)
                metadatas.append(meta)

        # Add to collection
        collection = await self._get_collection()
        # Cast to chromadb types - our list types are compatible at runtime
        collection.add(
            ids=ids,
            embeddings=cast(Embeddings, embedding_vectors),
            documents=documents_list,
            metadatas=cast(Metadatas, metadatas),
        )


class Chroma(Plugin):
    """ChromaDB vector store plugin for Genkit.

    This plugin registers retrievers and indexers for ChromaDB collections,
    enabling RAG (Retrieval-Augmented Generation) workflows.

    Example:
        ```python
        ai = Genkit(
            plugins=[
                Chroma(
                    collections=[
                        ChromaCollectionConfig(
                            collection_name='my_docs',
                            embedder='googleai/text-embedding-004',
                        )
                    ]
                )
            ]
        )
        ```
    """

    name = CHROMA_PLUGIN_NAME

    def __init__(
        self,
        collections: list[ChromaCollectionConfig] | None = None,
    ) -> None:
        """Initialize the Chroma plugin.

        Args:
            collections: List of collection configurations.
        """
        self._collections = collections or []
        self._registry: Registry | None = None
        self._actions: dict[str, Action] = {}

    async def init(self, registry: Registry | None = None) -> list[Action]:
        """Initialize plugin (lazy warm-up).

        Args:
            registry: Registry for action registration and embedder resolution.

        Returns:
            List of pre-registered actions.
        """
        self._registry = registry
        if registry is not None:
            for config in self._collections:
                self._register_collection(registry, config)
        return list(self._actions.values())

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action by name.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action.

        Returns:
            Action object if found, None otherwise.
        """
        if action_type not in (ActionKind.RETRIEVER, ActionKind.INDEXER):
            return None
        # Use composite key of action_type and name
        action_key = f'{action_type.value}/{name}'
        return self._actions.get(action_key)

    async def list_actions(self) -> list[ActionMetadata]:
        """List available actions for dev UI.

        Returns:
            List of action metadata.
        """
        metadata_list: list[ActionMetadata] = []
        for config in self._collections:
            name = f'{CHROMA_PLUGIN_NAME}/{config.collection_name}'
            metadata_list.append(
                ActionMetadata(
                    kind=ActionKind.RETRIEVER,
                    name=name,
                )
            )
            metadata_list.append(
                ActionMetadata(
                    kind=ActionKind.INDEXER,
                    name=name,
                )
            )
        return metadata_list

    def _register_collection(
        self,
        registry: Registry,
        config: ChromaCollectionConfig,
    ) -> None:
        """Register retriever and indexer for a collection.

        Args:
            registry: Action registry.
            config: Collection configuration.
        """
        name = f'{CHROMA_PLUGIN_NAME}/{config.collection_name}'

        # Create and register retriever
        retriever = ChromaRetriever(
            registry=registry,
            collection_name=config.collection_name,
            embedder=config.embedder,
            embedder_options=config.embedder_options,
            client_params=config.client_params,
            create_collection_if_missing=config.create_collection_if_missing,
        )

        retriever_action = registry.register_action(
            kind=ActionKind.RETRIEVER,
            name=name,
            fn=retriever.retrieve,
            metadata=retriever_action_metadata(
                name=name,
                options=RetrieverOptions(
                    label=f'ChromaDB - {config.collection_name}',
                    config_schema=to_json_schema(ChromaRetrieverOptions),
                ),
            ).metadata,
        )
        if retriever_action:
            self._actions[f'{ActionKind.RETRIEVER.value}/{name}'] = retriever_action

        # Create and register indexer
        indexer = ChromaIndexer(
            registry=registry,
            collection_name=config.collection_name,
            embedder=config.embedder,
            embedder_options=config.embedder_options,
            client_params=config.client_params,
            create_collection_if_missing=config.create_collection_if_missing,
        )

        indexer_action = registry.register_action(
            kind=ActionKind.INDEXER,
            name=name,
            fn=indexer.index,
            metadata=indexer_action_metadata(
                name=name,
                options=IndexerOptions(label=f'ChromaDB - {config.collection_name}'),
            ).metadata,
        )
        if indexer_action:
            self._actions[f'{ActionKind.INDEXER.value}/{name}'] = indexer_action


def chroma(
    collections: list[dict[str, Any]] | None = None,
) -> Chroma:
    """Create a Chroma plugin with the given configuration.

    This is a convenience function for creating a Chroma plugin instance.

    Args:
        collections: List of collection configuration dictionaries.

    Returns:
        Configured Chroma plugin instance.

    Example:
        ```python
        ai = Genkit(
            plugins=[
                chroma(
                    collections=[
                        {
                            'collection_name': 'my_docs',
                            'embedder': 'googleai/text-embedding-004',
                            'create_collection_if_missing': True,
                        }
                    ]
                )
            ]
        )
        ```
    """
    configs = []
    if collections:
        for c in collections:
            configs.append(
                ChromaCollectionConfig(
                    collection_name=c['collection_name'],
                    embedder=c['embedder'],
                    embedder_options=c.get('embedder_options'),
                    client_params=c.get('client_params'),
                    create_collection_if_missing=c.get('create_collection_if_missing', False),
                    metadata=c.get('metadata'),
                )
            )
    return Chroma(collections=configs)


def chroma_retriever_ref(
    collection_name: str,
    display_name: str | None = None,
) -> str:
    """Create a retriever reference for a ChromaDB collection.

    Args:
        collection_name: Name of the ChromaDB collection.
        display_name: Optional display name (unused, for parity with JS).

    Returns:
        Retriever reference string.
    """
    return f'chroma/{collection_name}'


def chroma_indexer_ref(
    collection_name: str,
    display_name: str | None = None,
) -> str:
    """Create an indexer reference for a ChromaDB collection.

    Args:
        collection_name: Name of the ChromaDB collection.
        display_name: Optional display name (unused, for parity with JS).

    Returns:
        Indexer reference string.
    """
    return f'chroma/{collection_name}'


async def create_chroma_collection(
    name: str,
    client_params: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Collection:
    """Create a ChromaDB collection.

    Args:
        name: Collection name.
        client_params: ChromaDB client configuration.
        metadata: Optional collection metadata.

    Returns:
        The created ChromaDB collection.
    """
    client = await _get_client_async(client_params)
    return client.create_collection(name=name, metadata=metadata)


async def delete_chroma_collection(
    name: str,
    client_params: dict[str, Any] | None = None,
) -> None:
    """Delete a ChromaDB collection.

    Args:
        name: Collection name.
        client_params: ChromaDB client configuration.
    """
    client = await _get_client_async(client_params)
    client.delete_collection(name=name)
