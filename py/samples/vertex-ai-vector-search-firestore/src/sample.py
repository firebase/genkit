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

from google.cloud import aiplatform, firestore
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.plugins.vertex_ai import (
    VertexAI,
    VertexAIVectorSearch,
    vertexai_name,
)
from genkit.plugins.vertex_ai.models.retriever import FirestoreRetriever
from genkit.plugins.vertex_ai import EmbeddingModels

LOCATION = os.getenv('LOCATION')
PROJECT_ID = os.getenv('PROJECT_ID')
FIRESTORE_COLLECTION = os.getenv('FIRESTORE_COLLECTION')
VECTOR_SEARCH_DEPLOYED_INDEX_ID = os.getenv('VECTOR_SEARCH_DEPLOYED_INDEX_ID')
VECTOR_SEARCH_INDEX_ENDPOINT_ID = os.getenv('VECTOR_SEARCH_INDEX_ENDPOINT_ID')
VECTOR_SEARCH_INDEX_ID = os.getenv('VECTOR_SEARCH_INDEX_ID')
VECTOR_SEARCH_PUBLIC_DOMAIN_NAME = os.getenv('VECTOR_SEARCH_PUBLIC_DOMAIN_NAME')

firestore_client = firestore.Client(project=PROJECT_ID)
aiplatform.init(project=PROJECT_ID, location=LOCATION)


ai = Genkit(
    plugins=[
        VertexAI(),
        VertexAIVectorSearch(
            retriever=FirestoreRetriever,
            retriever_extra_args={
                'firestore_client': firestore_client,
                'collection_name': FIRESTORE_COLLECTION,
            },
            embedder=EmbeddingModels.TEXT_EMBEDDING_004_ENG,
            embedder_options={'taskType': 'RETRIEVAL_DOCUMENT'},
        ),
    ]
)


class QueryFlowInputSchema(BaseModel):
    query: str
    k: int


class QueryFlowOutputSchema(BaseModel):
    result: list[dict]
    length: int
    time: int


@ai.flow(name='queryFlow')
async def query_flow(_input: QueryFlowInputSchema) -> QueryFlowOutputSchema:
    start_time = time.time()
    query_document = Document.from_text(text=_input.query)

    result: list[Document] = await ai.retrieve(
        retriever=vertexai_name(VECTOR_SEARCH_INDEX_ID),
        query=query_document,
    )

    end_time = time.time()

    duration = int(end_time - start_time)

    result_data = []
    for doc in result:
        result_data.append({
            'text': doc.content[0].root.text,
            'distance': doc.metadata.get('distance'),
        })

    result_data = sorted(result_data, key=lambda x: x['distance'])

    return QueryFlowOutputSchema(
        result=result_data,
        length=len(result_data),
        time=duration,
    )
