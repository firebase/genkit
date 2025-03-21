# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
from genkit.plugins.dev_local_vector_store.constant import Params
from genkit.plugins.dev_local_vector_store.plugin_api import DevLocalVectorStore
from genkit.plugins.vertex_ai import EmbeddingModels, VertexAI
from genkit.veneer import Genkit

ai = Genkit(
    plugins=[
        VertexAI(
            location='us-central1',
        ),
        DevLocalVectorStore(
            params=Params(
                index_name='menu-items',
                embedder=EmbeddingModels.TEXT_EMBEDDING_004_ENG,
                embedder_options={'taskType': 'RETRIEVAL_DOCUMENT'},
            )
        ),
    ]
)
