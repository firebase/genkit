# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vertex AI embedding plugin."""

from enum import StrEnum
from typing import Any

from genkit.ai.embedding import EmbedRequest, EmbedResponse
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel


class EmbeddingModels(StrEnum):
    """Embedding models supported by Vertex AI.

    Attributes:
        GECKO_003_ENG: Gecko 003 English model.
        TEXT_EMBEDDING_004_ENG: Text embedding 004 English model.
        TEXT_EMBEDDING_005_ENG: Text embedding 005 English model.
        GECKO_MULTILINGUAL: Gecko multilingual model.
        TEXT_EMBEDDING_002_MULTILINGUAL: Text embedding 002 multilingual model.
    """

    GECKO_003_ENG = 'textembedding-gecko@003'
    TEXT_EMBEDDING_004_ENG = 'text-embedding-004'
    TEXT_EMBEDDING_005_ENG = 'text-embedding-005'
    GECKO_MULTILINGUAL = 'textembedding-gecko-multilingual@001'
    TEXT_EMBEDDING_002_MULTILINGUAL = 'text-multilingual-embedding-002'


class TaskType(StrEnum):
    """Task types supported by Vertex AI.

    Attributes:
        SEMANTIC_SIMILARITY: Semantic similarity task.
        CLASSIFICATION: Classification task.
        CLUSTERING: Clustering task.
        RETRIEVAL_DOCUMENT: Retrieval document task.
        RETRIEVAL_QUERY: Retrieval query task.
        QUESTION_ANSWERING: Question answering task.
        FACT_VERIFICATION: Fact verification task.
        CODE_RETRIEVAL_QUERY: Code retrieval query task.
    """

    SEMANTIC_SIMILARITY = 'SEMANTIC_SIMILARITY'
    CLASSIFICATION = 'CLASSIFICATION'
    CLUSTERING = 'CLUSTERING'
    RETRIEVAL_DOCUMENT = 'RETRIEVAL_DOCUMENT'
    RETRIEVAL_QUERY = 'RETRIEVAL_QUERY'


class Embedder:
    """Embedder for Vertex AI.

    Attributes:
        version: The version of the embedding model to use.
        task: The task type to use for the embedding.
        dimensionality: The dimensionality of the embedding.
    """

    TASK = TaskType.RETRIEVAL_QUERY

    # By default, the model generates embeddings with 768 dimensions.
    # Models such as `text-embedding-004`, `text-embedding-005`,
    # and `text-multilingual-embedding-002`allow the output dimensionality
    # to be adjusted between 1 and 768.
    DIMENSIONALITY = 768

    def __init__(self, version: EmbeddingModels):
        """Initialize the embedder.

        Args:
            version: The version of the embedding model to use.
        """
        self._version = version

    @property
    def embedding_model(self) -> TextEmbeddingModel:
        """Get the embedding model.

        Returns:
            The embedding model.
        """
        return TextEmbeddingModel.from_pretrained(self._version)

    def handle_request(self, request: EmbedRequest) -> EmbedResponse:
        """Handle an embedding request.

        Args:
            request: The embedding request to handle.

        Returns:
            The embedding response.
        """
        inputs = [
            TextEmbeddingInput(text, self.TASK) for text in request.documents
        ]
        vertexai_embeddings = self.embedding_model.get_embeddings(inputs)
        embeddings = [embedding.values for embedding in vertexai_embeddings]
        return EmbedResponse(embeddings=embeddings)

    @property
    def model_metadata(self) -> dict[str, dict[str, Any]]:
        """Get the model metadata.

        Returns:
            The model metadata.
        """
        return {}
