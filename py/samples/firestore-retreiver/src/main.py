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


from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from genkit.ai import Genkit
from genkit.plugins.firebase.firestore import (
    FirestoreVectorStore,
    firestore_action_name,
)
from genkit.plugins.google_genai import VertexAI
from genkit.types import (
    Document,
    TextPart,
)

# Important: use the same embedding model for indexing and retrieval.
EMBEDDING_MODEL = 'vertexai/text-embedding-004'

firestore_client = firestore.Client()

ai = Genkit(
    plugins=[
        VertexAI(),
        FirestoreVectorStore(
            name='filmsretriever',
            collection='films',
            vector_field='embedding',
            content_field='text',
            embedder=EMBEDDING_MODEL,
            distance_measure=DistanceMeasure.EUCLIDEAN,
            firestore_client=firestore_client,
        ),
    ]
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
    genkit_documents = [Document(content=[TextPart(text=film)]) for film in films]
    embed_response = await ai.embed(embedder=EMBEDDING_MODEL, documents=genkit_documents)
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
    """Retrieves the film documents from Firestore."""
    return await ai.retrieve(
        query=Document.from_text('sci-fi film'),
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
    ai.run_main(main())
