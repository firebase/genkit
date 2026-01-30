# Copyright 2026 Google LLC
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

"""ChromaDB vector store plugin for Genkit.

This plugin provides retriever and indexer implementations backed by ChromaDB,
an open-source embedding database for AI applications.

Architecture
============

┌─────────────────────────────────────────────────────────────────────────────┐
│                         Chroma Plugin Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐        │
│  │   Genkit     │     │   Chroma     │     │   ChromaDB           │        │
│  │   Instance   │ ──► │   Plugin     │ ──► │   (Local/Remote)     │        │
│  └──────────────┘     └──────────────┘     └──────────────────────┘        │
│                              │                                              │
│                              ├─► Retriever (similarity search)              │
│                              └─► Indexer (document storage)                 │
│                                                                              │
│  Data Flow:                                                                  │
│  ┌────────┐    ┌──────────┐    ┌────────────┐    ┌──────────────┐          │
│  │Document│ ─► │ Embedder │ ─► │ Embedding  │ ─► │ ChromaDB     │          │
│  └────────┘    └──────────┘    └────────────┘    │ Collection   │          │
│                                                   └──────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.ai import Genkit
    from genkit.plugins.google_genai import GoogleAI
    from genkit.plugins.chroma import chroma, chroma_retriever_ref

    ai = Genkit(
        plugins=[
            GoogleAI(),
            chroma(
                collections=[
                    {
                        'collection_name': 'my_docs',
                        'embedder': 'googleai/text-embedding-004',
                    }
                ]
            ),
        ]
    )

    # Retrieve similar documents
    results = await ai.retrieve(
        retriever=chroma_retriever_ref(collection_name='my_docs'),
        query='What is machine learning?',
        options={'k': 5},
    )
    ```

Cross-Language Parity:
    - JavaScript: js/plugins/chroma/src/index.ts

See Also:
    - ChromaDB: https://www.trychroma.com/
    - Genkit RAG: https://genkit.dev/docs/rag
"""

from genkit.plugins.chroma.plugin import (
    Chroma,
    ChromaCollectionConfig,
    ChromaIndexerOptions,
    ChromaPluginConfig,
    ChromaRetrieverOptions,
    chroma,
    chroma_indexer_ref,
    chroma_retriever_ref,
    create_chroma_collection,
    delete_chroma_collection,
)

__all__ = [
    'Chroma',
    'ChromaCollectionConfig',
    'ChromaIndexerOptions',
    'ChromaPluginConfig',
    'ChromaRetrieverOptions',
    'chroma',
    'chroma_indexer_ref',
    'chroma_retriever_ref',
    'create_chroma_collection',
    'delete_chroma_collection',
]
