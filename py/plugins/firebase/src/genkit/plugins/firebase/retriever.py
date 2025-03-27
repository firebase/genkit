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

from typing import Dict, Any
from genkit.ai.veneer import Genkit
from genkit.core.typing import RetrieverRequest, TextPart
from genkit.core.action import ActionRunContext
from google.cloud.firestore.vector import Vector
from genkit.plugins.firebase.constant import FirestoreRetrieverConfig, DistanceMeasure
from firebase_admin.firestore import DocumentSnapshot
from genkit.blocks.document import Document


class FirestoreRetriever():
    def __init__(self,ai: Genkit, params: FirestoreRetrieverConfig):
        self.ai=ai
        self.params=params
        self.firestore_client = params.firestore_client

    def _to_content(self, doc_snapshot: DocumentSnapshot) -> list[Dict[str, str]]:
        content_field = self.params.get("content_field")
        if callable(content_field):
            return content_field(doc_snapshot)
        else:
            content = doc_snapshot.get(content_field)
            return [{"text": content}] if content is not None else []

    def _to_document(self, doc_snapshot: DocumentSnapshot) -> Document:
        content = self._to_content(doc_snapshot)
        metadata: Dict[str, Any] = {"id": doc_snapshot.id}
        data = doc_snapshot.to_dict()
        vector_field = self.params.get("vector_field")
        content_field_name = self.params.get("content_field")
        metadata.update({k: v for k, v in data.items() if k != vector_field and k != content_field_name})
        return Document(content=content, metadata=metadata)

    async def retrieve(self, request: RetrieverRequest, _: ActionRunContext):
        """
        Retrieves documents from Firestore using native vector similarity search.

        TO DO: Verifying that following works
        vector_query = query.find_nearest(
            vector_field=vector_field,
            query_vector=Vector(query_embedding),
            distance_measure=distance_measure_enum,
            limit=limit,
        )
        """

        query_embedding_result = await self.embedding_model.embed([Document(content=[TextPart(text=request.query)])])
        if not query_embedding_result.embeddings:
            return {"documents": []}
        query_embedding = query_embedding_result.embeddings[0].embedding

        collection_ref = self.firestore_client.collection(self.params.get("collection"))
        vector_field = self.params.get("vector_field")
        distance_measure_str = self.params.get("distance_measure", "COSINE").upper()
        limit = request.limit if request.limit is not None else (request.top_k if request.top_k is not None else 10)

        try:
            distance_measure_enum = DistanceMeasure(distance_measure_str)
        except ValueError:
            print(f"Invalid distance measure: {distance_measure_str}. Using COSINE.")
            distance_measure_enum = DistanceMeasure.COSINE

        query = collection_ref
        vector_query = query.find_nearest(
            vector_field=vector_field,
            query_vector=Vector(query_embedding),
            distance_measure=distance_measure_enum,
            limit=limit,
        )

        query_snapshot = await vector_query.get()
        documents = [self._to_document(doc) for doc in query_snapshot]

        return {"documents": documents}

