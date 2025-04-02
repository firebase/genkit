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


import asyncio
import hashlib

from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from genkit.ai.veneer import Genkit
from genkit.blocks.document import Document
from genkit.core.typing import (
    DocumentData,
    Embedding,
    EmbedRequest,
    EmbedResponse,
    TextPart,
)
from genkit.plugins.firebase.constant import FirestoreRetrieverConfig
from genkit.plugins.firebase.firebase_api import (
    FirebaseAPI,
    firestore_action_name,
)

# set GOOGLE_APPLICATION_CREDENTIALS on env
firestore_client = firestore.Client()

ai = Genkit(
    plugins=[
        FirebaseAPI(
            params=[
                FirestoreRetrieverConfig(
                    name='filmsretriever',
                    collection='films',
                    vector_field='embedding',
                    content_field='text',
                    embedder='mockembedder',
                    distance_measure=DistanceMeasure.EUCLIDEAN,
                    firestore_client=firestore_client,
                )
            ]
        )
    ]
)


class MockEmbedder:
    """A mock embedder which generates embeddings based on first three words for tests.

    Attributes:
        embedding_dimension: The dimensionality of the generated embeddings(defaults=3).
    """

    name = 'mockembedder'

    def __init__(self, embedding_dimension: int = 3) -> None:
        self.embedding_dimension = embedding_dimension

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        embeddings_list: list[Embedding] = []
        for doc in request.input:
            text = doc.content[0].root.text
            words = text.split()
            first_three_words = ' '.join(words[:3]) if len(words) >= 3 else text
            identifier = first_three_words.encode('utf-8')
            hashed_identifier = hashlib.md5(identifier).hexdigest()
            embedding_values = [
                (int(hashed_identifier[i * 8 : (i + 1) * 8], 16) % 100) / 100.0 for i in range(self.embedding_dimension)
            ]
            embedding: Embedding = Embedding(embedding=embedding_values)
            embeddings_list.append(embedding)
        return EmbedResponse(embeddings=embeddings_list)


embedder = MockEmbedder(
    embedding_dimension=3,
)
ai.define_embedder(
    name=embedder.name,
    fn=embedder.embed,
)

collection_name = 'films'

films = [
    'The Godfather is a 1972 crime film directed by Francis Ford Coppola.',
    'The Dark Knight is a 2008 superhero film directed by Christopher Nolan.',
    'Pulp Fiction is a 1994 crime film directed by Quentin Tarantino.',
    "Schindler's List is a 1993 historical drama directed by Steven Spielberg.",
    'Inception is a 2010 sci-fi film directed by Christopher Nolan.',
    'The Matrix is a 1999 sci-fi film directed by the Wachowskis.',
    'Fight Club is a 1999 film directed by David Fincher.',
    'Forrest Gump is a 1994 drama directed by Robert Zemeckis.',
    'Star Wars is a 1977 sci-fi film directed by George Lucas.',
    'The Shawshank Redemption is a 1994 drama directed by Frank Darabont.',
]


@ai.flow()
async def index_documents() -> None:
    """Indexes the film documents in Firestore."""
    mock_embedder = MockEmbedder(embedding_dimension=3)
    genkit_documents = [Document(content=[TextPart(text=film)]) for film in films]
    embed_response = await mock_embedder.embed(EmbedRequest(input=genkit_documents))
    embeddings = [emb.embedding for emb in embed_response.embeddings]

    for i, film_text in enumerate(films):
        doc_id = f'doc-{i + 1}'
        embedding = embeddings[i]

        doc_ref = firestore_client.collection(collection_name).document(doc_id)
        try:
            result = doc_ref.set({
                'text': film_text,
                'embedding': embedding,
                'metadata': f'metadata for doc {i + 1}',
            })
            print(f'Indexed document {i + 1} with text: {film_text} (WriteResult: {result})')
        except Exception as e:
            print(f'Failed to index document {i + 1}: {e}')
            return

    print('10 film documents indexed successfully')


@ai.flow()
async def retreive_documents():
    return await ai.retrieve(
        query=DocumentData(content=[TextPart(text='sci-fi film')]),
        retriever=firestore_action_name('filmsretriever'),
    )


async def main() -> None:
    """Main entry point for the flow sample.

    This function demonstrates how to create and use AI flows in the
    Genkit framework.
    """

    print(await index_documents())
    print(await retreive_documents())


if __name__ == '__main__':
    asyncio.run(main())
