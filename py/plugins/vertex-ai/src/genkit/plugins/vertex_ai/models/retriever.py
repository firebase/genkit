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
from collections.abc import Callable
from typing import Any

import structlog
from google.cloud import bigquery, firestore
from google.cloud.aiplatform_v1 import FindNeighborsRequest, FindNeighborsResponse, IndexDatapoint
from pydantic import BaseModel, Field, ValidationError

from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.core.typing import Embedding
from genkit.types import ActionRunContext, RetrieverRequest, RetrieverResponse

logger = structlog.get_logger(__name__)

DEFAULT_LIMIT_NEIGHBORS: int = 3


class DocRetriever(ABC):
    """Abstract base class for Vertex AI Vector Search document retrieval.

    This class outlines the core workflow for retrieving relevant documents.
    It is not intended to be instantiated directly. Subclasses must implement
    the abstract methods to provide concrete retrieval logic depending of the
    technology used.

    Attributes:
        ai: The Genkit instance.
        name: The name of this retriever instance.
        match_service_client:  The Vertex AI Matching Engine client.
        embedder: The name of the embedder to use for generating embeddings.
        embedder_options:  Options to pass to the embedder.
    """

    def __init__(
        self,
        ai: Genkit,
        name: str,
        match_service_client_generator: Callable,
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the DocRetriever.

        Args:
            ai: The Genkit application instance.
            name: The name of this retriever instance.
            match_service_client_generator: The Vertex AI Matching Engine client.
            embedder: The name of the embedder to use for generating embeddings.
                Already added plugin prefix.
            embedder_options: Optional dictionary of options to pass to the embedder.
        """
        self.ai = ai
        self.name = name
        self.embedder = embedder
        self.embedder_options = embedder_options or {}
        self._match_service_client_generator = match_service_client_generator

    async def retrieve(self, request: RetrieverRequest, _: ActionRunContext) -> RetrieverResponse:
        """Retrieves documents based on a given query.

        Args:
            request: The retrieval request containing the query.
            _: The ActionRunContext (unused in this method).

        Returns:
            A RetrieverResponse object containing the retrieved documents.
        """
        document = Document.from_document_data(document_data=request.query)

        embeddings = await self.ai.embed(
            embedder=self.embedder,
            documents=[document],
            options=self.embedder_options,
        )

        limit_neighbors = DEFAULT_LIMIT_NEIGHBORS
        if isinstance(request.options, dict) and request.options.get('limit') is not None:
            limit_neighbors = request.options.get('limit')

        docs = await self._get_closest_documents(
            request=request,
            top_k=limit_neighbors,
            query_embeddings=embeddings.embeddings[0],
        )

        return RetrieverResponse(documents=docs)

    async def _get_closest_documents(
        self, request: RetrieverRequest, top_k: int, query_embeddings: Embedding
    ) -> list[Document]:
        """Retrieves the closest documents from the vector search index based on query embeddings.

        Args:
            request: The retrieval request containing the query and metadata.
            top_k: The number of nearest neighbors to retrieve.
            query_embeddings: The embedding of the query.

        Returns:
            A list of Document objects representing the closest documents.

        Raises:
            AttributeError: If the request does not contain the necessary
            index endpoint path in its metadata.
        """
        metadata = request.query.metadata

        required_keys = ['index_endpoint_path', 'api_endpoint', 'deployed_index_id']

        if not metadata:
            raise AttributeError('Request metadata provides no data about index')

        for rkey in required_keys:
            if rkey not in metadata:
                raise AttributeError(f'Request metadata provides no data for {rkey}')

        api_endpoint = metadata['api_endpoint']
        index_endpoint_path = metadata['index_endpoint_path']
        deployed_index_id = metadata['deployed_index_id']

        client_options = {'api_endpoint': api_endpoint}

        vector_search_client = self._match_service_client_generator(
            client_options=client_options,
        )

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

        response = await vector_search_client.find_neighbors(request=nn_request)

        return await self._retrieve_neighbors_data_from_db(neighbors=response.nearest_neighbors[0].neighbors)

    @abstractmethod
    async def _retrieve_neighbors_data_from_db(self, neighbors: list[FindNeighborsResponse.Neighbor]) -> list[Document]:
        """Retrieves document data from the database based on neighbor information.

        This method must be implemented by subclasses to define how document
        data is fetched from the database using the provided neighbor information.

        Args:
            neighbors: A list of Neighbor objects representing the nearest neighbors
                found in the vector search index.

        Returns:
            A list of Document objects containing the data for the retrieved documents.
        """
        raise NotImplementedError


class BigQueryRetriever(DocRetriever):
    """Retrieves documents from a BigQuery table.

    This class extends DocRetriever to fetch document data from a specified BigQuery
    dataset and table. It constructs a query to retrieve documents based on the IDs
    obtained from nearest neighbor search results.

    Attributes:
        bq_client: The BigQuery client to use for querying.
        dataset_id: The ID of the BigQuery dataset.
        table_id: The ID of the BigQuery table.
    """

    def __init__(
        self,
        bq_client: bigquery.Client,
        dataset_id: str,
        table_id: str,
        *args,
        **kwargs,
    ) -> None:
        """Initializes the BigQueryRetriever.

        Args:
            bq_client: The BigQuery client to use for querying.
            dataset_id: The ID of the BigQuery dataset.
            table_id: The ID of the BigQuery table.
            *args: Additional positional arguments to pass to the parent class.
            **kwargs: Additional keyword arguments to pass to the parent class.
        """
        super().__init__(*args, **kwargs)
        self.bq_client = bq_client
        self.dataset_id = dataset_id
        self.table_id = table_id

    async def _retrieve_neighbors_data_from_db(self, neighbors: list[FindNeighborsResponse.Neighbor]) -> list[Document]:
        """Retrieves document data from the BigQuery table for the given neighbors.

        Constructs and executes a BigQuery query to fetch document data based on
        the IDs obtained. Handles potential errors during query execution and
        document parsing.

        Args:
            neighbors: A list of Neighbor objects representing the nearest neighbors.
                        Each neighbor should contain a datapoint with a datapoint_id.

        Returns:
            A list of Document objects containing the retrieved document data.
            Returns an empty list if no IDs are found in the neighbors or if the
            query fails.
        """
        ids = [n.datapoint.datapoint_id for n in neighbors if n.datapoint and n.datapoint.datapoint_id]

        distance_by_id = {
            n.datapoint.datapoint_id: n.distance for n in neighbors if n.datapoint and n.datapoint.datapoint_id
        }

        if not ids:
            return []

        query = f"""
            SELECT * FROM `{self.dataset_id}.{self.table_id}`
            WHERE id IN UNNEST(@ids)
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter('ids', 'STRING', ids)],
        )

        try:
            query_job = self.bq_client.query(query, job_config=job_config)
            rows = query_job.result()
        except Exception as e:
            await logger.aerror('Failed to execute BigQuery query: %s', e)
            return []

        documents: list[Document] = []

        for row in rows:
            try:
                id = row['id']

                content = row['content']
                content = json.dumps(content) if isinstance(content, dict) else str(content)

                metadata = row.get('metadata', {})
                metadata['id'] = id
                metadata['distance'] = distance_by_id[id]

                documents.append(Document.from_text(content, metadata))
            except (ValidationError, json.JSONDecodeError, Exception) as error:
                doc_id = row.get('id', '<unknown>')
                await logger.awarning('Failed to parse document data for document with ID %s: %s', doc_id, error)

        return documents


