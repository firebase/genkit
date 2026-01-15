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

from collections.abc import Callable
from typing import Any

from google.cloud.firestore_v1 import DocumentSnapshot
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from genkit.ai import Genkit, Plugin
from genkit.blocks.retriever import RetrieverOptions, retriever_action_metadata
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.plugins.firebase.retriever import FirestoreRetriever

from .constant import MetadataTransformFn


def firestore_action_name(name: str) -> str:
    """Create a firestore action name.

    Args:
        name: Base name for the action

    Returns:
        str: Firestore action name.

    """
    return f'firestore/{name}'


class FirestoreVectorStore(Plugin):
    """Firestore retriever plugin.

    Args:
        name: name if the retriever.
        collection: The name of the Firestore collection to query.
        vector_field: The name of the field containing the vector embeddings.
        content_field: The name of the field containing the document content, you wish to return.
        embedder: The embedder to use with this retriever.
        embedder_options: Optional configuration to pass to the embedder.
        distance_measure: The distance measure to use when comparing vectors. Defaults to 'COSINE'.
        firestore_client: The Firestore database instance from which to query.
        metadata_fields: Optional list of metadata fields to include.
    """

    name = 'firestore'

    def __init__(
        self,
        retriever_name: str,
        firestore_client: Any,
        collection: str,
        vector_field: str,
        content_field: str | Callable[[DocumentSnapshot], list[dict[str, str]]],
        embedder: str,
        embedder_options: dict[str, Any] | None = None,
        distance_measure: DistanceMeasure = DistanceMeasure.COSINE,
        metadata_fields: list[str] | MetadataTransformFn | None = None,
        ai: Genkit | None = None,
    ) -> None:
        """Initialize the firestore plugin.

        Args:
            retriever_name: name if the retriever.
            collection: The name of the Firestore collection to query.
            vector_field: The name of the field containing the vector embeddings.
            content_field: The name of the field containing the document content, you wish to return.
            embedder: The embedder to use with this retriever.
            embedder_options: Optional configuration to pass to the embedder.
            distance_measure: The distance measure to use when comparing vectors. Defaults to 'COSINE'.
            firestore_client: The Firestore database instance from which to query.
            metadata_fields: Optional list of metadata fields to include.
            ai: Optional Genkit instance for retriever initialization.
        """
        self.retriever_name = retriever_name
        self.firestore_client = firestore_client
        self.collection = collection
        self.vector_field = vector_field
        self.content_field = content_field
        self.embedder = embedder
        self.embedder_options = embedder_options
        self.distance_measure = distance_measure
        self.metadata_fields = metadata_fields
        self.ai = ai

    async def init(self) -> list[Action]:
        """Initialize firestore plugin.

        Creates and returns the retriever action.

        Returns:
            List containing the retriever Action.
        """
        if self.ai is None:
            return []

        retriever = FirestoreRetriever(
            ai=self.ai,
            name=self.retriever_name,
            firestore_client=self.firestore_client,
            collection=self.collection,
            vector_field=self.vector_field,
            content_field=self.content_field,
            embedder=self.embedder,
            embedder_options=self.embedder_options,
            distance_measure=self.distance_measure,
            metadata_fields=self.metadata_fields,
        )

        action = Action(
            kind=ActionKind.RETRIEVER,
            name=firestore_action_name(self.retriever_name),
            fn=retriever.retrieve,
        )

        return [action]

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action by name.

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action to resolve.

        Returns:
            Action object if found, None otherwise.
        """
        if action_type != ActionKind.RETRIEVER:
            return None

        # Extract local name (remove plugin prefix)
        expected_name = firestore_action_name(self.retriever_name)
        if name != expected_name:
            return None

        if self.ai is None:
            return None

        retriever = FirestoreRetriever(
            ai=self.ai,
            name=self.retriever_name,
            firestore_client=self.firestore_client,
            collection=self.collection,
            vector_field=self.vector_field,
            content_field=self.content_field,
            embedder=self.embedder,
            embedder_options=self.embedder_options,
            distance_measure=self.distance_measure,
            metadata_fields=self.metadata_fields,
        )

        return Action(
            kind=ActionKind.RETRIEVER,
            name=name,
            fn=retriever.retrieve,
        )

    async def list_actions(self) -> list[ActionMetadata]:
        """List available retriever actions.

        Returns:
            List of ActionMetadata for the retriever.
        """
        return [
            retriever_action_metadata(
                name=firestore_action_name(self.retriever_name),
                options=RetrieverOptions(),
            )
        ]
