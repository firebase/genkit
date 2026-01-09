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
from genkit.plugins.google_genai import GeminiEmbeddingModels, GoogleAI, googleai_name

ai = Genkit(
    plugins=[
        GoogleAI(),
        DevLocalVectorStore(
            name='menu-items',
            embedder=googleai_name(GeminiEmbeddingModels.TEXT_EMBEDDING_004),
            embedder_options={'taskType': 'RETRIEVAL_DOCUMENT'},
        ),
    ]
)
