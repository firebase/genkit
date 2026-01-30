# RAG with Cloud SQL PostgreSQL Sample

This sample demonstrates Retrieval-Augmented Generation (RAG) using Cloud SQL for PostgreSQL with pgvector support.

## Prerequisites

1. **Cloud SQL Instance**: A Cloud SQL for PostgreSQL instance with pgvector extension enabled
2. **Google Cloud Project**: A GCP project with Cloud SQL API enabled
3. **Authentication**: Either:
   * Service account with Cloud SQL Client role
   * Database user credentials

### Enable pgvector Extension

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Setup

1. Set environment variables:

```bash
# Required
export GOOGLE_GENAI_API_KEY="your-gemini-api-key"
export CLOUDSQL_PROJECT_ID="your-gcp-project"
export CLOUDSQL_REGION="us-central1"
export CLOUDSQL_INSTANCE="your-instance-name"
export CLOUDSQL_DATABASE="your-database"

# For password authentication (choose this OR IAM auth)
export CLOUDSQL_USER="your-db-user"
export CLOUDSQL_PASSWORD="your-db-password"

# For IAM authentication (alternative to password auth)
# export CLOUDSQL_IAM_EMAIL="your-service-account@your-project.iam.gserviceaccount.com"
```

2. Install dependencies:

```bash
cd py/samples/rag-cloud-sql-pg
uv sync
```

## Running the Sample

### Initialize the Database Table

First run will create the vector store table:

```bash
uv run genkit start -- python src/main.py --init
```

### Index Sample Documents

```bash
uv run genkit start -- python src/main.py --index
```

### Query the Vector Store

```bash
uv run genkit start -- python src/main.py --query "What are the benefits of exercise?"
```

### Run with DevUI

```bash
uv run genkit start
```

Then open http://localhost:4000 in your browser.

## Project Structure

```
rag-cloud-sql-pg/
├── pyproject.toml      # Dependencies
├── README.md           # This file
└── src/
    └── main.py         # Main application
```

## Code Overview

### Engine Setup

```python
from genkit.plugins.cloud_sql_pg import PostgresEngine

engine = await PostgresEngine.from_instance(
    project_id=os.environ['CLOUDSQL_PROJECT_ID'],
    region=os.environ['CLOUDSQL_REGION'],
    instance=os.environ['CLOUDSQL_INSTANCE'],
    database=os.environ['CLOUDSQL_DATABASE'],
    user=os.environ.get('CLOUDSQL_USER'),
    password=os.environ.get('CLOUDSQL_PASSWORD'),
)
```

### Table Initialization

```python
await engine.init_vectorstore_table(
    table_name='documents',
    vector_size=768,  # text-embedding-004 dimension
)
```

### Plugin Setup

```python
from genkit.plugins.cloud_sql_pg import CloudSqlPg, PostgresTableConfig

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

### Indexing

```python
await ai.index(
    indexer='postgres/documents',
    documents=[Document.from_text('Your text here')],
)
```

### Retrieval

```python
response = await ai.retrieve(
    retriever='postgres/documents',
    query=Document.from_text('Your query here'),
    options={'k': 5},
)
```

## Features Demonstrated

* Cloud SQL Connector for secure connections
* pgvector for vector similarity search
* Embedding generation with Google AI
* RAG flow with context injection
* SQL filtering support

## License

Apache-2.0
