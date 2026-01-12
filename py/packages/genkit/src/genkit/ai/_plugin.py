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
from collections.abc import Awaitable, Callable
from typing import Any

from genkit.core.registry import ActionKind

from ..core.action import Action, ActionMetadata
from ._registry import GenkitRegistry

# Type aliases for plugin resolver functions
ActionResolver = Callable[[ActionKind, str], Awaitable[Action | None]]
"""Async function that resolves an action by kind and name."""

ListActionsResolver = Callable[[], Awaitable[list[ActionMetadata]]]
"""Async function that returns a list of action metadata for discovery."""


class Plugin(abc.ABC):
    """Base class for Genkit plugins that return actions instead of mutating registry.

    Plugins are decoupled from the registry - they create and return Action
    objects which the framework then registers. This enables:
    - Standalone usage (use plugins without framework)
    - Better testability (test plugins in isolation)

    Plugin authors should inherit from this class and implement the required methods.

    Example:
        >>> class MyPlugin(Plugin):
        ...     name = 'myplugin'
        ...
        ...     async def init(self):
        ...         return [model(name='my-model', fn=self._generate)]
        ...
        ...     async def resolve(self, action_type, name):
        ...         return model(name=name, fn=self._generate)
        ...
        ...     async def list_actions(self):
        ...         return [ActionMetadata(name='my-model', kind=ActionKind.MODEL)]
    """

    name: str
    """Plugin name (e.g., 'anthropic', 'openai'). Must be set by subclass."""

    @abc.abstractmethod
    async def init(self) -> list[Action]:
        """Return eagerly-initialized actions.

        Called once during Genkit initialization. Return actions you want
        created immediately (common models, frequently used tools, etc.).

        Returns:
            List of Action objects (not yet registered with any registry).

        Example:
            >>> async def init(self):
            ...     from genkit.blocks.model import model
            ...
            ...     return [
            ...         model(name='gpt-4', fn=self._generate),
            ...         model(name='gpt-4o', fn=self._generate),
            ...     ]
        """
        ...

    @abc.abstractmethod
    async def resolve(
        self,
        action_type: ActionKind,
        name: str,
    ) -> Action | None:
        """Resolve a specific action on-demand (lazy loading).

        Called when the framework needs an action that wasn't returned from init().
        Enables lazy loading of less-common models or actions.

        Args:
            action_type: Type of action requested (MODEL, EMBEDDER, TOOL, etc.).
            name: Name of the action (WITHOUT plugin prefix - framework strips it).

        Returns:
            Action object if this plugin can provide it, None if it cannot.

        Example:
            >>> async def resolve(self, action_type, name):
            ...     if action_type == ActionKind.MODEL:
            ...         if name in SUPPORTED_MODELS:
            ...             from genkit.blocks.model import model
            ...
            ...             return model(name=name, fn=self._generate)
            ...     return None
        """
        ...

    async def list_actions(self) -> list[ActionMetadata]:
        """List all actions this plugin can provide.

        Used for discovery, developer tools, and documentation.
        Should return metadata for ALL actions the plugin supports,
        not just those returned from init().

        Returns:
            List of ActionMetadata objects (lightweight descriptions).

        Example:
            >>> async def list_actions(self):
            ...     return [
            ...         ActionMetadata(name='gpt-4', kind=ActionKind.MODEL, info={'supports': {'vision': True}}),
            ...         # ... more models
            ...     ]
        """
        # Default implementation returns empty (can override)
        return []

    async def model(self, name: str) -> Action:
        r"""Convenience method to get a specific model action.

        Enables clean standalone usage:
            plugin = SomePlugin()
            model = await plugin.model('model-name')
            response = await model.arun(...)

        Args:
            name: Model name (without plugin prefix).

        Returns:
            Action for the specified model.

        Raises:
            ValueError: If the model is not supported by this plugin.

        Example:
            >>> async def model(self, name: str) -> Action:
            ...     action = await self.resolve(ActionKind.MODEL, name)
            ...     if not action:
            ...         raise ValueError(f\"Model {name} not found\")
            ...     return action
        """
        # Call the async resolve method
        action = await self.resolve(ActionKind.MODEL, name)

        if not action:
            raise ValueError(f"Model '{name}' not found in plugin '{self.name}'")
        return action
