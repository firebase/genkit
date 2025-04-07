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

from collections.abc import Callable
from typing import Any

from google.cloud.firestore_v1 import DocumentSnapshot
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from genkit.ai import Genkit
from genkit.types import ActionRunContext, Document, GenkitError, RetrieverRequest, RetrieverResponse

from .constant import MetadataTransformFn


class FirestoreRetriever:
    """Retrieves documents from Google Cloud Firestore using vector similarity search.

    Attributes:
        ai: An instance of the Genkit AI registry.
        params: A FirestoreRetrieverConfig object containing the configuration
            for the retriever
        firestore_client: The initialized Firestore client from the configuration.
    """

    def __init__(
        self,
        ai: Genkit,
        name: str,
        firestore_client: Any,
        collection: str,
        vector_field: str,
        content_field: str | Callable[[DocumentSnapshot], list[dict[str, str]]],
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
        distance_measure: DistanceMeasure = DistanceMeasure.COSINE,
        metadata_fields: list[str] | MetadataTransformFn | None = None,
    ):
        """Initialize the FirestoreRetriever.

        Args:
            ai: An instance of the Genkit AI registry.
            params: A FirestoreRetrieverConfig object containing the configuration
                for the retriever
        """
        self.ai = ai
        self.name = name
        self.firestore_client = firestore_client
        self.collection = collection
        self.vector_field = vector_field
        self.content_field = content_field
        self.embedder = embedder
        self.embedder_options = embedder_options
        self.distance_measure = distance_measure
        self.metadata_fields = metadata_fields
        self._validate_config()

    def _validate_config(self):
        """Validate the FirestoreRetriever configuration.

        Raises:
            ValueError: If the configuration is invalid.
        """
        if not self.collection:
            raise ValueError('Firestore Retriever config must include firestore collection name.')
        if not self.vector_field:
            raise ValueError('Firestore Retriever config must include vector field name.')
        if not self.embedder:
            raise ValueError('Firestore Retriever config must include embedder name.')
        if not self.firestore_client:
            raise ValueError('Firestore Retriever config must include firestore client.')

    def _to_content(self, doc_snapshot: DocumentSnapshot) -> list[dict[str, str]]:
        """Convert a Firestore document snapshot to a list of content dictionaries.

        Args:
            doc_snapshot: A Firestore DocumentSnapshot object.

        Returns:
            A list of dictionaries containing the content of the document.
        """
        content_field = self.content_field
        if callable(content_field):
            return content_field(doc_snapshot)
        else:
            content = doc_snapshot.get(content_field)
            return [{'text': content}] if content else []

    def _to_metadata(self, doc_snapshot: DocumentSnapshot) -> Document:
        """Convert a Firestore document snapshot to a list of metadata dictionaries.

        Args:
            doc_snapshot: A Firestore DocumentSnapshot object.

        Returns:
            A list of dictionaries containing the metadata of the document.
        """
        metadata: dict[str, Any] = {}
        metadata_fields = self.metadata_fields
        if metadata_fields:
            if callable(metadata_fields):
                metadata = metadata_fields(doc_snapshot)
            else:
                for field in metadata_fields:
                    if field in doc_snapshot:
                        metadata[field] = doc_snapshot.get(field)
        else:
            metadata = doc_snapshot.to_dict()
            vector_field = self.vector_field
            content_field = self.content_field
            if vector_field in metadata:
                del metadata[vector_field]
            if isinstance(content_field, str) and content_field in metadata:
                del metadata[content_field]
        return metadata

    def _to_document(self, doc_snapshot: DocumentSnapshot) -> Document:
        """Convert a Firestore document snapshot to a Genkit Document object.

        Args:
            doc_snapshot: A Firestore DocumentSnapshot object.

        Returns:
            A Genkit Document object.
        """
        return Document(content=self._to_content(doc_snapshot), metadata=self._to_metadata(doc_snapshot))

    async def retrieve(self, request: RetrieverRequest, _: ActionRunContext) -> RetrieverResponse:
        """Retrieves documents from Firestore using native vector similarity search.

        Args:
            request: A RetrieverRequest Object

        Returns:
            A RetrieverResponse Object containing retrieved documents
        """
        query = request.query
        query_embedding_result = await self.ai.embed(
            embedder=self.embedder,
            documents=[query],
            options=self.embedder_options,
        )

        if not query_embedding_result.embeddings or len(query_embedding_result.embeddings) == 0:
            raise GenkitError(message='Embedder returned no embeddings')

        query_embedding = query_embedding_result.embeddings[0].embedding
        query_vector = Vector(query_embedding)
        collection = self.firestore_client.collection(self.collection)

        limit = 10
        if isinstance(request.options, dict) and (limit_val := request.options.get('limit')) is not None:
            limit = int(limit_val)

        vector_query = collection.find_nearest(
            vector_field=self.vector_field,
            query_vector=query_vector,
            distance_measure=self.distance_measure,
            limit=limit,
        )
        query_snapshot = vector_query.get()
        documents = [self._to_document(doc) for doc in query_snapshot]
        return RetrieverResponse(documents=documents)
