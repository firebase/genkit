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

"""Pinecone plugin implementation for Genkit.

This module provides the core plugin functionality for integrating Pinecone
with Genkit applications, including retriever and indexer implementations.

Key Components
==============

┌───────────────────────────────────────────────────────────────────────────┐
│                         Plugin Components                                   │
├───────────────────────┬───────────────────────────────────────────────────┤
│ Component             │ Purpose                                           │
├───────────────────────┼───────────────────────────────────────────────────┤
│ Pinecone              │ Main plugin class - registers retrievers/indexers │
│ PineconeRetriever     │ Similarity search against Pinecone indexes        │
│ PineconeIndexer       │ Upsert documents with embeddings to Pinecone      │
│ pinecone_retriever_ref│ Create retriever reference by index ID            │
│ pinecone_indexer_ref  │ Create indexer reference by index ID              │
└───────────────────────┴───────────────────────────────────────────────────┘

See Also:
    - JS Implementation: js/plugins/pinecone/src/index.ts
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, cast

import structlog
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
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from pinecone.db_data.index import Index as PineconeIndex

logger = structlog.get_logger(__name__)

PINECONE_PLUGIN_NAME = 'pinecone'
CONTENT_KEY = '_content'
CONTENT_TYPE_KEY = '_content_type'
MAX_K = 1000


class PineconeRetrieverOptions(BaseModel):
    """Options for Pinecone retriever queries.

    Attributes:
        k: Number of results to return (default: 10, max: 1000).
        namespace: Pinecone namespace for data isolation.
        filter: Metadata filter for queries.
    """

    k: int = Field(default=10, le=MAX_K, description='Number of results to return')
    namespace: str | None = Field(default=None, description='Pinecone namespace')
    filter: dict[str, Any] | None = Field(default=None, description='Metadata filter')


class PineconeIndexerOptions(BaseModel):
    """Options for Pinecone indexer operations.

    Attributes:
        namespace: Pinecone namespace for data isolation.
    """

    namespace: str | None = Field(default=None, description='Pinecone namespace')


@dataclass
class PineconeIndexConfig:
    """Configuration for a Pinecone index.

    Attributes:
        index_id: Name of the Pinecone index.
        embedder: Genkit embedder reference (e.g., 'googleai/text-embedding-004').
        embedder_options: Optional embedder-specific configuration.
        client_params: Pinecone client configuration.
        content_key: Metadata key for document content (default: '_content').
    """

    index_id: str
    embedder: str
    embedder_options: dict[str, Any] | None = None
    client_params: dict[str, Any] | None = None
    content_key: str = CONTENT_KEY


@dataclass
class PineconePluginConfig:
    """Configuration for the Pinecone plugin.

    Attributes:
        indexes: List of index configurations.
    """

    indexes: list[PineconeIndexConfig] = field(default_factory=list)


def _md5_hash(content: str) -> str:
    """Generate MD5 hash of content for document ID."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _get_client(client_params: dict[str, Any] | None) -> PineconeClient:
    """Create a Pinecone client from configuration.

    Args:
        client_params: Client configuration. Uses PINECONE_API_KEY env var if not provided.

    Returns:
        Pinecone client instance.
    """
    api_key = None
    if client_params:
        api_key = client_params.get('api_key')
    if not api_key:
        api_key = os.environ.get('PINECONE_API_KEY')

    if not api_key:
        raise ValueError('Pinecone API key must be provided via client_params or PINECONE_API_KEY environment variable')

    return PineconeClient(api_key=api_key)


