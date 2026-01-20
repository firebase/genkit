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

from dataclasses import dataclass
from functools import partial
from typing import Any

from google.auth.credentials import Credentials
from google.cloud import aiplatform_v1

from genkit.core.action import Action

from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
from genkit.plugins.vertex_ai.vector_search.retriever import (
    DocRetriever,
    RetrieverOptionsSchema,
)


def vertexai_vector_search_name(name: str) -> str:
    """Create a Vertex AI Vector Search action name under the VertexAI namespace.

    Args:
        name: Local name for the action.

    Returns:
        The fully qualified action name under the VertexAI plugin namespace.
    """
    return f'vertexai/{name}'


@dataclass(frozen=True)
class VectorSearchConfig:
    """Configuration for registering a vector search retriever."""

    retriever: type[DocRetriever]
    retriever_extra_args: dict[str, Any] | None = None
    credentials: Credentials | None = None
    retriever_name: str = 'vertexAIVectorSearch'


def create_vector_search_action(
    *,
    retriever: type[DocRetriever],
    retriever_name: str,
    retriever_extra_args: dict[str, Any] | None = None,
    credentials: Credentials | None = None,
    action_name: str | None = None,
) -> Action:
    """Create a retriever action for Vertex AI Vector Search."""
    match_service_client_generator = partial(
        aiplatform_v1.MatchServiceAsyncClient,
        credentials=credentials,
    )
    retriever_instance = retriever(
        name=retriever_name,
        match_service_client_generator=match_service_client_generator,
        **(retriever_extra_args or {}),
    )
    return Action(
        kind=ActionKind.RETRIEVER,
        name=action_name or retriever_name,
        fn=retriever_instance.retrieve,
        metadata={
            'retriever': {
                'label': retriever_name,
                'customOptions': to_json_schema(RetrieverOptionsSchema),
            }
        },
    )
