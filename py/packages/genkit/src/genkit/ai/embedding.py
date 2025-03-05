# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

type Embedding = list[float]


# TODO(ssbushi): Replace with generated type
class EmbeddingModel(BaseModel):
    """Represents an embedding with metadata."""

    embedding: Embedding
    metadata: dict[str, Any] | None = None


class EmbedRequest(BaseModel):
    """Request for embedding documents.

    Attributes:
        documents: The list of documents to embed.
    """

    documents: list[str]


class EmbedResponse(BaseModel):
    """Response for embedding documents.

    Attributes:
        embeddings: The list of embeddings for the documents.
    """

    embeddings: list[Embedding]


type EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
