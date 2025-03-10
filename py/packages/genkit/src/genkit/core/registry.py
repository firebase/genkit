# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Registry for managing Genkit resources and actions.

This module provides the Registry class, which is the central repository for
storing and managing various Genkit resources such as actions, flows,
plugins, and schemas. The registry enables dynamic registration and lookup
of these resources during runtime.

Example:
    >>> registry = Registry()
    >>> registry.register_action('<action kind>', 'my_action', ...)
    >>> action = registry.lookup_action('<action kind>', 'my_action')
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

# An action store is a nested dictionary mapping ActionKind to a dictionary of
# action names and their corresponding Action instances.
#
# Structure for illustration:
#
# ```python
# {
#     ActionKind.MODEL: {
#         'gemini-2.0-flash': Action(...),
#         'gemini-2.0-pro': Action(...)
#     },
# }
# ```
type ActionStore = dict[ActionKind, dict[ActionName, Action]]


class Registry:
    """Central repository for Genkit resources.

    The Registry class serves as the central storage and management system for
    various Genkit resources including actions, trace stores, flow state stores,
    plugins, and schemas. It provides methods for registering new resources and
    looking them up at runtime.

    Attributes:
        entries: A nested dictionary mapping ActionKind to a dictionary of
            action names and their corresponding Action instances.
    """

    default_model: str | None = None

    def __init__(self):
        """Initialize an empty Registry instance."""
        self._action_resolvers: dict[str, ActionResolver] = {}
        self._entries: ActionStore = {}
        self._value_by_kind_and_name: dict[str, dict[str, Any]] = {}

        # TODO: Figure out how to set this.
        self.api_stability: str = 'stable'

    def register_action_resolver(
        self, plugin_name: str, resolver: ActionResolver
    ):
        """Registers an ActionResolver function for a given plugin.

        Args:
            plugin_name: The name of the plugin.
            resolver: The ActionResolver instance to register.

        Raises:
            ValueError: If a resolver is already registered for the plugin.
        """
        if plugin_name in self._action_resolvers:
            raise ValueError(f'Plugin {plugin_name} already registered')
        self._action_resolvers[plugin_name] = resolver

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
        if kind not in self._entries:
            self._entries[kind] = {}
        self._entries[kind][name] = action
        return action

    def lookup_action(self, kind: ActionKind, name: str) -> Action | None:
        """Look up an action by its kind and name.

        Args:
            kind: The type of action to look up.
            name: The name of the action to look up.

        Returns:
            The Action instance if found, None otherwise.
        """
        # If the entry does not exist, we fist try to call the action resolver
        # for the plugin to give it a chance to dynamically add the action.
        if kind not in self._entries or name not in self._entries[kind]:
            plugin_name = parse_plugin_name_from_action_name(name)
            if plugin_name and plugin_name in self._action_resolvers:
                self._action_resolvers[plugin_name](kind, name)

        if kind in self._entries and name in self._entries[kind]:
            return self._entries[kind][name]

        return None

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
        for kind in self._entries:
            for name in self._entries[kind]:
                action = self.lookup_action(kind, name)
                if action is not None:
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

    def register_value(self, kind: str, name: str, value: Any):
        """Registers a value with a given kind and name.

        This method stores a value in a nested dictionary, where the first level
        is keyed by the 'kind' and the second level is keyed by the 'name'.
        It prevents duplicate registrations for the same kind and name.

        Args:
            kind: The kind of the value (e.g., "format", "default-model").
            name: The name of the value (e.g., "json", "text").
            value: The value to be registered. Can be of any non-serializable
                type.

        Raises:
            ValueError: If a value with the given kind and name is already
            registered.
        """
        if kind not in self._value_by_kind_and_name:
            self._value_by_kind_and_name[kind] = {}

        if name in self._value_by_kind_and_name[kind]:
            raise ValueError(
                f'value for kind "{kind}" '
                f'and name "{name}" is already registered'
            )

        self._value_by_kind_and_name[kind][name] = value

    def lookup_value(self, kind: str, name: str) -> Any | None:
        """Looks up value that us previously registered by `register_value`.

        Args:
            kind: The kind of the value (e.g., "format", "default-model").
            name: The name of the value (e.g., "json", "text").

        Returns:
            The value or None if not found.
        """
        return self._value_by_kind_and_name.get(kind, {}).get(name)
