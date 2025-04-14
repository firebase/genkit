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

"""Vertex AI embedding plugin."""

import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from typing import Any

from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from genkit.blocks.document import Document
from genkit.types import Embedding, EmbedRequest, EmbedResponse


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


class EmbeddingsTaskType(StrEnum):
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
    QUESTION_ANSWERING = 'QUESTION_ANSWERING'
    FACT_VERIFICATION = 'FACT_VERIFICATION'
    CODE_RETRIEVAL_QUERY = 'CODE_RETRIEVAL_QUERY'


class Embedder:
    """Embedder for Vertex AI."""

    TASK_KEY = 'task'
    DEFAULT_TASK = EmbeddingsTaskType.RETRIEVAL_QUERY

    # By default, the model generates embeddings with 768 dimensions.
    # Models such as `text-embedding-004`, `text-embedding-005`,
    # and `text-multilingual-embedding-002`allow the output dimensionality
    # to be adjusted between 1 and 768.

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
        # TODO: pass additional parameters
        return TextEmbeddingModel.from_pretrained(self._version)

    def generate(self, request: EmbedRequest) -> EmbedResponse:
        """Handle an embedding request.

        Args:
            request: The embedding request to handle.

        Returns:
            The embedding response.
        """
        options = request.options or {'task': self.DEFAULT_TASK}
        task = options.get(self.TASK_KEY)
        if task not in EmbeddingsTaskType:
            raise ValueError(f'Unsupported task {task} for VertexAI.')

        del options[self.TASK_KEY]

        inputs = [TextEmbeddingInput(Document.from_document_data(doc).text(), task) for doc in request.input]
        vertexai_embeddings = self.embedding_model.get_embeddings(inputs, **options)
        embeddings = [Embedding(embedding=embedding.values) for embedding in vertexai_embeddings]

        return EmbedResponse(embeddings=embeddings)

    @property
    def model_metadata(self) -> dict[str, dict[str, Any]]:
        """Get the model metadata.

        Returns:
            The model metadata.
        """
        return {}
