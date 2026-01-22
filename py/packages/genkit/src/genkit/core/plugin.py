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

from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind


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

    async def model(self, name: str) -> Action:
        """Convenience method to resolve a model without using the registry.

        Prefixes local name with plugin namespace before calling resolve.

        Args:
            name: The model name (local or namespaced).

        Returns:
            Action: The resolved model action.

        Raises:
            ValueError: If the model is not found.
        """
        target = name if '/' in name else f'{self.name}/{name}'
        action = await self.resolve(ActionKind.MODEL, target)
        if action is None:
            raise ValueError(f'Model not found: {target}')
        return action
