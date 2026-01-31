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


"""Development local vector store plugin for Genkit.

This plugin provides a simple, file-based vector store for local development
and testing. It's not intended for production use but is ideal for prototyping
RAG applications without setting up external infrastructure.

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                  Dev Local Vector Store Plugin                          │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  └── define_dev_local_vector_store() - Create local vector store        │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  plugin_api.py - Plugin API                                             │
    │  ├── define_dev_local_vector_store() - Main factory function            │
    │  └── Returns indexer and retriever pair                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  local_vector_store_api.py - Vector Store Implementation                │
    │  ├── In-memory vector storage                                           │
    │  └── Cosine similarity search                                           │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  indexer.py - Document Indexing                                         │
    │  └── Add documents to the local store                                   │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  retriever.py - Document Retrieval                                      │
    │  └── Retrieve similar documents by query                                │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        Data Flow                                        │
    │                                                                         │
    │  Documents ──► Embedder ──► Indexer ──► Local Store (file/memory)       │
    │                                                                         │
    │  Query ──► Embedder ──► Retriever ──► Similarity Search ──► Results     │
    └─────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit import Genkit
    from genkit.plugins.dev_local_vectorstore import define_dev_local_vector_store

    ai = Genkit(...)

    # Create a local vector store
    store = define_dev_local_vector_store(
        ai,
        name='my_store',
        embedder='googleai/gemini-embedding-001',
    )

    # Index documents
    await ai.index(indexer=store.indexer, documents=[...])

    # Retrieve similar documents
    results = await ai.retrieve(retriever=store.retriever, query='...')
    ```

Caveats:
    - NOT for production use (no persistence guarantees)
    - Data is stored in memory or local files
    - No concurrent access support
    - Use Firebase, Vertex AI, or other production stores for real applications

See Also:
    - Genkit documentation: https://genkit.dev/
"""

from .plugin_api import define_dev_local_vector_store

__all__ = [
    define_dev_local_vector_store.__name__,
]
