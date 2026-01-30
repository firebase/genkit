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

"""RAG sample using Cloud SQL PostgreSQL with pgvector.

This sample demonstrates:
- Setting up Cloud SQL PostgreSQL as a vector store
- Indexing documents with embeddings
- Retrieving relevant documents using similarity search
- Building a RAG flow with Genkit

Prerequisites:
- Cloud SQL for PostgreSQL instance with pgvector extension
- Environment variables for connection details
"""

import argparse
import asyncio
import os

from genkit import Genkit
from genkit.blocks.document import Document
from genkit.plugins.cloud_sql_pg import (
    CloudSqlPg,
    HNSWIndex,
    HNSWQueryOptions,
    PostgresEngine,
    PostgresTableConfig,
)
from genkit.plugins.google_genai import GoogleAI

# Sample documents for indexing
SAMPLE_DOCUMENTS = [
    """Regular exercise has numerous health benefits. It can help control weight,
    reduce risk of heart disease, and strengthen bones and muscles. Exercise also
    improves mental health by reducing anxiety, depression, and negative mood.""",
    """A balanced diet is essential for good health. It should include a variety
    of fruits, vegetables, whole grains, lean proteins, and healthy fats. Proper
    nutrition provides energy and supports all bodily functions.""",
    """Sleep is crucial for physical and mental health. Adults should aim for
    7-9 hours of sleep per night. Good sleep improves brain function, mood,
    and overall health while reducing disease risk.""",
    """Stress management is important for well-being. Techniques like meditation,
    deep breathing, and regular physical activity can help reduce stress levels.
    Chronic stress can lead to various health problems.""",
    """Staying hydrated is essential for body function. Water helps regulate
    temperature, transport nutrients, and remove waste. The recommended daily
    intake is about 8 glasses of water.""",
]

# Table and embedder configuration
TABLE_NAME = 'health_documents'
EMBEDDER = 'googleai/text-embedding-004'
EMBEDDING_DIMENSION = 768  # text-embedding-004 dimension


async def create_engine() -> PostgresEngine:
    """Create PostgresEngine from environment variables."""
    project_id = os.environ.get('CLOUDSQL_PROJECT_ID')
    region = os.environ.get('CLOUDSQL_REGION')
    instance = os.environ.get('CLOUDSQL_INSTANCE')
    database = os.environ.get('CLOUDSQL_DATABASE')
    user = os.environ.get('CLOUDSQL_USER')
    password = os.environ.get('CLOUDSQL_PASSWORD')
    iam_email = os.environ.get('CLOUDSQL_IAM_EMAIL')

    if not project_id or not region or not instance or not database:
        raise ValueError(
            'Missing required environment variables. Set: '
            'CLOUDSQL_PROJECT_ID, CLOUDSQL_REGION, CLOUDSQL_INSTANCE, CLOUDSQL_DATABASE'
        )

    # Use IAM auth if no user/password provided
    if user and password:
        return await PostgresEngine.from_instance(
            project_id=project_id,
            region=region,
            instance=instance,
            database=database,
            user=user,
            password=password,
        )
    else:
        return await PostgresEngine.from_instance(
            project_id=project_id,
            region=region,
            instance=instance,
            database=database,
            iam_account_email=iam_email,
        )


async def init_table(engine: PostgresEngine) -> None:
    """Initialize the vector store table."""
    print(f'Creating table: {TABLE_NAME}')
    await engine.init_vectorstore_table(
        table_name=TABLE_NAME,
        vector_size=EMBEDDING_DIMENSION,
        overwrite_existing=True,
    )
    print('Table created successfully!')

    # Optionally create an HNSW index for faster queries
    print('Creating HNSW index...')
    await engine.apply_vector_index(
        table_name=TABLE_NAME,
        index=HNSWIndex(m=16, ef_construction=64),
    )
    print('Index created successfully!')


async def index_documents(ai: Genkit) -> None:
    """Index sample documents."""
    print(f'Indexing {len(SAMPLE_DOCUMENTS)} documents...')

    documents = [Document.from_text(text) for text in SAMPLE_DOCUMENTS]

    await ai.index(
        indexer=f'postgres/{TABLE_NAME}',
        documents=documents,
    )

    print('Documents indexed successfully!')


async def query_documents(ai: Genkit, query: str) -> None:
    """Query the vector store and show results."""
    print(f'\nQuery: {query}')
    print('-' * 50)

    response = await ai.retrieve(
        retriever=f'postgres/{TABLE_NAME}',
        query=Document.from_text(query),
        options={'k': 3},
    )

    print(f'Found {len(response.documents)} relevant documents:\n')

    for i, doc_data in enumerate(response.documents, 1):
        doc = Document.from_document_data(doc_data)
        text = doc.text() or str(doc.content)
        distance = doc.metadata.get('_distance', 'N/A') if doc.metadata else 'N/A'
        print(f'{i}. (distance: {distance:.4f})')
        print(f'   {text[:200]}...\n')


async def run_rag_flow(ai: Genkit, question: str) -> None:
    """Run a RAG flow: retrieve context and generate answer."""
    print(f'\nQuestion: {question}')
    print('-' * 50)

    # Retrieve relevant documents
    response = await ai.retrieve(
        retriever=f'postgres/{TABLE_NAME}',
        query=Document.from_text(question),
        options={'k': 3},
    )

    # Build context from retrieved documents
    context_parts = []
    for doc_data in response.documents:
        doc = Document.from_document_data(doc_data)
        text = doc.text() or str(doc.content)
        context_parts.append(text)

    context = '\n\n'.join(context_parts)

    # Generate answer using the context
    prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {question}

Answer:"""

    result = await ai.generate(
        model='googleai/gemini-2.0-flash',
        prompt=prompt,
    )

    print(f'\nAnswer: {result.text}')


# Create engine and Genkit instance
# Note: In a real application, you'd use dependency injection or async context
_engine: PostgresEngine | None = None


async def get_engine() -> PostgresEngine:
    """Get or create the PostgresEngine instance."""
    global _engine
    if _engine is None:
        _engine = await create_engine()
    return _engine


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='RAG with Cloud SQL PostgreSQL')
    parser.add_argument('--init', action='store_true', help='Initialize the database table')
    parser.add_argument('--index', action='store_true', help='Index sample documents')
    parser.add_argument('--query', type=str, help='Query the vector store')
    parser.add_argument('--rag', type=str, help='Run RAG flow with a question')
    args = parser.parse_args()

    # Create engine
    engine = await get_engine()

    # Handle init command
    if args.init:
        await init_table(engine)
        return

    # Create Genkit instance with plugins
    ai = Genkit(
        plugins=[
            GoogleAI(),
            CloudSqlPg(
                tables=[
                    PostgresTableConfig(
                        table_name=TABLE_NAME,
                        engine=engine,
                        embedder=EMBEDDER,
                        index_query_options=HNSWQueryOptions(ef_search=40),
                    )
                ]
            ),
        ]
    )

    # Handle commands
    if args.index:
        await index_documents(ai)
    elif args.query:
        await query_documents(ai, args.query)
    elif args.rag:
        await run_rag_flow(ai, args.rag)
    else:
        # Default: run a demo query
        print('No command specified. Running demo...')
        print('\nUse --init to create the table')
        print('Use --index to index sample documents')
        print('Use --query "your query" to search')
        print('Use --rag "your question" to run RAG flow')


if __name__ == '__main__':
    asyncio.run(main())
