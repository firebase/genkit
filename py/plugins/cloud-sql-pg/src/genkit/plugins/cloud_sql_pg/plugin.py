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

"""Cloud SQL PostgreSQL plugin implementation for Genkit.

This module provides the core plugin functionality for integrating Cloud SQL
PostgreSQL with Genkit applications, including retriever and indexer implementations.

Key Components
==============

┌───────────────────────────────────────────────────────────────────────────┐
│                         Plugin Components                                   │
├───────────────────────┬───────────────────────────────────────────────────┤
│ Component             │ Purpose                                           │
├───────────────────────┼───────────────────────────────────────────────────┤
│ CloudSqlPg            │ Main plugin class - registers retrievers/indexers │
│ PostgresRetriever     │ Similarity search against PostgreSQL tables       │
│ PostgresIndexer       │ Store documents with embeddings in PostgreSQL     │
│ postgres_retriever_ref│ Create retriever reference by table name          │
│ postgres_indexer_ref  │ Create indexer reference by table name            │
└───────────────────────┴───────────────────────────────────────────────────┘

See Also:
    - JS Implementation: js/plugins/cloud-sql-pg/src/index.ts
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, cast

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text

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

from .engine import PostgresEngine
from .indexes import DEFAULT_DISTANCE_STRATEGY, DistanceStrategy, QueryOptions

logger = structlog.get_logger(__name__)

POSTGRES_PLUGIN_NAME = 'postgres'
MAX_K = 1000
DEFAULT_BATCH_SIZE = 100


class PostgresRetrieverOptions(BaseModel):
    """Options for PostgreSQL retriever queries.

    Attributes:
        k: Number of results to return (default: 4, max: 1000).
        filter: SQL WHERE clause for filtering results.
    """

    k: int = Field(default=4, le=MAX_K, description='Number of results to return')
    filter: str | None = Field(default=None, description='SQL WHERE clause filter')


class PostgresIndexerOptions(BaseModel):
    """Options for PostgreSQL indexer operations.

    Attributes:
        batch_size: Number of documents to process per batch (default: 100).
    """

    batch_size: int = Field(default=DEFAULT_BATCH_SIZE, description='Batch size for processing')


@dataclass
class PostgresTableConfig:
    """Configuration for a PostgreSQL vector store table.

    Attributes:
        table_name: Name of the PostgreSQL table.
        engine: PostgresEngine instance for database operations.
        embedder: Genkit embedder reference (e.g., 'googleai/text-embedding-004').
        embedder_options: Optional embedder-specific configuration.
        schema_name: PostgreSQL schema name (default: 'public').
        content_column: Column name for document content (default: 'content').
        embedding_column: Column name for vector embeddings (default: 'embedding').
        id_column: Column name for document IDs (default: 'id').
        metadata_columns: List of specific metadata column names to use.
        ignore_metadata_columns: List of metadata columns to ignore.
        metadata_json_column: Column name for JSON metadata (default: 'metadata').
        distance_strategy: Vector distance strategy (default: COSINE_DISTANCE).
        index_query_options: Optional index-specific query options.
    """

    table_name: str
    engine: PostgresEngine
    embedder: str
    embedder_options: dict[str, Any] | None = None
    schema_name: str = 'public'
    content_column: str = 'content'
    embedding_column: str = 'embedding'
    id_column: str = 'id'
    metadata_columns: list[str] | None = None
    ignore_metadata_columns: list[str] | None = None
    metadata_json_column: str = 'metadata'
    distance_strategy: DistanceStrategy = field(default_factory=lambda: DEFAULT_DISTANCE_STRATEGY)
    index_query_options: QueryOptions | None = None


class PostgresRetriever:
    """PostgreSQL retriever implementation.

    Performs similarity search against a PostgreSQL table using
    pgvector and embeddings generated by a Genkit embedder.
    """

    def __init__(
        self,
        registry: Registry,
        config: PostgresTableConfig,
    ) -> None:
        """Initialize the PostgreSQL retriever.

        Args:
            registry: Registry for resolving embedders.
            config: Table configuration.
        """
        self._registry = registry
        self._config = config
        self._columns_checked = False

    async def _check_columns(self) -> None:
        """Validate that required columns exist in the table."""
        if self._columns_checked:
            return

        config = self._config

        if config.metadata_columns is not None and config.ignore_metadata_columns is not None:
            raise ValueError('Cannot use both metadata_columns and ignore_metadata_columns')

        async with config.engine.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = :table_name AND table_schema = :schema_name
                """),
                {'table_name': config.table_name, 'schema_name': config.schema_name},
            )
            rows = result.fetchall()

        columns: dict[str, str] = {}
        for row in rows:
            columns[row[0]] = row[1]

        # Validate ID column
        if config.id_column and config.id_column not in columns:
            raise ValueError(f'Id column: {config.id_column}, does not exist.')

        # Validate content column
        if config.content_column not in columns:
            raise ValueError(f'Content column: {config.content_column}, does not exist.')

        content_type = columns.get(config.content_column, '')
        if content_type != 'text' and 'char' not in content_type:
            raise ValueError(
                f'Content column: {config.content_column}, is type: {content_type}. '
                'It must be a type of character string.'
            )

        # Validate embedding column
        if config.embedding_column not in columns:
            raise ValueError(f'Embedding column: {config.embedding_column}, does not exist.')

        # pgvector types show as USER-DEFINED
        if columns.get(config.embedding_column) != 'USER-DEFINED':
            raise ValueError(f'Embedding column: {config.embedding_column} is not of type Vector.')

        # Check if metadata JSON column exists (match JS behavior)
        metadata_json_column_to_check = config.metadata_json_column or ''
        if metadata_json_column_to_check and metadata_json_column_to_check not in columns:
            # If it doesn't exist, clear it (match JS: params.metadataJsonColumn = '')
            config.metadata_json_column = ''

        # Validate metadata columns
        if config.metadata_columns:
            for col in config.metadata_columns:
                if col and col not in columns:
                    raise ValueError(f'Metadata column: {col}, does not exist.')

        # Auto-populate metadata_columns from ignore_metadata_columns (match JS behavior)
        if config.ignore_metadata_columns is not None and len(config.ignore_metadata_columns) > 0:
            all_columns = dict(columns)
            # Remove ignored columns
            for col in config.ignore_metadata_columns:
                all_columns.pop(col, None)
            # Remove system columns
            if config.id_column:
                all_columns.pop(config.id_column, None)
            all_columns.pop(config.content_column, None)
            all_columns.pop(config.embedding_column, None)
            # Set metadata_columns to remaining columns
            config.metadata_columns = list(all_columns.keys())

        self._columns_checked = True

    async def _embed_content(self, content: list[Document]) -> list[list[float]]:
        """Generate embeddings using the registry-resolved embedder."""
        embedder_action = await self._registry.resolve_embedder(self._config.embedder)
        if embedder_action is None:
            raise ValueError(f'Embedder "{self._config.embedder}" not found')

        request = EmbedRequest(input=cast(list[DocumentData], content), options=self._config.embedder_options)
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
        await self._check_columns()

        config = self._config

        # Generate query embedding
        query_doc = Document.from_document_data(document_data=request.query)
        embeddings = await self._embed_content([query_doc])
        if not embeddings:
            raise ValueError('Embedder returned no embeddings for query')

        query_embedding = embeddings[0]

        # Parse options - JS default k is 4
        k = 4
        filter_clause = ''

        if request.options:
            opts = request.options if isinstance(request.options, dict) else request.options.model_dump()
            k = min(opts.get('k', 4), MAX_K)
            if opts.get('filter'):
                filter_clause = f'WHERE {opts["filter"]}'

        # Build metadata column selection
        metadata_col_names = ''
        if config.metadata_columns and len(config.metadata_columns) > 0:
            metadata_col_names = ', ' + ', '.join(f'"{col}"' for col in config.metadata_columns)

        metadata_json_col = ''
        if config.metadata_json_column:
            metadata_json_col = f', "{config.metadata_json_column}"'

        # Build query
        operator = config.distance_strategy.operator
        search_function = config.distance_strategy.search_function
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        query = f'''
            SELECT "{config.id_column}", "{config.content_column}", "{config.embedding_column}"
            {metadata_col_names} {metadata_json_col},
            {search_function}("{config.embedding_column}", '{embedding_str}') as distance
            FROM "{config.schema_name}"."{config.table_name}"
            {filter_clause}
            ORDER BY "{config.embedding_column}" {operator} '{embedding_str}'
            LIMIT {k}
        '''

        async with config.engine.engine.connect() as conn:
            # Set index query options if provided
            if config.index_query_options:
                await conn.execute(text(f'SET LOCAL {config.index_query_options.to_string()}'))

            result = await conn.execute(text(query))
            rows = result.fetchall()

        # Convert results to Documents
        documents: list[DocumentData] = []
        for row in rows:
            # Get column values by position
            row_dict = dict(row._mapping)

            # Build metadata
            metadata: dict[str, Any] = {}

            # Add JSON metadata if exists
            if config.metadata_json_column and config.metadata_json_column in row_dict:
                json_meta = row_dict.get(config.metadata_json_column)
                if json_meta:
                    if isinstance(json_meta, str):
                        try:
                            metadata = json.loads(json_meta)
                        except json.JSONDecodeError as e:
                            logger.warning('Failed to parse document metadata', error=str(e))
                    elif isinstance(json_meta, dict):
                        metadata = dict(json_meta)

            # Add individual metadata columns
            if config.metadata_columns:
                for col in config.metadata_columns:
                    if col in row_dict:
                        metadata[col] = row_dict[col]

            # Add distance to metadata
            metadata['_distance'] = row_dict.get('distance')

            # Create document
            content = row_dict.get(config.content_column, '')
            doc = Document.from_data(
                data=content,
                data_type='text',
                metadata=metadata,
            )
            documents.append(doc)

        return RetrieverResponse(documents=documents)


