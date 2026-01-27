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

"""Abstract base class for Genkit plugins.

This module defines the base plugin interface that all plugins must implement.
It provides a way to initialize and register plugin functionality.
"""

import abc
from typing import TYPE_CHECKING

from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind

if TYPE_CHECKING:
    from genkit.blocks.embedding import EmbedderRef
    from genkit.blocks.model import ModelReference


class Plugin(abc.ABC):
    """Abstract base class for implementing Genkit plugins.

    This class defines the async plugin interface that all plugins must implement.
    Plugins provide a way to extend functionality by registering new actions, models,
    or other capabilities.
    """

    name: str  # plugin namespace

    @abc.abstractmethod
    async def init(self) -> list[Action]:
        """Lazy warm-up called once per plugin per registry instance.

        This method is called lazily when the first action resolution attempt
        involving this plugin occurs. It should return a list of Action objects
        to pre-register.

        Returns:
            list[Action]: A list of Action instances to register.
        """
        ...

    @abc.abstractmethod
    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve a single action.

        The registry will call this with a namespaced name (e.g., "plugin/model-name").

        Args:
            action_type: The kind of action to resolve.
            name: The namespaced name of the action to resolve.

        Returns:
            Action | None: The Action instance if found, None otherwise.
        """
        ...

    @abc.abstractmethod
    async def list_actions(self) -> list[ActionMetadata]:
        """Advertised set for dev UI/reflection listing endpoint.

        This method should be safe and ideally inexpensive. It returns the set
        of actions that this plugin advertises without triggering full initialization.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects describing
                available actions.
        """
        ...

    def model(self, name: str) -> 'ModelReference':
        """Creates a model reference.

        Prefixes local name with plugin namespace.

        Args:
            name: The model name (local or namespaced).

        Returns:
            ModelReference: A reference to the model.
        """
        from genkit.blocks.model import ModelReference

        target = name if '/' in name else f'{self.name}/{name}'
        return ModelReference(name=target)

    def embedder(self, name: str) -> 'EmbedderRef':
        """Creates an embedder reference.

        Prefixes local name with plugin namespace.

        Args:
            name: The embedder name (local or namespaced).

        Returns:
            EmbedderRef: A reference to the embedder.
        """
        from genkit.blocks.embedding import EmbedderRef

        target = name if '/' in name else f'{self.name}/{name}'
        return EmbedderRef(name=target)
