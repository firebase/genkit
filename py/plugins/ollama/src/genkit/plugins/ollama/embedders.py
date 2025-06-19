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

from collections.abc import Callable

from pydantic import BaseModel

from genkit.blocks.embedding import EmbedRequest, EmbedResponse
from genkit.types import Embedding


class EmbeddingDefinition(BaseModel):
    """Defines an embedding model for Ollama.

    This class specifies the characteristics of an embedding model that
    can be used with the Ollama plugin. While Ollama models have fixed
    output dimensions, this definition can specify the expected
    dimensionality for informational purposes or for future truncation
    support.
    """

    name: str
    dimensions: int | None = None


class OllamaEmbedder:
    """Handles embedding requests using an Ollama embedding model.

    This class provides the necessary logic to interact with a specific
    Ollama embedding model, processing input text into vector embeddings.
    """

    def __init__(
        self,
        client: Callable,
        embedding_definition: EmbeddingDefinition,
    ) -> None:
        """Initializes the OllamaEmbedder.

        Sets up the client for communicating with the Ollama server and stores
        the definition of the embedding model.

        Args:
            client: A callable that returns an asynchronous Ollama client instance.
            embedding_definition: The definition describing the specific Ollama
                embedding model to be used.
        """
        self.client = client()
        self.embedding_definition = embedding_definition

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Generates embeddings for the provided input text.

        Converts the input documents from the Genkit EmbedRequest into a raw
        list of strings, sends them to the Ollama server for embedding, and then
        formats the response into a Genkit EmbedResponse.

        Args:
            request: The embedding request containing the input documents.

        Returns:
            An EmbedResponse containing the generated vector embeddings.
        """
        input_raw = []
        for doc in request.input:
            input_raw.extend([content.root.text for content in doc.content])
        response = await self.client.embed(
            model=self.embedding_definition.name,
            input=input_raw,
        )
        return EmbedResponse(embeddings=[Embedding(embedding=embedding) for embedding in response.embeddings])