class FirestoreRetriever(DocRetriever):
    """Retrieves documents from a Firestore collection.

    This class extends DocRetriever to fetch document data from a specified Firestore
    collection. It retrieves documents based on IDs obtained from nearest neighbor
    search results.

    Attributes:
        db: The Firestore client.
        collection_name: The name of the Firestore collection.
    """

    def __init__(
        self,
        firestore_client: firestore.AsyncClient,
        collection_name: str,
        *args,
        **kwargs,
    ) -> None:
        """Initializes the FirestoreRetriever.

        Args:
            firestore_client: The Firestore client to use for querying.
            collection_name: The name of the Firestore collection.
            *args: Additional positional arguments to pass to the parent class.
            **kwargs: Additional keyword arguments to pass to the parent class.
        """
        super().__init__(*args, **kwargs)
        self.db = firestore_client
        self.collection_name = collection_name

    async def _retrieve_neighbors_data_from_db(self, neighbors: list[FindNeighborsResponse.Neighbor]) -> list[Document]:
        """Retrieves document data from the Firestore collection for the given neighbors.

        Fetches document data from Firestore based on the IDs of the nearest neighbors.
        Handles potential errors during document retrieval and data parsing.

        Args:
            neighbors: A list of Neighbor objects representing the nearest neighbors.
                        Each neighbor should contain a datapoint with a datapoint_id.

        Returns:
            A list of Document objects containing the retrieved document data.
            Returns an empty list if no documents are found for the given IDs.
        """
        documents: list[Document] = []

        for neighbor in neighbors:
            doc_ref = self.db.collection(self.collection_name).document(document_id=neighbor.datapoint.datapoint_id)
            doc_snapshot = doc_ref.get()

            if doc_snapshot.exists:
                doc_data = doc_snapshot.to_dict() or {}

                content = doc_data.get('content', '')
                content = json.dumps(content) if isinstance(content, dict) else str(content)

                metadata = doc_data.get('metadata', {})
                metadata['id'] = neighbor.datapoint.datapoint_id
                metadata['distance'] = neighbor.distance

                try:
                    documents.append(
                        Document.from_text(
                            content,
                            metadata,
                        )
                    )
                except ValidationError as e:
                    await logger.awarning(
                        'Failed to parse document data for ID %s: %s',
                        neighbor.datapoint.datapoint_id,
                        e,
                    )

        return documents


class RetrieverOptionsSchema(BaseModel):
    """Schema for retriver options.

    Attributes:
        limit: Number of documents to retrieve.
    """

    limit: int | None = Field(title='Number of documents to retrieve', default=None)
