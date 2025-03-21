# Copyright 2025 Google LLC
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
