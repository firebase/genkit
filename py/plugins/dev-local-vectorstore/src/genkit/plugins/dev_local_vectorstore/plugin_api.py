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

from typing import Any

from genkit.ai import Plugin
from genkit.blocks.retriever import (
    IndexerOptions,
    RetrieverOptions,
    indexer_action_metadata,
    retriever_action_metadata,
)
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema

from .indexer import (
    DevLocalVectorStoreIndexer,
)
from .retriever import (
    DevLocalVectorStoreRetriever,
    RetrieverOptionsSchema,
)


class DevLocalVectorStore(Plugin):
    """Local file-based vectorstore plugin that provides retriever and indexer.

    NOT INTENDED FOR USE IN PRODUCTION
    """

    name = 'devLocalVectorstore'

    def __init__(self, name: str, embedder: str, embedder_options: dict[str, Any] | None = None):
        self.index_name = name
        self.embedder = embedder
        self.embedder_options = embedder_options

    async def init(self) -> list[Action]:
        return [
            self._create_retriever_action(),
            self._create_indexer_action(),
        ]

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        if name != self.index_name:
            return None
        if action_type == ActionKind.RETRIEVER:
            return self._create_retriever_action()
        if action_type == ActionKind.INDEXER:
            return self._create_indexer_action()
        return None

    async def list_actions(self) -> list[ActionMetadata]:
        return [
            retriever_action_metadata(
                name=self.index_name,
                options=RetrieverOptions(
                    label=self.index_name,
                    config_schema=to_json_schema(RetrieverOptionsSchema),
                ),
            ),
            indexer_action_metadata(
                name=self.index_name,
                options=IndexerOptions(
                    label=self.index_name,
                ),
            ),
        ]

    def _create_retriever_action(self) -> Action:
        metadata: dict[str, Any] = {
            'retriever': {
                'label': self.index_name,
                'customOptions': to_json_schema(RetrieverOptionsSchema),
            }
        }

        async def retrieve(request, ctx):
            ai = (ctx.context or {}).get('__genkit_ai__')
            if ai is None:
                raise ValueError(
                    'DevLocalVectorStore retriever requires a Genkit instance in action context. '
                    'Use it via `await ai.retrieve(...)`.'
                )
            retriever = DevLocalVectorStoreRetriever(
                ai=ai,
                index_name=self.index_name,
                embedder=self.embedder,
                embedder_options=self.embedder_options,
            )
            return await retriever.retrieve(request, ctx)

        return Action(kind=ActionKind.RETRIEVER, name=self.index_name, fn=retrieve, metadata=metadata)

    def _create_indexer_action(self) -> Action:
        metadata: dict[str, Any] = {
            'indexer': {
                'label': self.index_name,
            }
        }

        async def index(request, ctx):
            ai = (ctx.context or {}).get('__genkit_ai__')
            if ai is None:
                raise ValueError(
                    'DevLocalVectorStore indexer requires a Genkit instance in action context. '
                    'Use it via `await ai.index(...)`.'
                )
            indexer = DevLocalVectorStoreIndexer(
                ai=ai,
                index_name=self.index_name,
                embedder=self.embedder,
                embedder_options=self.embedder_options,
            )
            return await indexer.index(request)

        return Action(kind=ActionKind.INDEXER, name=self.index_name, fn=index, metadata=metadata)
