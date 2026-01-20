from dataclasses import dataclass
from typing import Any

from genkit.blocks.embedding import Embedder
from genkit.blocks.retriever import IndexParams, RetrieveParams


@dataclass(frozen=True)
class DevLocalVectorStoreOptions:
    """Options for the dev local vector store retriever."""

    limit: int | None = None


def dev_local_vectorstore_retrieve_params(
    *,
    embedder: Embedder,
    embedder_options: dict[str, Any] | None = None,
    options: DevLocalVectorStoreOptions | None = None,
) -> RetrieveParams:
    """Build RetrieveParams with typed dev local vector store options."""
    return RetrieveParams(
        embedder=embedder,
        embedder_options=embedder_options,
        options=options,
    )


def dev_local_vectorstore_index_params(
    *,
    embedder: Embedder,
    embedder_options: dict[str, Any] | None = None,
) -> IndexParams:
    """Build IndexParams for the dev local vector store indexer."""
    return IndexParams(
        embedder=embedder,
        embedder_options=embedder_options,
    )
