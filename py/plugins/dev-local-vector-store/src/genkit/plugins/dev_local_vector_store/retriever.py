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


from pydantic import BaseModel, Field

from genkit.ai import ActionRunContext, Document
from genkit.plugins.dev_local_vector_store.local_vector_store_api import (
    LocalVectorStoreAPI,
)
from genkit.types import Embedding, RetrieverRequest


class ScoredDocument(BaseModel):
    score: float
    document: Document


class RetrieverOptionsSchema(BaseModel):
    limit: int | None = Field(title='Number of documents to retrieve', default=None)


class DevLocalVectorStoreRetriever(LocalVectorStoreAPI):
    async def retrieve(self, request: RetrieverRequest, _: ActionRunContext):
        document = Document.from_document_data(document_data=request.query)
        embeddings = await self.ai.embed(
            embedder=self.params.embedder,
            documents=[document],
            options=self.params.embedder_options,
        )
        if self.params.embedder_options:
            k = self.params.embedder_options.get('limit') or 3
        else:
            k = 3
        return self._get_closest_documents(
            k=k,
            query_embeddings=embeddings.embeddings[0],
        )

    def _get_closest_documents(self, k: int, query_embeddings: Embedding) -> list[ScoredDocument]:
        db = self._load_filestore()
        scored_documents = []

        for val in db.values():
            this_embedding = val.embedding.embedding
            score = self.cosine_similarity(query_embeddings, this_embedding)
            scored_documents.append(
                ScoredDocument(
                    score=score,
                    document=Document.from_document_data(document_data=val.doc),
                )
            )

        scored_documents = sorted(scored_documents, key=lambda d: d.score, reverse=True)
        return scored_documents[:k]

    @classmethod
    def cosine_similarity(cls, a: list[int], b: list[int]) -> float:
        return cls.dot(a, b) / ((cls.dot(a, a) ** 0.5) * (cls.dot(b, b) ** 0.5))

    @staticmethod
    def dot(a: list[int], b: list[int]) -> float:
        return sum(a * b for a, b in zip(a, b, strict=False))