class PostgresIndexer:
    """PostgreSQL indexer implementation.

    Stores documents with their embeddings in a PostgreSQL table.
    """

    def __init__(
        self,
        registry: Registry,
        config: PostgresTableConfig,
    ) -> None:
        """Initialize the PostgreSQL indexer.

        Args:
            registry: Registry for resolving embedders.
            config: Table configuration.
        """
        self._registry = registry
        self._config = config
        self._columns_checked = False

    async def _check_columns(self) -> None:
        """Validate that required columns exist in the table."""
        if self._columns_checked:
            return

        config = self._config

        if config.metadata_columns is not None and config.ignore_metadata_columns is not None:
            raise ValueError('Cannot use both metadata_columns and ignore_metadata_columns')

        async with config.engine.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = :table_name AND table_schema = :schema_name
                """),
                {'table_name': config.table_name, 'schema_name': config.schema_name},
            )
            rows = result.fetchall()

        columns: dict[str, str] = {}
        for row in rows:
            columns[row[0]] = row[1]

        # Validate required columns
        if config.id_column not in columns:
            raise ValueError(f'Id column: {config.id_column}, does not exist.')

        if config.content_column not in columns:
            raise ValueError(f'Content column: {config.content_column}, does not exist.')

        if config.embedding_column not in columns:
            raise ValueError(f'Embedding column: {config.embedding_column}, does not exist.')

        if columns.get(config.embedding_column) != 'USER-DEFINED':
            raise ValueError(f'Embedding column: {config.embedding_column} is not of type Vector.')

        if config.metadata_columns:
            for col in config.metadata_columns:
                if col and col not in columns:
                    raise ValueError(f'Metadata column: {col}, does not exist.')

        self._columns_checked = True

    async def _embed_content(self, content: list[Document]) -> list[list[float]]:
        """Generate embeddings using the registry-resolved embedder."""
        embedder_action = await self._registry.resolve_embedder(self._config.embedder)
        if embedder_action is None:
            raise ValueError(f'Embedder "{self._config.embedder}" not found')

        request = EmbedRequest(input=cast(list[DocumentData], content), options=self._config.embedder_options)
        response = await embedder_action.arun(request)
        return [e.embedding for e in response.response.embeddings]

    async def index(self, request: IndexerRequest) -> None:
        """Index documents into the PostgreSQL table.

        Args:
            request: Indexer request containing documents to index.
        """
        if not request.documents:
            return

        await self._check_columns()

        config = self._config

        # Parse options
        batch_size = DEFAULT_BATCH_SIZE
        if request.options:
            opts = request.options if isinstance(request.options, dict) else request.options.model_dump()
            batch_size = opts.get('batch_size', DEFAULT_BATCH_SIZE)

        # Convert to Document objects
        docs = [Document.from_document_data(doc) for doc in request.documents]

        # Process in batches
        for i in range(0, len(docs), batch_size):
            chunk = docs[i : i + batch_size]

            # Get text content for each document
            texts = []
            for doc in chunk:
                if isinstance(doc.content, list):
                    # Join multiple parts
                    text_parts = []
                    for part in doc.content:
                        if hasattr(part, 'text'):
                            text_parts.append(part.text or '')
                    texts.append(' '.join(text_parts))
                else:
                    texts.append(str(doc.content) if doc.content else '')

            # Generate embeddings
            try:
                embeddings = await self._embed_content(chunk)
            except Exception as e:
                raise ValueError('Embedding failed') from e

            # Prepare insert data
            insert_data = []
            for doc, text_content, embedding in zip(chunk, texts, embeddings, strict=True):
                # Generate ID from metadata or create new UUID
                doc_id = doc.metadata.get(config.id_column) if doc.metadata else None
                if not doc_id:
                    doc_id = str(uuid.uuid4())

                # Build row data
                row_data: dict[str, Any] = {
                    config.id_column: doc_id,
                    config.content_column: text_content,
                    config.embedding_column: '[' + ','.join(str(x) for x in embedding) + ']',
                }

                # Add JSON metadata
                if config.metadata_json_column:
                    row_data[config.metadata_json_column] = json.dumps(doc.metadata or {})

                # Add individual metadata columns
                if config.metadata_columns and doc.metadata:
                    for col in config.metadata_columns:
                        if col in doc.metadata:
                            row_data[col] = doc.metadata[col]

                insert_data.append(row_data)

            # Build and execute INSERT query
            if insert_data:
                columns = list(insert_data[0].keys())
                col_names = ', '.join(f'"{col}"' for col in columns)

                # Build VALUES clause with parameterized values
                values_clauses = []
                params: dict[str, Any] = {}
                for idx, row in enumerate(insert_data):
                    placeholders = []
                    for col in columns:
                        param_name = f'{col}_{idx}'
                        placeholders.append(f':{param_name}')
                        params[param_name] = row[col]
                    values_clauses.append(f'({", ".join(placeholders)})')

                query = f'''
                    INSERT INTO "{config.schema_name}"."{config.table_name}" ({col_names})
                    VALUES {', '.join(values_clauses)}
                '''

                async with config.engine.engine.begin() as conn:
                    await conn.execute(text(query), params)


class CloudSqlPg(Plugin):
    """Cloud SQL PostgreSQL vector store plugin for Genkit.

    This plugin registers retrievers and indexers for PostgreSQL tables
    with pgvector support, enabling RAG (Retrieval-Augmented Generation) workflows.

    Example:
        ```python
        engine = await PostgresEngine.from_instance(
            project_id='my-project',
            region='us-central1',
            instance='my-instance',
            database='my-database',
        )

        ai = Genkit(
            plugins=[
                CloudSqlPg(
                    tables=[
                        PostgresTableConfig(
                            table_name='documents',
                            engine=engine,
                            embedder='googleai/text-embedding-004',
                        )
                    ]
                )
            ]
        )
        ```
    """

    name = POSTGRES_PLUGIN_NAME

    def __init__(
        self,
        tables: list[PostgresTableConfig] | None = None,
    ) -> None:
        """Initialize the Cloud SQL PostgreSQL plugin.

        Args:
            tables: List of table configurations.
        """
        self._tables = tables or []
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
            for config in self._tables:
                self._register_table(registry, config)
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
        action_key = f'{action_type.value}/{name}'
        return self._actions.get(action_key)

    async def list_actions(self) -> list[ActionMetadata]:
        """List available actions for dev UI.

        Returns:
            List of action metadata.
        """
        metadata_list: list[ActionMetadata] = []
        for config in self._tables:
            name = f'{POSTGRES_PLUGIN_NAME}/{config.table_name}'
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

    def _register_table(
        self,
        registry: Registry,
        config: PostgresTableConfig,
    ) -> None:
        """Register retriever and indexer for a table.

        Args:
            registry: Action registry.
            config: Table configuration.
        """
        name = f'{POSTGRES_PLUGIN_NAME}/{config.table_name}'

        # Create and register retriever
        retriever = PostgresRetriever(registry=registry, config=config)

        retriever_action = registry.register_action(
            kind=ActionKind.RETRIEVER,
            name=name,
            fn=retriever.retrieve,
            metadata=retriever_action_metadata(
                name=name,
                options=RetrieverOptions(
                    label=f'Postgres - {config.table_name}',
                    config_schema=to_json_schema(PostgresRetrieverOptions),
                ),
            ).metadata,
        )
        if retriever_action:
            self._actions[f'{ActionKind.RETRIEVER.value}/{name}'] = retriever_action

        # Create and register indexer
        indexer = PostgresIndexer(registry=registry, config=config)

        indexer_action = registry.register_action(
            kind=ActionKind.INDEXER,
            name=name,
            fn=indexer.index,
            metadata=indexer_action_metadata(
                name=name,
                options=IndexerOptions(label=f'Postgres - {config.table_name}'),
            ).metadata,
        )
        if indexer_action:
            self._actions[f'{ActionKind.INDEXER.value}/{name}'] = indexer_action


def postgres(
    tables: list[dict[str, Any]] | None = None,
) -> CloudSqlPg:
    """Create a Cloud SQL PostgreSQL plugin with the given configuration.

    This is a convenience function for creating a CloudSqlPg plugin instance.

    Args:
        tables: List of table configuration dictionaries.

    Returns:
        Configured CloudSqlPg plugin instance.

    Example:
        ```python
        ai = Genkit(
            plugins=[
                postgres(
                    tables=[
                        {
                            'table_name': 'documents',
                            'engine': engine,
                            'embedder': 'googleai/text-embedding-004',
                        }
                    ]
                )
            ]
        )
        ```
    """
    configs = []
    if tables:
        for t in tables:
            configs.append(
                PostgresTableConfig(
                    table_name=t['table_name'],
                    engine=t['engine'],
                    embedder=t['embedder'],
                    embedder_options=t.get('embedder_options'),
                    schema_name=t.get('schema_name', 'public'),
                    content_column=t.get('content_column', 'content'),
                    embedding_column=t.get('embedding_column', 'embedding'),
                    id_column=t.get('id_column', 'id'),
                    metadata_columns=t.get('metadata_columns'),
                    ignore_metadata_columns=t.get('ignore_metadata_columns'),
                    metadata_json_column=t.get('metadata_json_column', 'metadata'),
                    distance_strategy=t.get('distance_strategy', DEFAULT_DISTANCE_STRATEGY),
                    index_query_options=t.get('index_query_options'),
                )
            )
    return CloudSqlPg(tables=configs)


def postgres_retriever_ref(
    table_name: str,
    display_name: str | None = None,
) -> str:
    """Create a retriever reference for a PostgreSQL table.

    Args:
        table_name: Name of the PostgreSQL table.
        display_name: Optional display name (unused, for parity with JS).

    Returns:
        Retriever reference string.
    """
    return f'{POSTGRES_PLUGIN_NAME}/{table_name}'


def postgres_indexer_ref(
    table_name: str,
    display_name: str | None = None,
) -> str:
    """Create an indexer reference for a PostgreSQL table.

    Args:
        table_name: Name of the PostgreSQL table.
        display_name: Optional display name (unused, for parity with JS).

    Returns:
        Indexer reference string.
    """
    return f'{POSTGRES_PLUGIN_NAME}/{table_name}'


def configure_postgres_retriever(
    ai: Any,  # noqa: ANN401
    config: PostgresTableConfig,
) -> Action | None:
    """Configure a PostgreSQL retriever outside of the plugin.

    This function allows configuring retrievers independently of the plugin,
    matching the JS API.

    Args:
        ai: Genkit instance (uses internal _registry attribute).
        config: Table configuration.

    Returns:
        Configured retriever action.
    """
    registry = ai._registry  # noqa: SLF001
    retriever = PostgresRetriever(registry=registry, config=config)
    name = f'{POSTGRES_PLUGIN_NAME}/{config.table_name}'

    return registry.register_action(
        kind=ActionKind.RETRIEVER,
        name=name,
        fn=retriever.retrieve,
        metadata=retriever_action_metadata(
            name=name,
            options=RetrieverOptions(
                label=f'Postgres - {config.table_name}',
                config_schema=to_json_schema(PostgresRetrieverOptions),
            ),
        ).metadata,
    )


def configure_postgres_indexer(
    ai: Any,  # noqa: ANN401
    config: PostgresTableConfig,
) -> Action | None:
    """Configure a PostgreSQL indexer outside of the plugin.

    This function allows configuring indexers independently of the plugin,
    matching the JS API.

    Args:
        ai: Genkit instance (uses internal _registry attribute).
        config: Table configuration.

    Returns:
        Configured indexer action.
    """
    registry = ai._registry  # noqa: SLF001
    indexer = PostgresIndexer(registry=registry, config=config)
    name = f'{POSTGRES_PLUGIN_NAME}/{config.table_name}'

    return registry.register_action(
        kind=ActionKind.INDEXER,
        name=name,
        fn=indexer.index,
        metadata=indexer_action_metadata(
            name=name,
            options=IndexerOptions(label=f'Postgres - {config.table_name}'),
        ).metadata,
    )
