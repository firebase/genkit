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

from genkit.ai import Genkit
from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore
from genkit.plugins.google_genai import VertexAI
from genkit.types import Document

ai = Genkit(
    plugins=[
        VertexAI(),
        DevLocalVectorStore(
            name='films',
            embedder='vertexai/text-embedding-004',
        ),
    ],
    model='vertexai/gemini-2.0.',
)

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
    genkit_documents = [Document.from_text(text=film) for film in films]
    await DevLocalVectorStore.index('films', genkit_documents)

    print('10 film documents indexed successfully')


@ai.flow()
async def retreive_documents():
    return await ai.retrieve(
        query=Document.from_text('sci-fi film'),
        retriever='films',
    )


ai.run_main()
