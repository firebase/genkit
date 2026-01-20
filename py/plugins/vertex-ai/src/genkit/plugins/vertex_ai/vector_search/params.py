from dataclasses import dataclass
from typing import Any

from genkit.blocks.embedding import Embedder
from genkit.blocks.retriever import RetrieveParams


@dataclass(frozen=True)
class VertexAIVectorSearchOptions:
    """Options for Vertex AI vector search retrievers."""

    limit: int | None = None


def vertexai_retrieve_params(
    *,
    embedder: Embedder,
    embedder_options: dict[str, Any] | None = None,
    options: VertexAIVectorSearchOptions | None = None,
) -> RetrieveParams:
    """Build RetrieveParams with typed Vertex AI vector search options."""
    return RetrieveParams(
        embedder=embedder,
        embedder_options=embedder_options,
        options=options,
    )
