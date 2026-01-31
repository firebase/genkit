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

"""Firebase plugin for Genkit.

This plugin provides Firebase integrations for Genkit, including Firestore
vector stores for RAG and Firebase telemetry export to Google Cloud.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Firebase            │ Google's app development platform. Like a         │
    │                     │ toolbox for building apps with database, auth.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Firestore           │ A NoSQL database that syncs in real-time.         │
    │                     │ Store data as flexible documents.                 │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Vector Store        │ A database that can find "similar" items.         │
    │                     │ Like Google but for YOUR documents.               │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ RAG                 │ Retrieval-Augmented Generation. AI looks up       │
    │                     │ your docs before answering. Fewer hallucinations! │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Embeddings          │ Convert text to numbers that capture meaning.     │
    │                     │ "Cat" and "kitten" become similar numbers.        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Indexer             │ Stores documents with their embeddings.           │
    │                     │ Like adding books to a library catalog.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Retriever           │ Finds documents matching a query.                 │
    │                     │ Like a librarian finding relevant books.          │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow (RAG with Firestore)::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                  HOW FIRESTORE VECTOR SEARCH WORKS                      │
    │                                                                         │
    │    STEP 1: INDEXING (Store your documents)                              │
    │    ────────────────────────────────────────                             │
    │    Your Documents                                                       │
    │    ["How to reset password", "Billing FAQ", ...]                        │
    │         │                                                               │
    │         │  (1) Convert text to embeddings                               │
    │         ▼                                                               │
    │    ┌─────────────────┐                                                  │
    │    │  Embedder       │   "Reset password" → [0.12, -0.34, ...]          │
    │    │  (Gemini, etc.) │                                                  │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (2) Store in Firestore with vectors                      │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Firestore      │   Document + embedding stored together           │
    │    │  (Vector Index) │                                                  │
    │    └─────────────────┘                                                  │
    │                                                                         │
    │    STEP 2: RETRIEVAL (Find relevant documents)                          │
    │    ─────────────────────────────────────────────                        │
    │    User Query: "How do I change my password?"                           │
    │         │                                                               │
    │         │  (3) Convert query to embedding                               │
    │         ▼                                                               │
    │    ┌─────────────────┐                                                  │
    │    │  Embedder       │   Query → [0.11, -0.33, ...] (similar!)          │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (4) Find nearest neighbors                               │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Firestore      │   "Reset password" doc is 95% match!             │
    │    │  Vector Search  │                                                  │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (5) Return matching documents                            │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Your App       │   AI uses these docs to answer accurately        │
    │    └─────────────────┘                                                  │
    └─────────────────────────────────────────────────────────────────────────┘

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        Firebase Plugin                                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  ├── define_firestore_vector_store() - Create Firestore vector store    │
    │  └── add_firebase_telemetry() - Enable Cloud observability              │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  firestore.py - Firestore Vector Store                                  │
    │  ├── define_firestore_vector_store() - Main factory function            │
    │  ├── Firestore indexer implementation                                   │
    │  └── Firestore retriever implementation                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  retriever.py - Retriever Implementation                                │
    │  └── FirestoreRetriever (vector similarity search)                      │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                     Firestore Vector Store Flow                         │
    │                                                                         │
    │  Documents ──► Embedder ──► Firestore (with vector index)               │
    │                                                                         │
    │  Query ──► Embedder ──► Firestore Vector Search ──► Results             │
    └─────────────────────────────────────────────────────────────────────────┘

Overview:
    The Firebase plugin enables:
    - Firestore as a vector store for document retrieval (RAG)
    - Telemetry export to Google Cloud Trace and Monitoring

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component                    │ Purpose                                  │
    ├──────────────────────────────┼──────────────────────────────────────────┤
    │ define_firestore_vector_store│ Create a Firestore-backed vector store   │
    │ add_firebase_telemetry()     │ Enable Cloud Trace/Monitoring export     │
    └──────────────────────────────┴──────────────────────────────────────────┘

Example:
    Using Firestore vector store:

    ```python
    from genkit import Genkit
    from genkit.plugins.firebase import define_firestore_vector_store

    ai = Genkit(...)

    # Define a Firestore vector store
    store = define_firestore_vector_store(
        ai,
        name='my_store',
        collection='documents',
        embedder='vertexai/text-embedding-005',
    )

    # Index documents
    await ai.index(indexer=store.indexer, documents=[...])

    # Retrieve documents
    docs = await ai.retrieve(retriever=store.retriever, query='...')
    ```

    Enabling telemetry:

    ```python
    from genkit.plugins.firebase import add_firebase_telemetry

    # Export traces to Cloud Trace (disabled in dev mode by default)
    add_firebase_telemetry()
    ```

Caveats:
    - Requires firebase-admin SDK and Google Cloud credentials
    - Telemetry is disabled by default in development mode (GENKIT_ENV=dev)

See Also:
    - Firestore: https://firebase.google.com/docs/firestore
    - Genkit documentation: https://genkit.dev/
"""

from genkit.plugins.google_cloud.telemetry.tracing import add_gcp_telemetry

from .firestore import define_firestore_vector_store


def package_name() -> str:
    """Get the package name for the Firebase plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.firebase'


def add_firebase_telemetry() -> None:
    """Add Firebase telemetry export to Google Cloud Observability.

    Exports traces to Cloud Trace and metrics to Cloud Monitoring.
    In development (GENKIT_ENV=dev), telemetry is disabled by default.
    """
    add_gcp_telemetry(force_export=False)


__all__ = [
    'package_name',
    'add_firebase_telemetry',
    'define_firestore_vector_store',
]