class PineconeRetriever:
    """Pinecone retriever implementation.

    Performs similarity search against a Pinecone index using
    embeddings generated by a Genkit embedder.
    """

    def __init__(
        self,
        registry: Registry,
        index_id: str,
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
        client_params: dict[str, Any] | None = None,
        content_key: str = CONTENT_KEY,
    ) -> None:
        """Initialize the Pinecone retriever.

        Args:
            registry: Registry for resolving embedders.
            index_id: Name of the Pinecone index.
            embedder: Embedder reference string.
            embedder_options: Optional embedder configuration.
            client_params: Pinecone client configuration.
            content_key: Metadata key for document content.
        """
        self._registry = registry
        self._index_id = index_id
        self._embedder = embedder
        self._embedder_options = embedder_options
        self._client_params = client_params
        self._content_key = content_key

    def _get_index(self) -> PineconeIndex:
        """Get the Pinecone index."""
        client = _get_client(self._client_params)
        return client.Index(self._index_id)

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
        namespace: str | None = None
        filter_dict: dict[str, Any] | None = None

        if request.options:
            opts = request.options if isinstance(request.options, dict) else request.options.model_dump()
            k = min(opts.get('k', 10), MAX_K)
            namespace = opts.get('namespace')
            filter_dict = opts.get('filter')

        # Query Pinecone
        index = self._get_index()
        results = index.query(
            vector=query_embedding,
            top_k=k,
            include_values=False,
            include_metadata=True,
            namespace=namespace,
            filter=filter_dict,
        )

        # Convert results to Documents
        documents: list[DocumentData] = []
        for match in results.get('matches', []):
            metadata = match.get('metadata', {})

            # Extract content
            content = metadata.get(self._content_key, '')
            content_type = metadata.get(CONTENT_TYPE_KEY, 'text')

            # Parse stored document metadata
            doc_metadata: dict[str, Any] = {}
            if 'doc_metadata' in metadata:
                try:
                    doc_metadata = json.loads(str(metadata['doc_metadata']))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning('Failed to parse document metadata', error=str(e))

            # Add score to metadata
            doc_metadata['_score'] = match.get('score', 0.0)

            # Reconstruct document
            doc = Document.from_data(
                data=content,
                data_type=content_type,
                metadata=doc_metadata,
            )
            # Document extends DocumentData, so it can be used directly
            documents.append(doc)

        return RetrieverResponse(documents=documents)


