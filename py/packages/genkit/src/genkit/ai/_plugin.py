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
import inspect
from collections.abc import Awaitable
from typing import Any, Literal

from genkit.core.registry import ActionKind

from ..core.action import Action, ActionMetadata
from ._registry import GenkitRegistry


class Plugin(abc.ABC):
    """Abstract base class for implementing Genkit plugins.

    This class defines the interface that all plugins must implement.  Plugins
    provide a way to extend functionality by registering new actions, models, or
    other capabilities.
    """

    def plugin_name(self):
        """The name of the plugin.

        Returns:
            The name of the plugin.
        """
        return self.name

    # TODO: https://github.com/firebase/genkit/issues/2438
    # @abc.abstractmethod
    def resolve_action(  # noqa: B027
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        """Resolves an action by adding it to the provided GenkitRegistry.

        Args:
            ai: The Genkit registry.
            kind: The kind of action to resolve.
            name: The name of the action to resolve.

        Returns:
            None, action resolution is done by side-effect on the registry.
        """
        pass

    @abc.abstractmethod
    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin with the given registry.

        Args:
            ai: Registry to register plugin functionality.

        Returns:
            None, initialization is done by side-effect on the registry.
        """
        pass

    def list_actions(self) -> list[ActionMetadata]:
        """Generate a list of available actions or models.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects, each with the following attributes:
                - name (str): The name of the action or model.
                - kind (ActionKind): The type or category of the action.
                - info (dict): The metadata dictionary describing the model configuration and properties.
                - config_schema (type): The schema class used for validating the model's configuration.
        """
        return []


class PluginV2(abc.ABC):
    """Base class for v2 plugins that return actions instead of mutating registry.

    V2 plugins are decoupled from the registry - they create and return Action
    objects which the framework then registers. This enables:
    - Standalone usage (use plugins without framework)
    - Better testability (test plugins in isolation)

    Plugin authors should inherit from this class and implement the required methods.
    The version marker is set automatically.

    Example:
        >>> class MyPlugin(PluginV2):
        ...     name = "myplugin"
        ...
        ...     def init(self):
        ...         return [model(name="my-model", fn=self._generate)]
        ...
        ...     def resolve(self, action_type, name):
        ...         return model(name=name, fn=self._generate)
    """

    version: Literal["v2"] = "v2"
    """Version marker - set automatically by base class."""

    name: str
    """Plugin name (e.g., 'anthropic', 'openai'). Must be set by subclass."""

    @abc.abstractmethod
    def init(self) -> list[Action] | Awaitable[list[Action]]:
        """Return eagerly-initialized actions.

        Called once during Genkit initialization. Return actions you want
        created immediately (common models, frequently used tools, etc.).

        Can be sync or async.

        Returns:
            List of Action objects (not yet registered with any registry).

        Example:
            >>> def init(self):
            ...     from genkit.blocks.model import model
            ...     return [
            ...         model(name="gpt-4", fn=self._generate),
            ...         model(name="gpt-4o", fn=self._generate),
            ...     ]
        """
        ...

    @abc.abstractmethod
    def resolve(
        self,
        action_type: ActionKind,
        name: str,
    ) -> Action | None | Awaitable[Action | None]:
        """Resolve a specific action on-demand (lazy loading).

        Called when the framework needs an action that wasn't returned from init().
        Enables lazy loading of less-common models or actions.

        Can be sync or async.

        Args:
            action_type: Type of action requested (MODEL, EMBEDDER, TOOL, etc.).
            name: Name of the action (WITHOUT plugin prefix - framework strips it).

        Returns:
            Action object if this plugin can provide it, None if it cannot.

        Example:
            >>> def resolve(self, action_type, name):
            ...     if action_type == ActionKind.MODEL:
            ...         if name in SUPPORTED_MODELS:
            ...             from genkit.blocks.model import model
            ...             return model(name=name, fn=self._generate)
            ...     return None
        """
        ...

    def list(self) -> list[ActionMetadata] | Awaitable[list[ActionMetadata]]:
        """List all actions this plugin can provide.

        Used for discovery, developer tools, and documentation.
        Should return metadata for ALL actions the plugin supports,
        not just those returned from init().

        Can be sync or async.

        Returns:
            List of ActionMetadata objects (lightweight descriptions).

        Example:
            >>> def list(self):
            ...     return [
            ...         ActionMetadata(
            ...             name="gpt-4",
            ...             kind=ActionKind.MODEL,
            ...             info={"supports": {"vision": True}}
            ...         ),
            ...         # ... more models
            ...     ]
        """
        # Default implementation returns empty (can override)
        return []

    async def model(self, name: str) -> Action:
        """Convenience method to get a specific model action.

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
            ...     action = self.resolve(ActionKind.MODEL, name)
            ...     if not action:
            ...         raise ValueError(f\"Model {name} not found\")
            ...     return action
        """
        # Default implementation - plugins can override if needed
        if inspect.iscoroutinefunction(self.resolve):
            action = await self.resolve(ActionKind.MODEL, name)
        else:
            action = self.resolve(ActionKind.MODEL, name)

        if not action:
            raise ValueError(
                f"Model '{name}' not found in plugin '{self.name}'"
            )
        return action


def is_plugin_v2(plugin: Any) -> bool:
    return hasattr(plugin, "version") and getattr(plugin, "version") == "v2"

def is_plugin_v1(plugin: Any) -> bool:
    return isinstance(plugin, Plugin)
