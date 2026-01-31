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

"""Tests for Cloud SQL PostgreSQL plugin."""

from unittest.mock import MagicMock

import pytest

from genkit.core.registry import ActionKind
from genkit.plugins.cloud_sql_pg import (
    POSTGRES_PLUGIN_NAME,
    CloudSqlPg,
    DistanceStrategy,
    PostgresIndexerOptions,
    PostgresRetrieverOptions,
    PostgresTableConfig,
    postgres,
    postgres_indexer_ref,
    postgres_retriever_ref,
)


class TestPostgresRetrieverOptions:
    """Tests for PostgresRetrieverOptions."""

    def test_default_values(self) -> None:
        """Test default values (k=4 matches JS default)."""
        options = PostgresRetrieverOptions()
        assert options.k == 4  # Matches JS default
        assert options.filter is None

    def test_custom_values(self) -> None:
        """Test custom values."""
        options = PostgresRetrieverOptions(k=50, filter="category = 'science'")
        assert options.k == 50
        assert options.filter == "category = 'science'"

    def test_k_max_limit(self) -> None:
        """Test that k has max limit of 1000."""
        with pytest.raises(ValueError):
            PostgresRetrieverOptions(k=1001)


class TestPostgresIndexerOptions:
    """Tests for PostgresIndexerOptions."""

    def test_default_values(self) -> None:
        """Test default values."""
        options = PostgresIndexerOptions()
        assert options.batch_size == 100

    def test_custom_values(self) -> None:
        """Test custom values."""
        options = PostgresIndexerOptions(batch_size=50)
        assert options.batch_size == 50


class TestPostgresTableConfig:
    """Tests for PostgresTableConfig."""

    def test_required_fields(self) -> None:
        """Test required fields."""
        engine = MagicMock()
        config = PostgresTableConfig(
            table_name='documents',
            engine=engine,
            embedder='googleai/text-embedding-004',
        )
        assert config.table_name == 'documents'
        assert config.engine is engine
        assert config.embedder == 'googleai/text-embedding-004'

    def test_default_values(self) -> None:
        """Test default values."""
        engine = MagicMock()
        config = PostgresTableConfig(
            table_name='documents',
            engine=engine,
            embedder='googleai/text-embedding-004',
        )
        assert config.schema_name == 'public'
        assert config.content_column == 'content'
        assert config.embedding_column == 'embedding'
        assert config.id_column == 'id'
        assert config.metadata_columns is None
        assert config.ignore_metadata_columns is None
        assert config.metadata_json_column == 'metadata'
        assert config.distance_strategy == DistanceStrategy.COSINE_DISTANCE
        assert config.index_query_options is None

    def test_custom_values(self) -> None:
        """Test custom values."""
        engine = MagicMock()
        config = PostgresTableConfig(
            table_name='my_docs',
            engine=engine,
            embedder='vertexai/text-embedding-005',
            schema_name='custom_schema',
            content_column='text',
            embedding_column='vector',
            id_column='doc_id',
            metadata_columns=['category', 'author'],
            distance_strategy=DistanceStrategy.EUCLIDEAN,
        )
        assert config.table_name == 'my_docs'
        assert config.schema_name == 'custom_schema'
        assert config.content_column == 'text'
        assert config.embedding_column == 'vector'
        assert config.id_column == 'doc_id'
        assert config.metadata_columns == ['category', 'author']
        assert config.distance_strategy == DistanceStrategy.EUCLIDEAN


class TestReferenceHelpers:
    """Tests for reference helper functions."""

    def test_postgres_retriever_ref(self) -> None:
        """Test postgres_retriever_ref returns correct format."""
        ref = postgres_retriever_ref('documents')
        assert ref == 'postgres/documents'

    def test_postgres_retriever_ref_with_display_name(self) -> None:
        """Test postgres_retriever_ref with display name (unused)."""
        ref = postgres_retriever_ref('documents', display_name='My Documents')
        assert ref == 'postgres/documents'

    def test_postgres_indexer_ref(self) -> None:
        """Test postgres_indexer_ref returns correct format."""
        ref = postgres_indexer_ref('documents')
        assert ref == 'postgres/documents'

    def test_postgres_indexer_ref_with_display_name(self) -> None:
        """Test postgres_indexer_ref with display name (unused)."""
        ref = postgres_indexer_ref('documents', display_name='My Documents')
        assert ref == 'postgres/documents'


