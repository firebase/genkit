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

"""PostgreSQL engine for Cloud SQL vector store operations.

This module provides the PostgresEngine class for managing connections
to Cloud SQL PostgreSQL instances and performing vector store operations.

Key Components
==============

┌───────────────────────────────────────────────────────────────────────────┐
│                         Engine Components                                  │
├───────────────────────┬───────────────────────────────────────────────────┤
│ Component             │ Purpose                                           │
├───────────────────────┼───────────────────────────────────────────────────┤
│ PostgresEngine        │ Main engine class for database operations         │
│ Column                │ Column definition for custom metadata columns     │
│ IpAddressTypes        │ IP address type enum (PUBLIC, PRIVATE)            │
└───────────────────────┴───────────────────────────────────────────────────┘

See Also:
    - JS Implementation: js/plugins/cloud-sql-pg/src/engine.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .indexes import DEFAULT_INDEX_NAME_SUFFIX, BaseIndex, ExactNearestNeighbor

USER_AGENT = 'genkit-cloud-sql-pg-python'


class IpAddressTypes(Enum):
    """IP address types for Cloud SQL connections.

    Attributes:
        PUBLIC: Connect via public IP address.
        PRIVATE: Connect via private IP address (VPC).
    """

    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'

    def to_ip_types(self) -> IPTypes:
        """Convert to Cloud SQL Connector IPTypes."""
        if self == IpAddressTypes.PRIVATE:
            return IPTypes.PRIVATE
        return IPTypes.PUBLIC


@dataclass
class Column:
    """Database column definition.

    Attributes:
        name: Column name.
        data_type: PostgreSQL data type (e.g., 'TEXT', 'INT', 'UUID').
        nullable: Whether the column can be NULL.
    """

    name: str
    data_type: str
    nullable: bool = True

    def __post_init__(self) -> None:
        """Validate column definition."""
        if not isinstance(self.name, str):
            raise TypeError('Column name must be a string')
        if not isinstance(self.data_type, str):
            raise TypeError('Column data_type must be a string')


@dataclass
class VectorStoreTableArgs:
    """Arguments for creating a vector store table.

    Attributes:
        schema_name: PostgreSQL schema name (default: 'public').
        content_column: Column name for document content (default: 'content').
        embedding_column: Column name for vector embeddings (default: 'embedding').
        metadata_columns: List of custom metadata columns.
        metadata_json_column: Column name for JSON metadata (default: 'json_metadata').
        id_column: Column name or Column object for IDs (default: 'id' with UUID type).
        overwrite_existing: Drop existing table if exists (default: False).
        store_metadata: Whether to create JSON metadata column (default: True).
        concurrently: Build index concurrently (default: False).
        index_name: Optional custom index name.
    """

    schema_name: str = 'public'
    content_column: str = 'content'
    embedding_column: str = 'embedding'
    metadata_columns: list[Column] | None = None
    metadata_json_column: str = 'json_metadata'
    id_column: str | Column = 'id'
    overwrite_existing: bool = False
    store_metadata: bool = True
    concurrently: bool = False
    index_name: str | None = None


def _strip_service_account_domain(email: str) -> str:
    """Strip .gserviceaccount.com domain from service account email.

    This matches the JS behavior in getIAMPrincipalEmail.

    Args:
        email: The email address.

    Returns:
        Email with .gserviceaccount.com stripped if present.
    """
    return email.replace('.gserviceaccount.com', '')


async def _get_iam_principal_email() -> str:
    """Get the IAM principal email from application default credentials.

    This matches the JS getIAMPrincipalEmail function behavior.

    Returns:
        The IAM principal email (service account or user email),
        with .gserviceaccount.com stripped for service accounts.

    Raises:
        ValueError: If unable to determine IAM principal email.
    """
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)

    # For service accounts, the email is in the credentials
    if hasattr(credentials, 'service_account_email'):
        return _strip_service_account_domain(credentials.service_account_email)

    # For user credentials, we need to get the email differently
    if hasattr(credentials, '_service_account_email'):
        return _strip_service_account_domain(credentials._service_account_email)

    # Try to get from token info
    if hasattr(credentials, 'token'):
        # For user credentials, parse the token
        try:
            request = google.auth.transport.requests.Request()
            id_info = google.oauth2.id_token.verify_oauth2_token(credentials.token, request)
            if 'email' in id_info:
                return _strip_service_account_domain(id_info['email'])
        except Exception:
            pass

    raise ValueError(
        "Failed to automatically obtain authenticated IAM principal's "
        "email address using environment's ADC credentials!"
    )


class PostgresEngine:
    """PostgreSQL engine for Cloud SQL vector store operations.

    This class manages connections to Cloud SQL PostgreSQL instances
    and provides methods for vector store table management.

    Example:
        ```python
        # Using Cloud SQL Connector with IAM auth
        engine = await PostgresEngine.from_instance(
            project_id='my-project',
            region='us-central1',
            instance='my-instance',
            database='my-database',
        )

        # Initialize vector store table
        await engine.init_vectorstore_table(
            table_name='documents',
            vector_size=768,
        )
        ```
    """

    _connector: Connector | None = None

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize PostgresEngine with an async engine.

        Use factory methods (from_instance, from_engine, from_connection_string)
        to create instances.

        Args:
            engine: SQLAlchemy async engine.
        """
        self._engine = engine

    @property
    def engine(self) -> AsyncEngine:
        """Get the underlying SQLAlchemy async engine."""
        return self._engine

    @classmethod
    async def from_instance(
        cls,
        project_id: str,
        region: str,
        instance: str,
        database: str,
        *,
        ip_type: IpAddressTypes = IpAddressTypes.PUBLIC,
        user: str | None = None,
        password: str | None = None,
        iam_account_email: str | None = None,
    ) -> PostgresEngine:
        """Create PostgresEngine using Cloud SQL Connector.

        This is the recommended method for connecting to Cloud SQL instances.
        Supports both password and IAM authentication.

        Args:
            project_id: GCP project ID.
            region: Cloud SQL instance region.
            instance: Cloud SQL instance name.
            database: Database name.
            ip_type: IP address type (PUBLIC or PRIVATE).
            user: Database user for password authentication.
            password: Database password for password authentication.
            iam_account_email: IAM service account email for IAM auth.

        Returns:
            Configured PostgresEngine instance.

        Raises:
            ValueError: If authentication configuration is invalid.
        """
        # Validate authentication configuration
        if (user is None) != (password is None):
            raise ValueError(
                "Only one of 'user' or 'password' was specified. Either both should be "
                'specified for password authentication, or neither for IAM authentication.'
            )

        # Determine authentication mode
        if user is not None and password is not None:
            # Password authentication
            enable_iam_auth = False
            db_user = user
            db_password = password
        else:
            # IAM authentication
            enable_iam_auth = True
            db_password = None
            if iam_account_email is not None:
                db_user = iam_account_email
            else:
                db_user = await _get_iam_principal_email()

        # Create connector if not exists
        if cls._connector is None:
            cls._connector = Connector()

        instance_connection_name = f'{project_id}:{region}:{instance}'

        async def getconn() -> asyncpg.Connection[Any]:
            """Get connection from Cloud SQL Connector."""
            assert cls._connector is not None
            conn = await cls._connector.connect_async(
                instance_connection_name,
                'asyncpg',
                user=db_user,
                password=db_password,
                db=database,
                ip_type=ip_type.to_ip_types(),
                enable_iam_auth=enable_iam_auth,
            )
            return conn

        engine = create_async_engine(
            'postgresql+asyncpg://',
            async_creator=getconn,
            echo=False,
        )

        return cls(engine)

    @classmethod
    async def from_engine(cls, engine: AsyncEngine) -> PostgresEngine:
        """Create PostgresEngine from existing SQLAlchemy async engine.

        Args:
            engine: Existing SQLAlchemy async engine.

        Returns:
            PostgresEngine wrapping the provided engine.
        """
        return cls(engine)

    @classmethod
    async def from_connection_string(
        cls,
        connection_string: str,
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> PostgresEngine:
        """Create PostgresEngine from connection string.

        Args:
            connection_string: PostgreSQL connection string.
                Should start with 'postgresql+asyncpg://'.
            pool_size: Connection pool size.
            max_overflow: Maximum overflow connections.

        Returns:
            Configured PostgresEngine instance.

        Raises:
            ValueError: If connection string has wrong format.
        """
        if not connection_string.startswith('postgresql+asyncpg://'):
            raise ValueError("Connection string must start with 'postgresql+asyncpg://'")

        engine = create_async_engine(
            connection_string,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False,
        )

        return cls(engine)

    # Alias for JS API parity (JS calls this fromEngineArgs)
    @classmethod
    async def from_engine_args(
        cls,
        url: str,
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> PostgresEngine:
        """Create PostgresEngine from connection string.

        This is an alias for `from_connection_string()` to match the JS API.

        Args:
            url: PostgreSQL connection string.
                Should start with 'postgresql+asyncpg://'.
            pool_size: Connection pool size.
            max_overflow: Maximum overflow connections.

        Returns:
            Configured PostgresEngine instance.

        Raises:
            ValueError: If connection string has wrong format.
        """
        return await cls.from_connection_string(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

    async def init_vectorstore_table(
        self,
        table_name: str,
        vector_size: int,
        *,
        schema_name: str = 'public',
        content_column: str = 'content',
        embedding_column: str = 'embedding',
        metadata_columns: list[Column] | None = None,
        metadata_json_column: str = 'json_metadata',
        id_column: str | Column = 'id',
        overwrite_existing: bool = False,
        store_metadata: bool = True,
    ) -> None:
        """Create a vector store table.

        Creates a PostgreSQL table with pgvector extension support
        for storing document embeddings.

        Args:
            table_name: Name of the table to create.
            vector_size: Dimension of the embedding vectors.
            schema_name: PostgreSQL schema name.
            content_column: Column name for document content.
            embedding_column: Column name for vector embeddings.
            metadata_columns: List of custom metadata columns.
            metadata_json_column: Column name for JSON metadata.
            id_column: Column name or Column object for IDs.
            overwrite_existing: Drop existing table if exists.
            store_metadata: Whether to create JSON metadata column.
        """
        async with self._engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))

            # Drop table if overwriting
            if overwrite_existing:
                await conn.execute(text(f'DROP TABLE IF EXISTS "{schema_name}"."{table_name}"'))

            # Determine ID column configuration
            if isinstance(id_column, Column):
                id_col_name = id_column.name
                id_col_type = id_column.data_type
            else:
                id_col_name = id_column
                id_col_type = 'UUID'

            # Build CREATE TABLE query
            query = f'''CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name}"(
                {id_col_name} {id_col_type} PRIMARY KEY,
                {content_column} TEXT NOT NULL,
                {embedding_column} vector({vector_size}) NOT NULL'''

            # Add custom metadata columns
            if metadata_columns:
                for col in metadata_columns:
                    nullable = '' if col.nullable else 'NOT NULL'
                    query += f',\n    {col.name} {col.data_type} {nullable}'

            # Add JSON metadata column
            if store_metadata:
                query += f',\n    {metadata_json_column} JSON'

            query += '\n);'

            await conn.execute(text(query))

    async def close(self) -> None:
        """Close the database connection and cleanup resources."""
        await self._engine.dispose()
        if PostgresEngine._connector is not None:
            await PostgresEngine._connector.close_async()
            PostgresEngine._connector = None

    # Alias for JS API parity
    async def close_connection(self) -> None:
        """Close the database connection and cleanup resources.

        This is an alias for `close()` to match the JS API.
        """
        await self.close()

    async def test_connection(self) -> bool:
        """Test the database connection.

        Returns:
            True if connection is successful.
        """
        async with self._engine.connect() as conn:
            result = await conn.execute(text('SELECT NOW()'))
            result.fetchone()
            return True

    async def apply_vector_index(
        self,
        table_name: str,
        index: BaseIndex,
        *,
        schema_name: str = 'public',
        embedding_column: str = 'embedding',
        concurrently: bool = False,
    ) -> None:
        """Create a vector index on the table.

        Args:
            table_name: Name of the table.
            index: Index configuration (HNSWIndex, IVFFlatIndex, etc.).
            schema_name: PostgreSQL schema name.
            embedding_column: Column containing embeddings.
            concurrently: Build index concurrently (allows concurrent writes).
        """
        if isinstance(index, ExactNearestNeighbor):
            # Drop any existing index for exact search
            await self.drop_vector_index(table_name=table_name, schema_name=schema_name)
            return

        index_name = index.name or f'{table_name}{DEFAULT_INDEX_NAME_SUFFIX}'
        filter_clause = f'WHERE ({index.partial_indexes})' if index.partial_indexes else ''
        index_options = f'WITH {index.index_options()}'
        index_function = index.distance_strategy.index_function

        concurrently_clause = 'CONCURRENTLY' if concurrently else ''

        query = f'''
            CREATE INDEX {concurrently_clause} {index_name}
            ON "{schema_name}"."{table_name}"
            USING {index.index_type} ({embedding_column} {index_function})
            {index_options} {filter_clause};
        '''

        async with self._engine.begin() as conn:
            await conn.execute(text(query))

    async def is_valid_index(
        self,
        table_name: str,
        *,
        index_name: str | None = None,
        schema_name: str = 'public',
    ) -> bool:
        """Check if a vector index exists on the table.

        Args:
            table_name: Name of the table.
            index_name: Optional specific index name to check.
            schema_name: PostgreSQL schema name.

        Returns:
            True if the index exists.
        """
        idx_name = index_name or f'{table_name}{DEFAULT_INDEX_NAME_SUFFIX}'

        query = text("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE tablename = :table_name
            AND schemaname = :schema_name
            AND indexname = :index_name
        """)

        async with self._engine.connect() as conn:
            result = await conn.execute(
                query,
                {'table_name': table_name, 'schema_name': schema_name, 'index_name': idx_name},
            )
            rows = result.fetchall()
            return len(rows) == 1

    async def drop_vector_index(
        self,
        table_name: str | None = None,
        index_name: str | None = None,
        schema_name: str = 'public',
    ) -> None:
        """Drop a vector index.

        Args:
            table_name: Table name (used to derive default index name).
            index_name: Specific index name to drop.
            schema_name: PostgreSQL schema name.

        Raises:
            ValueError: If neither table_name nor index_name is provided.
        """
        if index_name:
            idx_name = index_name
        elif table_name:
            idx_name = f'{table_name}{DEFAULT_INDEX_NAME_SUFFIX}'
        else:
            raise ValueError('Either table_name or index_name must be provided')

        async with self._engine.begin() as conn:
            await conn.execute(text(f'DROP INDEX IF EXISTS "{schema_name}"."{idx_name}"'))

    async def reindex(
        self,
        table_name: str | None = None,
        index_name: str | None = None,
    ) -> None:
        """Rebuild a vector index.

        Args:
            table_name: Table name (used to derive default index name).
            index_name: Specific index name to rebuild.

        Raises:
            ValueError: If neither table_name nor index_name is provided.
        """
        if index_name:
            idx_name = index_name
        elif table_name:
            idx_name = f'{table_name}{DEFAULT_INDEX_NAME_SUFFIX}'
        else:
            raise ValueError('Either table_name or index_name must be provided')

        async with self._engine.begin() as conn:
            await conn.execute(text(f'REINDEX INDEX {idx_name}'))
