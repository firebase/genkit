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

import json
from abc import ABC, abstractmethod
from typing import Any

import structlog
from google.cloud import aiplatform_v1, bigquery, firestore
from google.cloud.aiplatform_v1 import FindNeighborsRequest, IndexDatapoint, Neighbor
from pydantic import ValidationError

from genkit.blocks.document import Document
from genkit.core.typing import Embedding
from genkit.types import ActionRunContext, RetrieverRequest, RetrieverResponse

logger = structlog.get_logger(__name__)


class VertexAIVectorStoreRetriever(ABC):
    def __init__(
        self,
        ai,
        name: str,
        match_service_client: aiplatform_v1.MatchServiceAsyncClient,
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
    ):
        self.ai = ai
        self.name = name
        self._match_service_client = match_service_client
        self.embedder = embedder
        self.embedder_options = embedder_options or {}

    async def retrieve(self, request: RetrieverRequest, _: ActionRunContext) -> RetrieverResponse:
        document = Document.from_document_data(document_data=request.query)
        embeddings = await self.ai.embed(
            embedder=self.embedder,
            documents=[document],
            options=self.embedder_options,
        )
        if self.embedder_options:
            top_k = self.embedder_options.get('limit') or 3
        else:
            top_k = 3
        docs = await self._get_closest_documents(
            request=request,
            top_k=top_k,
            query_embeddings=embeddings.embeddings[0],
        )

        return RetrieverResponse(documents=[d.document for d in docs])

    async def _get_closest_documents(
        self, request: RetrieverRequest, top_k: int, query_embeddings: Embedding
    ) -> list[Document]:
        metadata = request.query.metadata
        if not metadata or 'index_endpoint_path' not in metadata:
            raise AttributeError('Request provides no data about index endpoint path')

        index_endpoint_path = metadata['index_endpoint_path']
        deployed_index_id = metadata['deployed_index_id']

        nn_request = FindNeighborsRequest(
            index_endpoint=index_endpoint_path,
            deployed_index_id=deployed_index_id,
            queries=[
                FindNeighborsRequest.Query(
                    datapoint=IndexDatapoint(feature_vector=query_embeddings.embedding),
                    neighbor_count=top_k,
                )
            ],
        )

        response = await self._match_service_client.find_neighbors(request=nn_request)

        return await self._retrieve_neighbours_data_from_db(neighbours=response.nearest_neighbors[0].neighbors)

    @abstractmethod
    async def _retrieve_neighbours_data_from_db(self, neighbours: list[Neighbor]) -> list[Document]:
        pass


class BigQueryRetriever(VertexAIVectorStoreRetriever):
    def __init__(self, bq_client: bigquery.Client, dataset_id: str, table_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bq_client = bq_client
        self.dataset_id = dataset_id
        self.table_id = table_id

    async def _retrieve_neighbours_data_from_db(self, neighbours: list[Neighbor]) -> list[Document]:
        ids = [n.datapoint.datapoint_id for n in neighbours if n.datapoint and n.datapoint.datapoint_id]

        if not ids:
            return []

        query = f"""
                SELECT * FROM `{self.dataset_id}.{self.table_id}`
                WHERE id IN UNNEST(@ids)
            """

        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter('ids', 'STRING', ids)])

        try:
            query_job = self.bq_client.query(query, job_config=job_config)
            rows = query_job.result()
        except Exception as e:
            await logger.aerror('Failed to execute BigQuery query: %s', e)
            return []

        documents: list[Document] = []

        for row in rows:
            try:
                doc_data = {
                    'content': json.loads(row['content']),
                }
                if row.get('metadata'):
                    doc_data['metadata'] = json.loads(row['metadata'])

                documents.append(Document(**doc_data))
            except (ValidationError, json.JSONDecodeError, Exception) as error:
                doc_id = row.get('id', '<unknown>')
                await logger.awarning(f'Failed to parse document data for document with ID {doc_id}: {error}')

        return documents


class FirestoreRetriever(VertexAIVectorStoreRetriever):
    def __init__(self, firestore_client: firestore.AsyncClient, collection_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = firestore_client
        self.collection_name = collection_name

    async def _retrieve_neighbours_data_from_db(self, neighbours: list[Neighbor]) -> list[Document]:
        documents: list[Document] = []

        for neighbor in neighbours:
            doc_ref = self.db.collection(self.collection_name).document(document_id=neighbor.datapoint.datapoint_id)
            doc_snapshot = await doc_ref.get()

            if doc_snapshot.exists:
                doc_data = doc_snapshot.to_dict() or {}

                try:
                    documents.append(Document(**doc_data))
                except ValidationError as e:
                    await logger.awarning(
                        f'Failed to parse document data for ID {neighbor.datapoint.datapoint_id}: {e}'
                    )

        return documents
