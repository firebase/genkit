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

from functools import partial
from typing import Any

from google.auth.credentials import Credentials
from google.cloud import aiplatform_v1

from genkit.ai import Plugin
from genkit.blocks.retriever import RetrieverOptions, retriever_action_metadata
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
from genkit.plugins.vertex_ai.vector_search.retriever import (
    DocRetriever,
    RetrieverOptionsSchema,
)

VERTEXAI_PLUGIN_NAME = 'vertexai'


def vertexai_name(name: str) -> str:
    """Create a VertexAI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Google AI action name.
    """
    return f'{VERTEXAI_PLUGIN_NAME}/{name}'


class VertexAIVectorSearch(Plugin):
    """A plugin for integrating VertexAI Vector Search."""

    name: str = VERTEXAI_PLUGIN_NAME
    retriever_name: str = 'vertexAIVectorSearch'

    def __init__(
        self,
        retriever: DocRetriever,
        retriever_extra_args: dict[str, Any] | None = None,
        credentials: Credentials | None = None,
        project: str | None = None,
        location: str | None = 'us-central1',
        embedder: str | None = None,
        embedder_options: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the VertexAIVectorSearch plugin.

        Args:
            retriever: The DocRetriever class to use for retrieving documents.
            retriever_extra_args: Optional dictionary of extra arguments to pass to the
                retriever's constructor.
            credentials: Optional Google Cloud credentials to use. If not provided,
                the default application credentials will be used.
            project: Optional Google Cloud project ID. If not provided, it will be
                inferred from the credentials.
            location: Optional Google Cloud location (region). Defaults to
                'us-central1'.
            embedder: Optional identifier for the embedding model to use.
            embedder_options: Optional dictionary of options to pass to the embedding
                model.
        """
        self.project = project
        self.location = location

        self.embedder = embedder
        self.embedder_options = embedder_options

        self.retriever_cls = retriever
        self.retriever_extra_args = retriever_extra_args or {}

        self._match_service_client_generator = partial(
            aiplatform_v1.MatchServiceAsyncClient,
            credentials=credentials,
        )

    async def init(self) -> list[Action]:
        return [self._create_retriever_action()]

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        if action_type != ActionKind.RETRIEVER:
            return None
        if name != self.retriever_name:
            return None
        return self._create_retriever_action()

    async def list_actions(self) -> list[ActionMetadata]:
        return [
            retriever_action_metadata(
                name=self.retriever_name,
                options=RetrieverOptions(
                    label='Vertex AI Vector Search',
                    config_schema=to_json_schema(RetrieverOptionsSchema),
                ),
            )
        ]

    def _create_retriever_action(self) -> Action:
        metadata: dict[str, Any] = {
            'retriever': {
                'label': self.retriever_name,
                'customOptions': to_json_schema(RetrieverOptionsSchema),
            }
        }

        async def retrieve(request, ctx):
            ai = (ctx.context or {}).get('__genkit_ai__')
            if ai is None:
                raise ValueError(
                    'VertexAIVectorSearch retriever requires a Genkit instance in action context. '
                    'Use it via `await ai.retrieve(...)`.'
                )

            retriever = self.retriever_cls(
                ai=ai,
                name=self.retriever_name,
                match_service_client_generator=self._match_service_client_generator,
                embedder=self.embedder,
                embedder_options=self.embedder_options,
                **self.retriever_extra_args,
            )
            return await retriever.retrieve(request, ctx)

        return Action(
            kind=ActionKind.RETRIEVER,
            name=self.retriever_name,
            fn=retrieve,
            metadata=metadata,
        )
