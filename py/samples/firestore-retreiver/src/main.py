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


"""Firestore retriever sample - Vector search with Firestore.

This sample demonstrates how to use Firestore as a vector store for
retrieval-augmented generation (RAG) with Genkit.

Key Features
============
| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Firestore Vector Store Definition       | `define_firestore_vector_store`     |
| Embed Many                              | `ai.embed_many()`                   |
| Document Retrieval                      | `ai.retrieve()`                     |
| Firestore Integration                   | `firestore.Client()`                |

See README.md for testing instructions.
"""

import os

from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from genkit.ai import Genkit
from genkit.plugins.firebase import add_firebase_telemetry, define_firestore_vector_store
from genkit.plugins.google_genai import VertexAI
from genkit.types import Document, RetrieverResponse

if 'GCLOUD_PROJECT' not in os.environ:
    os.environ['GCLOUD_PROJECT'] = input('Please enter your GCLOUD_PROJECT: ')

# Important: use the same embedding model for indexing and retrieval.
EMBEDDING_MODEL = 'vertexai/text-embedding-004'

# Add Firebase telemetry (metrics, logs, traces)
add_firebase_telemetry()

firestore_client = firestore.Client()

# Create Genkit instance
ai = Genkit(plugins=[VertexAI()])

# Define Firestore vector store - returns the retriever name
RETRIEVER_NAME = define_firestore_vector_store(
    ai,
    name='my_firestore_retriever',
    embedder=EMBEDDING_MODEL,
    collection='films',
    vector_field='embedding',
    content_field='text',
    firestore_client=firestore_client,
    distance_measure=DistanceMeasure.EUCLIDEAN,
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
    embeddings = await ai.embed_many(embedder=EMBEDDING_MODEL, content=films)
    for i, film_text in enumerate(films):
        doc_id = f'doc-{i + 1}'
        embedding = embeddings[i].embedding

        doc_ref = firestore_client.collection(collection_name).document(doc_id)
        try:
            result = doc_ref.set({
                'text': film_text,
                'embedding': Vector(embedding),
                'metadata': f'metadata for doc {i + 1}',
            })
            print(f'Indexed document {i + 1} with text: {film_text} (WriteResult: {result})')
        except Exception as e:
            print(f'Failed to index document {i + 1}: {e}')
            return

    print('10 film documents indexed successfully')


@ai.flow()
async def retreive_documents() -> RetrieverResponse:
    """Retrieves the film documents from Firestore."""
    return await ai.retrieve(
        query=Document.from_text('sci-fi film'),
        retriever=RETRIEVER_NAME,
        options={'limit': 10},
    )


async def main() -> None:
    """Main entry point for the flow sample.

    This function demonstrates how to create and use AI flows in the
    Genkit framework.
    """
    await index_documents()
    print(await retreive_documents())


if __name__ == '__main__':
    ai.run_main(main())
