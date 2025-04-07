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

from genkit.ai import GenkitRegistry, Plugin
from genkit.core.action import Action
from genkit.plugins.firebase.constant import FirestoreRetrieverConfig
from genkit.plugins.firebase.retriever import FirestoreRetriever


def firestore_action_name(name: str) -> str:
    """Create a firestore action name.

    Args:
        name: Base name for the action

    Returns:
        str: Firestore action name.

    """
    return f'firestore/{name}'


class FirebaseAPI(Plugin):
    """Firestore retriever plugin."""

    name = 'firebaseFirestore'

    def __init__(self, params: list[FirestoreRetrieverConfig]):
        """Initialize the firestore plugin.

        Args:
            params: List of firestore retriever configurations.
        """
        self.params = params

    # TODO: Extend implementation of firestore indexer.
    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize firestore plugin.

        Register actions with the registry making them available for use in the Genkit framework.

        Args:
            ai: The registry to register actions with.

        Returns:
            None
        """
        for params in self.params:
            self._configure_firestore_retriever(ai=ai, params=params)

    @classmethod
    def _configure_firestore_retriever(cls, ai: GenkitRegistry, params: FirestoreRetrieverConfig) -> Action:
        """Registers Local Vector Store retriever for provided parameters.

        Args:
            ai: The registry to register the retriever with.
            params: Parameters to register the retriever with.

        Returns:
            registered Action instance.
        """
        retriever = FirestoreRetriever(
            ai=ai,
            params=params,
        )

        return ai.define_retriever(
            name=firestore_action_name(params.name),
            fn=retriever.retrieve,
        )
