# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Registry for managing Genkit resources and actions.

This module provides the Registry class, which is the central repository for
storing and managing various Genkit resources such as actions, flows,
plugins, and schemas. The registry enables dynamic registration and lookup
of these resources during runtime.

Example:
    >>> registry = Registry()
    >>> registry.register_action(my_action)
    >>> action = registry.get_action('my_action')
"""

from collections.abc import Callable
from typing import Any

from genkit.core.action import (
    Action,
    ActionKind,
    create_action_key,
    parse_action_key,
    parse_plugin_name_from_action_name,
)

type ActionName = str

type ActionResolver = Callable[[ActionKind, str], None]


class Registry:
    """Central repository for Genkit resources.

    The Registry class serves as the central storage and management system for
    various Genkit resources including actions, trace stores, flow state stores,
    plugins, and schemas. It provides methods for registering new resources and
    looking them up at runtime.

    Attributes:
        actions: A nested dictionary mapping ActionKind to a dictionary of
            action names and their corresponding Action instances.
    """

    default_model: str | None = None

    def __init__(self):
        """Initialize an empty Registry instance."""
        self.action_resolvers: dict[str, ActionResolver] = {}
        self.entries: dict[ActionKind, dict[ActionName, Action]] = {}
        # TODO: Figure out how to set this.
        self.api_stability: str = 'stable'

    def register_action_resolver(
        self, plugin_name: str, resolver: ActionResolver
    ):
        if plugin_name in self.action_resolvers:
            raise ValueError(f'Plugin {plugin_name} already registered')
        self.action_resolvers[plugin_name] = resolver

    def register_action(
        self,
        kind: ActionKind,
        name: str,
        fn: Callable,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        span_metadata: dict[str, str] | None = None,
    ) -> Action:
        """Register a new action with the registry.

        This method creates a new Action instance with the provided parameters
        and registers it in the registry under the specified kind and name.

        Args:
            kind: The type of action being registered (e.g., TOOL, MODEL).
            name: A unique name for the action within its kind.
            fn: The function to be called when the action is executed.
            description: Optional human-readable description of the action.
            metadata: Optional dictionary of metadata about the action.
            span_metadata: Optional dictionary of tracing span metadata.

        Returns:
            The newly created and registered Action instance.
        """
        action = Action(
            kind=kind,
            name=name,
            fn=fn,
            description=description,
            metadata=metadata,
            span_metadata=span_metadata,
        )
        if kind not in self.entries:
            self.entries[kind] = {}
        self.entries[kind][name] = action
        return action

    def lookup_action(self, kind: ActionKind, name: str) -> Action | None:
        """Look up an action by its kind and name.

        Args:
            kind: The type of action to look up.
            name: The name of the action to look up.

        Returns:
            The Action instance if found, None otherwise.
        """
        if kind not in self.entries or name not in self.entries[kind]:
            plugin_name = parse_plugin_name_from_action_name(name)
            if plugin_name and plugin_name in self.action_resolvers:
                self.action_resolvers[plugin_name](kind, name)

        if kind in self.entries and name in self.entries[kind]:
            return self.entries[kind][name]

    def lookup_action_by_key(self, key: str) -> Action | None:
        """Look up an action using its combined key string.

        The key format is `<kind>/<name>`, where kind must be a valid
        `ActionKind` and name must be a registered action name within that kind.

        Args:
            key: The action key in the format `<kind>/<name>`.

        Returns:
            The `Action` instance if found, None otherwise.

        Raises:
            ValueError: If the key format is invalid or the kind is not a valid
                `ActionKind`.
        """
        kind, name = parse_action_key(key)
        return self.lookup_action(kind, name)

    def list_serializable_actions(self) -> dict[str, Action] | None:
        """Enlist all the actions into a dictionary.

        Returns:
            A dictionary of serializable Actions.
        """
        actions = {}
        for kind in self.entries:
            for name in self.entries[kind]:
                action = self.lookup_action(kind, name)
                key = create_action_key(kind, name)
                # TODO: Serialize the Action instance
                actions[key] = {
                    'key': key,
                    'name': action.name,
                    'inputSchema': action.input_schema,
                    'outputSchema': action.output_schema,
                    'metadata': action.metadata,
                }
        return actions
