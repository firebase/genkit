# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import enum

from google import genai

from genkit.core.typing import Embedding, EmbedRequest, EmbedResponse
from genkit.plugins.google_genai.models.utils import PartConverter


class VertexEmbeddingModels(enum.StrEnum):
    """Embedding models supported by Google-Genai vertex."""

    GECKO_003_ENG = 'textembedding-gecko@003'
    TEXT_EMBEDDING_004_ENG = 'text-embedding-004'
    TEXT_EMBEDDING_005_ENG = 'text-embedding-005'
    GECKO_MULTILINGUAL = 'textembedding-gecko-multilingual@001'
    TEXT_EMBEDDING_002_MULTILINGUAL = 'text-multilingual-embedding-002'


class GeminiEmbeddingModels(enum.StrEnum):
    """Embedding models supported by Google-Genai gemini."""

    GEMINI_EMBEDDING_EXP_03_07 = 'gemini-embedding-exp-03-07'
    TEXT_EMBEDDING_004 = 'text-embedding-004'
    EMBEDDING_001 = 'embedding-001'


class EmbeddingTaskType(enum.StrEnum):
    RETRIEVAL_QUERY = 'RETRIEVAL_QUERY'
    RETRIEVAL_DOCUMENT = 'RETRIEVAL_DOCUMENT'
    SEMANTIC_SIMILARITY = 'SEMANTIC_SIMILARITY'
    CLASSIFICATION = 'CLASSIFICATION'
    CLUSTERING = 'CLUSTERING'
    QUESTION_ANSWERING = 'QUESTION_ANSWERING'
    FACT_VERIFICATION = 'FACT_VERIFICATION'


class Embedder:
    def __init__(
        self,
        version: VertexEmbeddingModels | GeminiEmbeddingModels | str,
        client: genai.Client,
    ):
        self._client = client
        self._version = version

    async def generate(self, request: EmbedRequest) -> EmbedResponse:
        contents = self._build_contents(request)
        config = self._genkit_to_googleai_cfg(request)
        response = await self._client.aio.models.embed_content(
            model=self._version, contents=contents, config=config
        )

        embeddings = [
            Embedding(embedding=em.values) for em in response.embeddings
        ]
        return EmbedResponse(embeddings=embeddings)

    def _build_contents(
        self, request: EmbedRequest
    ) -> list[genai.types.Content]:
        """Build google-genai request contents from Genkit request

        Args:
            request: Genkit request

        Returns:
            list of google-genai contents
        """

        reqest_contents: list[genai.types.Content] = []
        for doc in request.input:
            content_parts: list[genai.types.Part] = []
            for p in doc.content:
                content_parts.append(PartConverter.to_gemini(p))
            reqest_contents.append(genai.types.Content(parts=content_parts))

        return reqest_contents

    def _genkit_to_googleai_cfg(
        self, request: EmbedRequest
    ) -> genai.types.EmbedContentConfig | None:
        """Translate EmbedRequest options to Google Ai GenerateContentConfig

        Args:
            request: Genkit embed request

        Returns:
            Google Ai embed config or None
        """

        cfg = None
        if request.options:
            cfg = genai.types.EmbedContentConfig(
                task_type=request.options.get('task_type'),
                title=request.options.get('title'),
                output_dimensionality=request.options.get(
                    'output_dimensionality'
                ),
            )

        return cfg