class TestCloudSqlPgPlugin:
    """Tests for CloudSqlPg plugin class."""

    def test_plugin_name(self) -> None:
        """Test plugin name is correct."""
        plugin = CloudSqlPg()
        assert plugin.name == POSTGRES_PLUGIN_NAME
        assert plugin.name == 'postgres'

    def test_empty_initialization(self) -> None:
        """Test initialization with no tables."""
        plugin = CloudSqlPg()
        assert plugin._tables == []

    def test_initialization_with_tables(self) -> None:
        """Test initialization with tables."""
        engine = MagicMock()
        config = PostgresTableConfig(
            table_name='documents',
            engine=engine,
            embedder='googleai/text-embedding-004',
        )
        plugin = CloudSqlPg(tables=[config])
        assert len(plugin._tables) == 1
        assert plugin._tables[0] == config

    @pytest.mark.asyncio
    async def test_init_without_registry(self) -> None:
        """Test init without registry."""
        plugin = CloudSqlPg()
        actions = await plugin.init(registry=None)
        assert actions == []

    @pytest.mark.asyncio
    async def test_list_actions(self) -> None:
        """Test list_actions returns correct metadata."""
        engine = MagicMock()
        config = PostgresTableConfig(
            table_name='documents',
            engine=engine,
            embedder='googleai/text-embedding-004',
        )
        plugin = CloudSqlPg(tables=[config])

        actions = await plugin.list_actions()

        assert len(actions) == 2  # One retriever, one indexer

        retriever_meta = actions[0]
        assert retriever_meta.kind == ActionKind.RETRIEVER
        assert retriever_meta.name == 'postgres/documents'

        indexer_meta = actions[1]
        assert indexer_meta.kind == ActionKind.INDEXER
        assert indexer_meta.name == 'postgres/documents'

    @pytest.mark.asyncio
    async def test_resolve_unknown_action(self) -> None:
        """Test resolve returns None for unknown action."""
        plugin = CloudSqlPg()
        await plugin.init(registry=None)

        result = await plugin.resolve(ActionKind.RETRIEVER, 'unknown')
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_wrong_kind(self) -> None:
        """Test resolve returns None for wrong action kind."""
        plugin = CloudSqlPg()
        await plugin.init(registry=None)

        result = await plugin.resolve(ActionKind.MODEL, 'postgres/documents')
        assert result is None


class TestPostgresConvenienceFunction:
    """Tests for postgres() convenience function."""

    def test_empty_tables(self) -> None:
        """Test with no tables."""
        plugin = postgres()
        assert isinstance(plugin, CloudSqlPg)
        assert plugin._tables == []

    def test_with_table_config_dicts(self) -> None:
        """Test with table configuration dictionaries."""
        engine = MagicMock()
        plugin = postgres(
            tables=[
                {
                    'table_name': 'documents',
                    'engine': engine,
                    'embedder': 'googleai/text-embedding-004',
                },
                {
                    'table_name': 'articles',
                    'engine': engine,
                    'embedder': 'vertexai/text-embedding-005',
                    'schema_name': 'public',
                    'content_column': 'body',
                    'distance_strategy': DistanceStrategy.INNER_PRODUCT,
                },
            ]
        )

        assert isinstance(plugin, CloudSqlPg)
        assert len(plugin._tables) == 2

        # Check first table config
        config1 = plugin._tables[0]
        assert config1.table_name == 'documents'
        assert config1.embedder == 'googleai/text-embedding-004'

        # Check second table config
        config2 = plugin._tables[1]
        assert config2.table_name == 'articles'
        assert config2.embedder == 'vertexai/text-embedding-005'
        assert config2.content_column == 'body'
        assert config2.distance_strategy == DistanceStrategy.INNER_PRODUCT
