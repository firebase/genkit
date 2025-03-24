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

import ollama as ollama_api
from genkit.blocks.embedding import EmbedRequest, EmbedResponse
from genkit.plugins.ollama.models import EmbeddingModelDefinition


class OllamaEmbedder:
    def __init__(
        self,
        client: ollama_api.AsyncClient,
        embedding_definition: EmbeddingModelDefinition,
    ):
        self.client = client
        self.embedding_definition = embedding_definition

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        response = await self.client.embed(
            model=self.embedding_definition.name,
            input=request.input,
        )
        return EmbedResponse(embeddings=response.embeddings)
