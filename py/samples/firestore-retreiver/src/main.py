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


import firebase_admin
import asyncio
from genkit.ai.veneer import Genkit
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from genkit.plugins.firebase.firebase_api import FirebaseAPI
from genkit.plugins.firebase.constant import FirestoreRetrieverConfig, DistanceMeasure
from genkit.core.typing import EmbedResponse
from genkit.blocks.document import Document
from typing import NewType
import os


credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
cred = credentials.Certificate(credentials_path)
firebase_admin.initialize_app(cred)

firestore_client = firestore.client()

ai = Genkit(
    plugins=[
        FirebaseAPI(
            params=[
                FirestoreRetrieverConfig(
                    name='filmsretriever',
                    collection='films',
                    vector_field='embedding',
                    distance_measure=DistanceMeasure.COSINE,
                    firestore_client=firestore_client
                )
            ]
        )
    ]
)

Embedding = NewType('Embedding', list[float])

class MockEmbedder:
    def __init__(self, embedding_dimension: int = 3):
        self.embedding_dimension = embedding_dimension

    async def embed(self, documents: list[Document]) -> EmbedResponse:
        embeddings_list: list[Embedding] = []
        for doc in documents:
            if not doc.content:
                embedding: Embedding = Embedding([0.0] * self.embedding_dimension)
            else:
                text = doc.content[0].text
                embedding_values = [(len(text)) * (j + 0.1) for j in range(self.embedding_dimension)]
                embedding: Embedding = Embedding(embedding_values)
            embeddings_list.append(embedding)
        return EmbedResponse(embeddings=embeddings_list)

collection_name = 'films'

films = [
    "The Godfather is a 1972 crime film directed by Francis Ford Coppola.",
    "The Dark Knight is a 2008 superhero film directed by Christopher Nolan.",
    "Pulp Fiction is a 1994 crime film directed by Quentin Tarantino.",
    "Schindler's List is a 1993 historical drama directed by Steven Spielberg.",
    "Inception is a 2010 sci-fi film directed by Christopher Nolan.",
    "The Matrix is a 1999 sci-fi film directed by the Wachowskis.",
    "Fight Club is a 1999 film directed by David Fincher.",
    "Forrest Gump is a 1994 drama directed by Robert Zemeckis.",
    "Star Wars is a 1977 sci-fi film directed by George Lucas.",
    "The Shawshank Redemption is a 1994 drama directed by Frank Darabont.",
]

@ai.flow
async def embed_documents():
    """Indexes the film documents in Firestore."""
    mock_embedder = MockEmbedder(embedding_dimension=3)
    genkit_documents = [Document(content=[Part(text=film)]) for film in films]
    embed_response = await mock_embedder.embed(genkit_documents)
    embeddings = [emb.embedding for emb in embed_response.embeddings]

    for i, film_text in enumerate(films):
        doc_id = f"doc-{i+1}"
        embedding = embeddings[i]

        doc_ref = firestore_client.collection(collection_name).document(doc_id)
        try:
            result = doc_ref.set({
                "text": film_text,
                "embedding": embedding,
                "metadata": f"metadata for doc {i+1}",
            })
            print(f"Indexed document {i+1} with text: {film_text} (WriteResult: {result})")
        except Exception as e:
            print(f"Failed to index document {i+1}: {e}")
            return

    print("10 film documents indexed successfully")

def main() -> None:
    """Main entry point for the flow sample.

    This function demonstrates how to create and use AI flows in the
    Genkit framework.
    """

    asyncio.run(embed_documents())


if __name__ == '__main__':
    main()