class PineconeIndexer:
    """Pinecone indexer implementation.

    Upserts documents with their embeddings to a Pinecone index.
    """

    def __init__(
        self,
        registry: Registry,
        index_id: str,
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
        client_params: dict[str, Any] | None = None,
        content_key: str = CONTENT_KEY,
    ) -> None:
        """Initialize the Pinecone indexer.

        Args:
            registry: Registry for resolving embedders.
            index_id: Name of the Pinecone index.
            embedder: Embedder reference string.
            embedder_options: Optional embedder configuration.
            client_params: Pinecone client configuration.
            content_key: Metadata key for document content.
        """
        self._registry = registry
        self._index_id = index_id
        self._embedder = embedder
        self._embedder_options = embedder_options
        self._client_params = client_params
        self._content_key = content_key

    def _get_index(self) -> PineconeIndex:
        """Get the Pinecone index."""
        client = _get_client(self._client_params)
        return client.Index(self._index_id)

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
        """Index documents into the Pinecone index.

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

        # Parse namespace from options
        namespace: str | None = None
        if request.options:
            opts = request.options if isinstance(request.options, dict) else {}
            namespace = opts.get('namespace')

        # Prepare vectors for Pinecone
        vectors: list[dict[str, Any]] = []

        for doc, embedding in zip(docs, embeddings, strict=True):
            # Get embedding documents (handles multi-part documents)
            from genkit.types import Embedding

            emb_obj = Embedding(embedding=embedding)
            embedding_docs = doc.get_embedding_documents([emb_obj])

            for emb_doc in embedding_docs:
                # Generate unique ID from content
                content = emb_doc.text() or json.dumps(emb_doc.data())
                doc_id = _md5_hash(content)

                # Prepare metadata
                metadata: dict[str, Any] = {
                    self._content_key: content,
                    CONTENT_TYPE_KEY: emb_doc.data_type() or 'text',
                }
                if emb_doc.metadata:
                    metadata['doc_metadata'] = json.dumps(emb_doc.metadata)

                vectors.append({
                    'id': doc_id,
                    'values': embedding,
                    'metadata': metadata,
                })

        # Upsert to Pinecone
        index = self._get_index()
        index.upsert(vectors=vectors, namespace=namespace)


class Pinecone(Plugin):
    """Pinecone vector store plugin for Genkit.

    This plugin registers retrievers and indexers for Pinecone indexes,
    enabling RAG (Retrieval-Augmented Generation) workflows.

    Example:
        ```python
        ai = Genkit(
            plugins=[
                Pinecone(
                    indexes=[
                        PineconeIndexConfig(
                            index_id='my-index',
                            embedder='googleai/text-embedding-004',
                        )
                    ]
                )
            ]
        )
        ```
    """

    name = PINECONE_PLUGIN_NAME

    def __init__(
        self,
        indexes: list[PineconeIndexConfig] | None = None,
    ) -> None:
        """Initialize the Pinecone plugin.

        Args:
            indexes: List of index configurations.
        """
        self._indexes = indexes or []
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
            for config in self._indexes:
                self._register_index(registry, config)
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
        for config in self._indexes:
            name = f'{PINECONE_PLUGIN_NAME}/{config.index_id}'
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

    def _register_index(
        self,
        registry: Registry,
        config: PineconeIndexConfig,
    ) -> None:
        """Register retriever and indexer for an index.

        Args:
            registry: Action registry.
            config: Index configuration.
        """
        name = f'{PINECONE_PLUGIN_NAME}/{config.index_id}'

        # Create and register retriever
        retriever = PineconeRetriever(
            registry=registry,
            index_id=config.index_id,
            embedder=config.embedder,
            embedder_options=config.embedder_options,
            client_params=config.client_params,
            content_key=config.content_key,
        )

        retriever_action = registry.register_action(
            kind=ActionKind.RETRIEVER,
            name=name,
            fn=retriever.retrieve,
            metadata=retriever_action_metadata(
                name=name,
                options=RetrieverOptions(
                    label=f'Pinecone - {config.index_id}',
                    config_schema=to_json_schema(PineconeRetrieverOptions),
                ),
            ).metadata,
        )
        if retriever_action:
            self._actions[f'{ActionKind.RETRIEVER.value}/{name}'] = retriever_action

        # Create and register indexer
        indexer = PineconeIndexer(
            registry=registry,
            index_id=config.index_id,
            embedder=config.embedder,
            embedder_options=config.embedder_options,
            client_params=config.client_params,
            content_key=config.content_key,
        )

        indexer_action = registry.register_action(
            kind=ActionKind.INDEXER,
            name=name,
            fn=indexer.index,
            metadata=indexer_action_metadata(
                name=name,
                options=IndexerOptions(label=f'Pinecone - {config.index_id}'),
            ).metadata,
        )
        if indexer_action:
            self._actions[f'{ActionKind.INDEXER.value}/{name}'] = indexer_action


def pinecone(
    indexes: list[dict[str, Any]] | None = None,
) -> Pinecone:
    """Create a Pinecone plugin with the given configuration.

    This is a convenience function for creating a Pinecone plugin instance.

    Args:
        indexes: List of index configuration dictionaries.

    Returns:
        Configured Pinecone plugin instance.

    Example:
        ```python
        ai = Genkit(
            plugins=[
                pinecone(
                    indexes=[
                        {
                            'index_id': 'my-index',
                            'embedder': 'googleai/text-embedding-004',
                        }
                    ]
                )
            ]
        )
        ```
    """
    configs = []
    if indexes:
        for idx in indexes:
            configs.append(
                PineconeIndexConfig(
                    index_id=idx['index_id'],
                    embedder=idx['embedder'],
                    embedder_options=idx.get('embedder_options'),
                    client_params=idx.get('client_params'),
                    content_key=idx.get('content_key', CONTENT_KEY),
                )
            )
    return Pinecone(indexes=configs)


def pinecone_retriever_ref(
    index_id: str,
    display_name: str | None = None,
) -> str:
    """Create a retriever reference for a Pinecone index.

    Args:
        index_id: Name of the Pinecone index.
        display_name: Optional display name (unused, for parity with JS).

    Returns:
        Retriever reference string.
    """
    return f'pinecone/{index_id}'


def pinecone_indexer_ref(
    index_id: str,
    display_name: str | None = None,
) -> str:
    """Create an indexer reference for a Pinecone index.

    Args:
        index_id: Name of the Pinecone index.
        display_name: Optional display name (unused, for parity with JS).

    Returns:
        Indexer reference string.
    """
    return f'pinecone/{index_id}'


async def create_pinecone_index(
    name: str,
    dimension: int,
    metric: str = 'cosine',
    client_params: dict[str, Any] | None = None,
    cloud: str = 'aws',
    region: str = 'us-east-1',
) -> dict[str, Any]:
    """Create a Pinecone index.

    Args:
        name: Index name.
        dimension: Vector dimension.
        metric: Distance metric ('cosine', 'euclidean', 'dotproduct').
        client_params: Pinecone client configuration.
        cloud: Cloud provider ('aws', 'gcp', 'azure').
        region: Cloud region.

    Returns:
        Index information dictionary.
    """
    client = _get_client(client_params)
    client.create_index(
        name=name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(cloud=cloud, region=region),
    )
    return {'name': name, 'dimension': dimension, 'metric': metric}


async def describe_pinecone_index(
    name: str,
    client_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe a Pinecone index.

    Args:
        name: Index name.
        client_params: Pinecone client configuration.

    Returns:
        Index information dictionary.
    """
    client = _get_client(client_params)
    description = client.describe_index(name)
    return {
        'name': description.name,
        'dimension': description.dimension,
        'metric': description.metric,
        'host': description.host,
        'status': description.status,
    }


async def delete_pinecone_index(
    name: str,
    client_params: dict[str, Any] | None = None,
) -> None:
    """Delete a Pinecone index.

    Args:
        name: Index name.
        client_params: Pinecone client configuration.
    """
    client = _get_client(client_params)
    client.delete_index(name)
