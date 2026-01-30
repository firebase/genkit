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

"""Pinecone vector store plugin for Genkit.

This plugin provides retriever and indexer implementations backed by Pinecone,
a managed vector database for AI applications.

Architecture
============

┌─────────────────────────────────────────────────────────────────────────────┐
│                        Pinecone Plugin Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐        │
│  │   Genkit     │     │  Pinecone    │     │   Pinecone Cloud     │        │
│  │   Instance   │ ──► │   Plugin     │ ──► │   (Managed Service)  │        │
│  └──────────────┘     └──────────────┘     └──────────────────────┘        │
│                              │                                              │
│                              ├─► Retriever (similarity search)              │
│                              └─► Indexer (vector upsert)                    │
│                                                                              │
│  Data Flow:                                                                  │
│  ┌────────┐    ┌──────────┐    ┌────────────┐    ┌──────────────┐          │
│  │Document│ ─► │ Embedder │ ─► │ Embedding  │ ─► │ Pinecone     │          │
│  └────────┘    └──────────┘    └────────────┘    │ Index        │          │
│                                                   └──────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.ai import Genkit
    from genkit.plugins.google_genai import GoogleAI
    from genkit.plugins.pinecone import pinecone, pinecone_retriever_ref

    ai = Genkit(
        plugins=[
            GoogleAI(),
            pinecone(
                indexes=[
                    {
                        'index_id': 'my_index',
                        'embedder': 'googleai/text-embedding-004',
                    }
                ]
            ),
        ]
    )

    # Retrieve similar documents
    results = await ai.retrieve(
        retriever=pinecone_retriever_ref(index_id='my_index'),
        query='What is machine learning?',
        options={'k': 5},
    )
    ```

Cross-Language Parity:
    - JavaScript: js/plugins/pinecone/src/index.ts

See Also:
    - Pinecone: https://www.pinecone.io/
    - Genkit RAG: https://genkit.dev/docs/rag
"""

from genkit.plugins.pinecone.plugin import (
    Pinecone,
    PineconeIndexConfig,
    PineconeIndexerOptions,
    PineconeRetrieverOptions,
    create_pinecone_index,
    delete_pinecone_index,
    describe_pinecone_index,
    pinecone,
    pinecone_indexer_ref,
    pinecone_retriever_ref,
)

__all__ = [
    'Pinecone',
    'PineconeIndexConfig',
    'PineconeIndexerOptions',
    'PineconeRetrieverOptions',
    'create_pinecone_index',
    'delete_pinecone_index',
    'describe_pinecone_index',
    'pinecone',
    'pinecone_indexer_ref',
    'pinecone_retriever_ref',
]
