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

"""Local file-based vectorstore plugin that provides retriever and indexer for Genkit."""

from genkit.ai import GenkitRegistry, Plugin
from genkit.core.action import Action
from genkit.plugins.dev_local_vector_store.constant import Params
from genkit.plugins.dev_local_vector_store.indexer import (
    DevLocalVectorStoreIndexer,
)
from genkit.plugins.dev_local_vector_store.retriever import (
    DevLocalVectorStoreRetriever,
    RetrieverOptionsSchema,
)
from genkit.types import Docs


def dev_local_vectorstore_name(name: str) -> str:
    """Create a Dev Local Vector Store action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Dev Local Vector Store action name.
    """
    return f'devLocalVectorstore/{name}'


class DevLocalVectorStore(Plugin):
    """Local file-based vectorstore plugin that provides retriever and indexer.

    NOT INTENDED FOR USE IN PRODUCTION
    """

    name = 'devLocalVectorstore'
    _indexers: dict[str, DevLocalVectorStoreIndexer] = {}

    def __init__(self, params: list[Params]):
        self.params = params

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions with the registry.

        This method registers the Local Vector Store actions with the provided
        registry, making them available for use in the Genkit framework.

        Args:
            ai: The registry to register actions with.

        Returns:
            None
        """
        for params in self.params:
            self._configure_dev_local_retriever(ai=ai, params=params)
            self._configure_dev_local_indexer(ai=ai, params=params)

    @classmethod
    def _configure_dev_local_retriever(cls, ai: GenkitRegistry, params: Params) -> Action:
        """Registers Local Vector Store retriever for provided parameters.

        Args:
            ai: The registry to register retriever with.
            params: Parameters to register retriever with.

        Returns:
            registered Action instance
        """
        retriever = DevLocalVectorStoreRetriever(
            ai=ai,
            params=params,
        )

        return ai.define_retriever(
            name=dev_local_vectorstore_name(params.index_name),
            config_schema=RetrieverOptionsSchema,
            fn=retriever.retrieve,
        )

    @classmethod
    def _configure_dev_local_indexer(cls, ai: GenkitRegistry, params: Params) -> Action:
        """Registers Local Vector Store indexer for provided parameters.

        Args:
            ai: The registry to register indexer with.
            params: Parameters to register indexer with.

        Returns:
            registered Action instance
        """
        indexer = DevLocalVectorStoreIndexer(
            ai=ai,
            params=params,
        )

        cls._indexers[params.index_name] = indexer

    @classmethod
    async def index(cls, index_name: str, documents: Docs) -> None:
        """Lookups the Local Vector Store indexer for provided index name.

        If matching indexer found - invokes indexing for provided documents

        Args:
            index_name: name of the indexer to look up
            documents: list of documents to index

        Returns:
            None

        Raises:
            KeyError: if index name is not found among registered indexers.
        """
        matching_indexer = cls._indexers.get(index_name)
        if not matching_indexer:
            raise KeyError(
                f'Failed to find indexer matching name: {index_name}!r\nRegistered indexers: {cls._indexers.keys()}'
            )
        return await matching_indexer.index(documents)
