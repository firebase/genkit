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
from genkit.plugins.dev_local_vector_store.constant import Params
from genkit.plugins.dev_local_vector_store.plugin_api import DevLocalVectorStore
from genkit.plugins.google_genai import GoogleGenai
from genkit.plugins.vertex_ai import EmbeddingModels

ai = Genkit(
    plugins=[
        GoogleGenai(
            vertexai=True,
            location='us-central1',
        ),
        DevLocalVectorStore(
            params=[
                Params(
                    index_name='menu-items',
                    embedder=EmbeddingModels.TEXT_EMBEDDING_004_ENG,
                    embedder_options={'taskType': 'RETRIEVAL_DOCUMENT'},
                )
            ]
        ),
    ]
)
