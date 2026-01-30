# Cloud SQL PostgreSQL Plugin for Genkit

This plugin provides a vector store implementation for [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres) with [pgvector](https://github.com/pgvector/pgvector) support, enabling RAG (Retrieval-Augmented Generation) workflows in Genkit applications.

## Features

- **Cloud SQL Connector**: Secure connections to Cloud SQL instances using the Cloud SQL Python Connector
- **IAM Authentication**: Support for both IAM-based and password authentication
- **pgvector Support**: Vector similarity search using PostgreSQL's pgvector extension
- **Multiple Distance Strategies**: Cosine distance, Euclidean distance, and inner product
- **Vector Indexes**: Support for HNSW and IVFFlat indexes for efficient similarity search
- **Flexible Metadata**: Store metadata in dedicated columns or JSON format
- **Batch Processing**: Efficient batch indexing of documents

## Installation

```bash
pip install genkit-cloud-sql-pg-plugin
```

## Prerequisites

1. A Cloud SQL for PostgreSQL instance with the `pgvector` extension enabled
2. A Google Cloud project with the Cloud SQL API enabled
3. Proper IAM permissions or database credentials

### Enable pgvector Extension

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Usage

### Basic Setup

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.cloud_sql_pg import (
    CloudSqlPg,
    PostgresEngine,
    PostgresTableConfig,
)

# Create the engine using Cloud SQL Connector (recommended)
engine = await PostgresEngine.from_instance(
    project_id='your-project-id',
    region='us-central1',
    instance='your-instance',
    database='your-database',
    # For IAM authentication (recommended):
    # iam_account_email='your-service-account@your-project.iam.gserviceaccount.com'
    # For password authentication:
    user='your-user',
    password='your-password',
)

# Initialize the table (run once)
await engine.init_vectorstore_table(
    table_name='documents',
    vector_size=768,  # Match your embedder's dimension
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
```

### Indexing Documents

```python
from genkit.blocks.document import Document

# Index documents
await ai.index(
    indexer='postgres/documents',
    documents=[
        Document.from_text('The quick brown fox jumps over the lazy dog.'),
        Document.from_text('A journey of a thousand miles begins with a single step.'),
    ],
)
```

### Retrieving Documents

```python
# Retrieve similar documents
response = await ai.retrieve(
    retriever='postgres/documents',
    query=Document.from_text('What animal is jumping?'),
    options={'k': 5},
)

for doc in response.documents:
    print(doc.text())
```

### Using SQL Filters

```python
# Filter results using SQL WHERE clause
response = await ai.retrieve(
    retriever='postgres/documents',
    query=Document.from_text('search query'),
    options={
        'k': 10,
        'filter': "category = 'science'",  # SQL WHERE clause
    },
)
```

## Configuration Options

### PostgresEngine

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | str | Yes | GCP project ID |
| `region` | str | Yes | Cloud SQL instance region |
| `instance` | str | Yes | Cloud SQL instance name |
| `database` | str | Yes | Database name |
| `user` | str | No | Database user (for password auth) |
| `password` | str | No | Database password (for password auth) |
| `iam_account_email` | str | No | IAM service account email (for IAM auth) |
| `ip_type` | IpAddressTypes | No | IP address type (PUBLIC or PRIVATE) |

### PostgresTableConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `table_name` | str | Required | Table name |
| `engine` | PostgresEngine | Required | Database engine instance |
| `embedder` | str | Required | Embedder reference |
| `embedder_options` | dict | None | Embedder configuration |
| `schema_name` | str | 'public' | PostgreSQL schema name |
| `content_column` | str | 'content' | Column for document content |
| `embedding_column` | str | 'embedding' | Column for vector embeddings |
| `id_column` | str | 'id' | Column for document IDs |
| `metadata_columns` | list[str] | None | Specific metadata columns to use |
| `metadata_json_column` | str | 'metadata' | JSON column for metadata |
| `distance_strategy` | DistanceStrategy | COSINE_DISTANCE | Vector distance strategy |
| `index_query_options` | QueryOptions | None | Index-specific query options |

### Distance Strategies

- `DistanceStrategy.COSINE_DISTANCE` - Cosine distance (default)
- `DistanceStrategy.EUCLIDEAN` - L2 distance
- `DistanceStrategy.INNER_PRODUCT` - Inner product

### Vector Indexes

#### HNSW Index

```python
from genkit.plugins.cloud_sql_pg import HNSWIndex, HNSWQueryOptions

# Create HNSW index
await engine.apply_vector_index(
    table_name='documents',
    index=HNSWIndex(m=16, ef_construction=64),
)

# Use with query options
ai = Genkit(
    plugins=[
        CloudSqlPg(
            tables=[
                PostgresTableConfig(
                    table_name='documents',
                    engine=engine,
                    embedder='googleai/text-embedding-004',
                    index_query_options=HNSWQueryOptions(ef_search=40),
                )
            ]
        ),
    ]
)
```

#### IVFFlat Index

```python
from genkit.plugins.cloud_sql_pg import IVFFlatIndex, IVFFlatQueryOptions

# Create IVFFlat index
await engine.apply_vector_index(
    table_name='documents',
    index=IVFFlatIndex(lists=100),
)

# Use with query options
index_query_options=IVFFlatQueryOptions(probes=10)
```

## API Parity with JavaScript

This plugin maintains API and behavioral parity with the JavaScript `@genkit-ai/cloud-sql-pg` plugin.

| Feature | JS | Python |
|---------|-----|--------|
| Cloud SQL Connector | ✅ | ✅ |
| IAM Authentication | ✅ | ✅ |
| Password Authentication | ✅ | ✅ |
| Direct Connection | ✅ | ✅ |
| HNSW Index | ✅ | ✅ |
| IVFFlat Index | ✅ | ✅ |
| Distance Strategies | ✅ | ✅ |
| Metadata Columns | ✅ | ✅ |
| JSON Metadata | ✅ | ✅ |
| SQL Filtering | ✅ | ✅ |
| Batch Indexing | ✅ | ✅ |

## License

Apache-2.0
