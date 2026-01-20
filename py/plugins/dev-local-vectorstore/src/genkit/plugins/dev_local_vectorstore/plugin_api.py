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
from genkit.core.action import Action
from genkit.core.action import ActionMetadata
from genkit.core.registry import ActionKind
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

    def __init__(
        self,
        name: str,
    ):
        self.index_name = name

    async def init(self) -> list:
        """Initialize the plugin by creating and returning retriever and indexer actions.

        Returns:
            List of Action objects (retriever and indexer).
        """
        actions = []

        # Create retriever action
        retriever = DevLocalVectorStoreRetriever(
            index_name=self.index_name,
        )

        actions.append(
            Action(
                kind=ActionKind.RETRIEVER,
                name=self.index_name,
                fn=retriever.retrieve,
                metadata={
                    'retriever': {
                        'customOptions': to_json_schema(RetrieverOptionsSchema),
                    },
                },
            )
        )

        # Create indexer action
        indexer = DevLocalVectorStoreIndexer(
            index_name=self.index_name,
        )

        actions.append(
            Action(
                kind=ActionKind.INDEXER,
                name=self.index_name,
                fn=indexer.index,
                metadata={},
            )
        )

        return actions

    async def resolve(self, action_type: ActionKind, name: str):
        """Resolve an action.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action to resolve.

        Returns:
            None (all actions are returned by init).
        """
        return None

    async def list_actions(self) -> list[ActionMetadata]:
        """Advertise available actions for dev UI/reflection without initialization."""
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
