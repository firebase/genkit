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

import threading
from collections.abc import Callable
from typing import Any

import structlog
from dotpromptz.dotprompt import Dotprompt

from genkit.core.action import (
    Action,
    ActionMetadata,
    create_action_key,
    parse_action_key,
    parse_plugin_name_from_action_name,
)
from genkit.core.action.types import ActionKind, ActionName, ActionResolver

logger = structlog.get_logger(__name__)

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
ActionStore = dict[ActionKind, dict[ActionName, Action]]


class Registry:
    """Central repository for Genkit resources.

    The Registry class serves as the central storage and management system for
    various Genkit resources including actions, trace stores, flow state stores,
    plugins, and schemas. It provides methods for registering new resources and
    looking them up at runtime.

    This class is thread-safe and can be safely shared between multiple threads.

    Attributes:
        entries: A nested dictionary mapping ActionKind to a dictionary of
            action names and their corresponding Action instances.
    """

    default_model: str | None = None

    def __init__(self):
        """Initialize an empty Registry instance."""
        self._action_resolvers: dict[str, ActionResolver] = {}
        self._list_actions_resolvers: dict[str, Callable] = {}
        self._entries: ActionStore = {}
        self._value_by_kind_and_name: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.dotprompt = Dotprompt()
        # TODO: Figure out how to set this.
        self.api_stability: str = 'stable'

    def register_action_resolver(self, plugin_name: str, resolver: ActionResolver) -> None:
        """Registers an ActionResolver function for a given plugin.

        Args:
            plugin_name: The name of the plugin.
            resolver: The ActionResolver instance to register.

        Raises:
            ValueError: If a resolver is already registered for the plugin.
        """
        with self._lock:
            if plugin_name in self._action_resolvers:
                raise ValueError(f'Plugin {plugin_name} already registered')
            self._action_resolvers[plugin_name] = resolver

    def register_list_actions_resolver(self, plugin_name: str, resolver: Callable) -> None:
        """Registers an Callable function to list available actions or models.

        Args:
            plugin_name: The name of the plugin.
            resolver: The Callable function to list models.

        Raises:
            ValueError: If a resolver is already registered for the plugin.
        """
        with self._lock:
            if plugin_name in self._list_actions_resolvers:
                raise ValueError(f'Plugin {plugin_name} already registered')
            self._list_actions_resolvers[plugin_name] = resolver

    def register_action(
        self,
        kind: ActionKind,
        name: str,
        fn: Callable,
        metadata_fn: Callable | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        span_metadata: dict[str, str] | None = None,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
    ) -> Action:
        """Register a new action with the registry.

        This method creates a new Action instance with the provided parameters
        and registers it in the registry under the specified kind and name.

        Args:
            kind: The type of action being registered (e.g., TOOL, MODEL).
            name: A unique name for the action within its kind.
            fn: The function to be called when the action is executed.
            metadata_fn: The function to be used to infer metadata (e.g.
                schemas).
            description: Optional human-readable description of the action.
            metadata: Optional dictionary of metadata about the action.
            span_metadata: Optional dictionary of tracing span metadata.
            input_schema: Optional JSON schema for the input.
            output_schema: Optional JSON schema for the output.

        Returns:
            The newly created and registered Action instance.
        """
        action = Action(
            kind=kind,
            name=name,
            fn=fn,
            metadata_fn=metadata_fn,
            description=description,
            metadata=metadata,
            span_metadata=span_metadata,
            input_schema=input_schema,
            output_schema=output_schema,
        )
        with self._lock:
            if kind not in self._entries:
                self._entries[kind] = {}
            self._entries[kind][name] = action
        return action

    def register_action_from_instance(self, action: Action) -> None:
        """Register an existing Action instance.
        Allows registering a pre-configured Action object, such as one created via
        `dynamic_resource` or other factory methods.
        Args:
           action: The action instance to register.
        """
        with self._lock:
            if action.kind not in self._entries:
                self._entries[action.kind] = {}
            self._entries[action.kind][action.name] = action

    async def resolve_action_names(self, key: str) -> list[str]:
        """Resolves all action names matching a key (including dynamic providers)."""
        kind, name = parse_action_key(key)
        if ':' in name:
            host_part, pattern = name.split(':', 1)
            provider_key = create_action_key(ActionKind.DYNAMIC_ACTION_PROVIDER, host_part)
            dap = await self.lookup_action_by_key(provider_key)
            if dap and is_dynamic_action_provider(dap):
                # pattern is like "tool/mytool" or "tool/*"
                if '/' in pattern:
                    p_kind_str, p_name_pattern = pattern.split('/', 1)
                    p_kind = ActionKind(p_kind_str)
                    metadata = await dap.list_action_metadata(p_kind, p_name_pattern)
                    return [f'{provider_key}:{p_kind.value}/{m.name}' for m in metadata]

        if await self.lookup_action(kind, name):
            return [key]
        return []

    async def lookup_action(self, kind: ActionKind, name: str) -> Action | None:
        """Look up an action by its kind and name.

        Args:
            kind: The type of action to look up.
            name: The name of the action to look up.

        Returns:
            The Action instance if found, None otherwise.
        """
        if ':' in name:
            host_part, tool_part = name.split(':', 1)
            provider_key = create_action_key(ActionKind.DYNAMIC_ACTION_PROVIDER, host_part)
            dap = await self.lookup_action_by_key(provider_key)
            if dap and is_dynamic_action_provider(dap):
                if '/' in tool_part:
                    p_kind_str, p_name = tool_part.split('/', 1)
                    p_kind = ActionKind(p_kind_str)
                    return await dap.get_action(p_kind, p_name)

        with self._lock:
            # If the entry does not exist, we fist try to call the action
            # resolver for the plugin to give it a chance to dynamically add the
            # action.
            if kind not in self._entries or name not in self._entries[kind]:
                plugin_name = parse_plugin_name_from_action_name(name)
                if plugin_name and plugin_name in self._action_resolvers:
                    self._action_resolvers[plugin_name](kind, name)

            if kind in self._entries and name in self._entries[kind]:
                return self._entries[kind][name]

            return None

    def get_actions_by_kind(self, kind: ActionKind) -> dict[str, Action]:
        """Returns a dictionary of all registered actions for a specific kind.

        Args:
            kind: The type of actions to retrieve (e.g., TOOL, MODEL, RESOURCE).

        Returns:
            A dictionary mapping action names to Action instances.
            Returns an empty dictionary if no actions of that kind are registered.
        """
        with self._lock:
            return self._entries.get(kind, {}).copy()

    async def lookup_action_by_key(self, key: str) -> Action | None:
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
        return await self.lookup_action(kind, name)

    async def list_serializable_actions(self, allowed_kinds: set[ActionKind] | None = None) -> dict[str, Any] | None:
        """Enlist all the actions into a dictionary.

        Args:
            allowed_kinds: The types of actions to list. If None, all actions
            are listed.

        Returns:
            A dictionary of serializable Actions.
        """
        with self._lock:
            actions = {}
            for kind in self._entries:
                if allowed_kinds is not None and kind not in allowed_kinds:
                    continue
                for name in self._entries[kind]:
                    action = await self.lookup_action(kind, name)
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

    async def list_resolvable_actions(self) -> dict[str, Any]:
        """Returns all resolvable actions including dynamic ones."""
        resolvable_actions = {}
        # TODO: parallelize or use resolvers?
        with self._lock:
            # First add all directly registered actions
            for kind in self._entries:
                for name, action in self._entries[kind].items():
                    key = create_action_key(kind, name)
                    resolvable_actions[key] = {
                        'name': action.name,
                        'inputSchema': action.input_schema,
                        'outputSchema': action.output_schema,
                        'metadata': action.metadata,
                    }
                    if is_dynamic_action_provider(action):
                        dap_prefix = key
                        dap_record = await action.get_action_metadata_record(dap_prefix)
                        resolvable_actions.update(dap_record)
        return resolvable_actions

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
        with self._lock:
            if kind not in self._value_by_kind_and_name:
                self._value_by_kind_and_name[kind] = {}

            if name in self._value_by_kind_and_name[kind]:
                raise ValueError(f'value for kind "{kind}" and name "{name}" is already registered')

            self._value_by_kind_and_name[kind][name] = value

    def lookup_value(self, kind: str, name: str) -> Any | None:
        """Looks up value that us previously registered by `register_value`.

        Args:
            kind: The kind of the value (e.g., "format", "default-model").
            name: The name of the value (e.g., "json", "text").

        Returns:
            The value or None if not found.
        """
        with self._lock:
            return self._value_by_kind_and_name.get(kind, {}).get(name)
