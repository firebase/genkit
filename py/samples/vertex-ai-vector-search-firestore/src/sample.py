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

import os
import time

import structlog
from google.cloud import aiplatform, firestore
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.plugins.vertex_ai import (
    EmbeddingModels,
    VertexAI,
    VertexAIVectorSearch,
    vertexai_name,
)
from genkit.plugins.vertex_ai.models.retriever import FirestoreRetriever

LOCATION = os.getenv('LOCATION')
PROJECT_ID = os.getenv('PROJECT_ID')
EMBEDDING_MODEL = EmbeddingModels.TEXT_EMBEDDING_004_ENG

FIRESTORE_COLLECTION = os.getenv('FIRESTORE_COLLECTION')

VECTOR_SEARCH_DEPLOYED_INDEX_ID = os.getenv('VECTOR_SEARCH_DEPLOYED_INDEX_ID')
VECTOR_SEARCH_INDEX_ENDPOINT_PATH = os.getenv('VECVECTOR_SEARCH_INDEX_ENDPOINT_PATHTOR_SEARCH_INDEX_ENDPOINT_ID')
VECTOR_SEARCH_API_ENDPOINT = os.getenv('VECTOR_SEARCH_API_ENDPOINT')

firestore_client = firestore.Client(project=PROJECT_ID)
aiplatform.init(project=PROJECT_ID, location=LOCATION)

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[
        VertexAI(),
        VertexAIVectorSearch(
            retriever=FirestoreRetriever,
            retriever_extra_args={
                'firestore_client': firestore_client,
                'collection_name': FIRESTORE_COLLECTION,
            },
            embedder=vertexai_name(EMBEDDING_MODEL),
            embedder_options={
                'task': 'RETRIEVAL_DOCUMENT',
                'output_dimensionality': 128,
            },
        ),
    ]
)


class QueryFlowInputSchema(BaseModel):
    """Input schema."""

    query: str
    k: int


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

    options = {
        'limit': 10,
    }

    result: list[Document] = await ai.retrieve(
        retriever=vertexai_name('vertexAIVectorSearch'),
        query=query_document,
        options=options,
    )

    end_time = time.time()

    duration = int(end_time - start_time)

    result_data = []
    for doc in result.documents:
        result_data.append({
            'id': doc.metadata.get('id'),
            'text': doc.content[0].root.text,
            'distance': doc.metadata.get('distance'),
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
