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

"""Vertex AI Vector Search with BigQuery sample.

Key features demonstrated in this sample:

| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| BigQuery Vector Search Definition       | `define_vertex_vector_search_big_query`|
| BigQuery Client Integration             | `bigquery.Client()`                 |
| Document Retrieval with Filters         | `ai.retrieve(..., options={'limit': ...})`|
| Performance Metrics                     | Duration tracking                   |
"""

import os
import time

import structlog
from google.cloud import aiplatform, bigquery
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.plugins.google_genai import VertexAI
from genkit.plugins.vertex_ai import define_vertex_vector_search_big_query

LOCATION = os.getenv('LOCATION')
PROJECT_ID = os.getenv('PROJECT_ID')

BIGQUERY_DATASET_NAME = os.getenv('BIGQUERY_DATASET_NAME')
BIGQUERY_TABLE_NAME = os.getenv('BIGQUERY_TABLE_NAME')

VECTOR_SEARCH_DEPLOYED_INDEX_ID = os.getenv('VECTOR_SEARCH_DEPLOYED_INDEX_ID')
VECTOR_SEARCH_INDEX_ENDPOINT_PATH = os.getenv('VECTOR_SEARCH_INDEX_ENDPOINT_PATH')
VECTOR_SEARCH_API_ENDPOINT = os.getenv('VECTOR_SEARCH_API_ENDPOINT')

bq_client = bigquery.Client(project=PROJECT_ID)
aiplatform.init(project=PROJECT_ID, location=LOCATION)

logger = structlog.get_logger(__name__)

ai = Genkit(plugins=[VertexAI()])

# Define Vertex AI Vector Search with BigQuery
define_vertex_vector_search_big_query(
    ai,
    name='my-vector-search',
    embedder='vertexai/text-embedding-004',
    embedder_options={
        'task': 'RETRIEVAL_DOCUMENT',
        'output_dimensionality': 128,
    },
    bq_client=bq_client,
    dataset_id=BIGQUERY_DATASET_NAME or 'default_dataset',
    table_id=BIGQUERY_TABLE_NAME or 'default_table',
)


class QueryFlowInputSchema(BaseModel):
    """Input schema."""

    query: str = Field(default='document 1', description='Search query text')
    k: int = Field(default=5, description='Number of results to return')


class QueryFlowOutputSchema(BaseModel):
    """Output schema."""

    result: list[dict]
    length: int
    time: int


@ai.flow(name='queryFlow')
async def query_flow(_input: QueryFlowInputSchema) -> QueryFlowOutputSchema:
    """Executes a vector search with VertexAI Vector Search."""
    start_time = time.time()

    query_document = Document.from_text(text=_input.query)
    query_document.metadata = {
        'api_endpoint': VECTOR_SEARCH_API_ENDPOINT,
        'index_endpoint_path': VECTOR_SEARCH_INDEX_ENDPOINT_PATH,
        'deployed_index_id': VECTOR_SEARCH_DEPLOYED_INDEX_ID,
    }

    response = await ai.retrieve(
        retriever='my-vector-search',
        query=query_document,
        options={'limit': 10},
    )

    end_time = time.time()

    duration = int(end_time - start_time)

    result_data = []
    for doc in response.documents:
        metadata = doc.metadata or {}
        result_data.append({
            'id': metadata.get('id'),
            'text': doc.content[0].root.text if doc.content and doc.content[0].root.text else '',
            'distance': metadata.get('distance'),
        })

    result_data = sorted(result_data, key=lambda x: x['distance'])

    return QueryFlowOutputSchema(
        result=result_data,
        length=len(result_data),
        time=duration,
    )


async def main() -> None:
    """Main function."""
    query_input = QueryFlowInputSchema(
        query='Content for doc',
        k=3,
    )

    await logger.ainfo(await query_flow(query_input))


if __name__ == '__main__':
    ai.run_main(main())
