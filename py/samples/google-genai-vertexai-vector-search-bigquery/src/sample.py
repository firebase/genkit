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

from google.cloud import aiplatform, bigquery
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.plugins.google_genai import VertexAI
from genkit.plugins.google_genai.google import VertexAIVectorSearch, vertexai_name
from genkit.plugins.google_genai.models.retriever import BigQueryRetriever
from genkit.plugins.vertex_ai import EmbeddingModels

LOCATION = os.getenv('LOCATION')
PROJECT_ID = os.getenv('PROJECT_ID')
BIGQUERY_DATASET = os.getenv('BIGQUERY_DATASET')
BIGQUERY_TABLE = os.getenv('BIGQUERY_TABLE')
VECTOR_SEARCH_DEPLOYED_INDEX_ID = os.getenv('VECTOR_SEARCH_DEPLOYED_INDEX_ID')
VECTOR_SEARCH_INDEX_ENDPOINT_ID = os.getenv('VECTOR_SEARCH_INDEX_ENDPOINT_ID')
VECTOR_SEARCH_INDEX_ID = os.getenv('VECTOR_SEARCH_INDEX_ID')
VECTOR_SEARCH_PUBLIC_DOMAIN_NAME = os.getenv('VECTOR_SEARCH_PUBLIC_DOMAIN_NAME')


bq_client = bigquery.Client(project=PROJECT_ID)
aiplatform.init(project=PROJECT_ID, location=LOCATION)


ai = Genkit(
    plugins=[
        VertexAI(),
        VertexAIVectorSearch(
            retriever=BigQueryRetriever,
            retriever_extra_args={
                'bq_client': bq_client,
                'dataset_id': BIGQUERY_DATASET,
                'table_id': BIGQUERY_TABLE,
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
