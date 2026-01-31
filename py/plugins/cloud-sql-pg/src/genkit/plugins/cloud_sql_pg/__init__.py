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

"""Cloud SQL PostgreSQL vector store plugin for Genkit.

This plugin provides a vector store implementation for Cloud SQL for PostgreSQL
with pgvector support, enabling RAG (Retrieval-Augmented Generation) workflows.

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.google_genai import GoogleAI
    from genkit.plugins.cloud_sql_pg import (
        CloudSqlPg,
        PostgresEngine,
        PostgresTableConfig,
    )

    # Create the engine
    engine = await PostgresEngine.from_instance(
        project_id='your-project-id',
        region='us-central1',
        instance='your-instance',
        database='your-database',
        user='your-user',
        password='your-password',
    )

    # Initialize Genkit with the plugin
    ai = Genkit(
        plugins=[
            GoogleAI(),
            CloudSqlPg(
                tables=[
                    PostgresTableConfig(
                        table_name='documents',
                        engine=engine,
                        embedder='googleai/text-embedding-004',
                    )
                ]
            ),
        ]
    )

    # Index documents
    await ai.index(
        indexer='postgres/documents',
        documents=[Document.from_text('Hello, world!')],
    )

    # Retrieve similar documents
    response = await ai.retrieve(
        retriever='postgres/documents',
        query=Document.from_text('greeting'),
        options={'k': 5},
    )
    ```
"""

__version__ = '1.0.0'

from .engine import Column, IpAddressTypes, PostgresEngine, VectorStoreTableArgs
from .indexes import (
    DEFAULT_DISTANCE_STRATEGY,
    DEFAULT_INDEX_NAME_SUFFIX,
    BaseIndex,
    DistanceStrategy,
    ExactNearestNeighbor,
    HNSWIndex,
    HNSWQueryOptions,
    IVFFlatIndex,
    IVFFlatQueryOptions,
    QueryOptions,
)
from .plugin import (
    POSTGRES_PLUGIN_NAME,
    CloudSqlPg,
    PostgresIndexer,
    PostgresIndexerOptions,
    PostgresRetriever,
    PostgresRetrieverOptions,
    PostgresTableConfig,
    configure_postgres_indexer,
    configure_postgres_retriever,
    postgres,
    postgres_indexer_ref,
    postgres_retriever_ref,
)

__all__ = [
    # Plugin
    'CloudSqlPg',
    'POSTGRES_PLUGIN_NAME',
    'postgres',
    # Engine
    'PostgresEngine',
    'Column',
    'IpAddressTypes',
    'VectorStoreTableArgs',
    # Configuration
    'PostgresTableConfig',
    'PostgresRetrieverOptions',
    'PostgresIndexerOptions',
    # Retriever/Indexer
    'PostgresRetriever',
    'PostgresIndexer',
    'postgres_retriever_ref',
    'postgres_indexer_ref',
    'configure_postgres_retriever',
    'configure_postgres_indexer',
    # Indexes
    'DistanceStrategy',
    'DEFAULT_DISTANCE_STRATEGY',
    'DEFAULT_INDEX_NAME_SUFFIX',
    'BaseIndex',
    'ExactNearestNeighbor',
    'HNSWIndex',
    'IVFFlatIndex',
    'QueryOptions',
    'HNSWQueryOptions',
    'IVFFlatQueryOptions',
]
