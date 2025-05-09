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

from genkit.ai import GenkitRegistry, Plugin
from genkit.plugins.vertex_ai import vertexai_name
from genkit.plugins.vertex_ai.models.retriever import (
    DocRetriever,
    RetrieverOptionsSchema,
)


class VertexAIVectorSearch(Plugin):
    """A plugin for integrating VertexAI Vector Search.

    This class registers VertexAI Vector Stores within a registry,
    and allows interaction to retrieve similar documents.
    """

    name: str = 'vertexAIVectorSearch'

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

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize plugin with the retriver specified.

        Register actions with the registry making them available for use in the Genkit framework.

        Args:
            ai: The registry to register actions with.
        """
        retriever = self.retriever_cls(
            ai=ai,
            name=self.name,
            match_service_client_generator=self._match_service_client_generator,
            embedder=self.embedder,
            embedder_options=self.embedder_options,
            **self.retriever_extra_args,
        )

        return ai.define_retriever(
            name=vertexai_name(self.name),
            config_schema=RetrieverOptionsSchema,
            fn=retriever.retrieve,
        )
