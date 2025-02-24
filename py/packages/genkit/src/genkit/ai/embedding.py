# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable

from pydantic import BaseModel


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

    embeddings: list[list[float]]


type EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
