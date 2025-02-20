# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""The registry is used to store and lookup resources such as actions and
flows."""

from typing import Any, Callable, Dict

from genkit.core.action import Action, ActionKind, parse_action_key

"""Stores actions, trace stores, flow state stores, plugins, and schemas."""


class Registry:
    """Stores actions, trace stores, flow state stores, plugins, and schemas."""

    actions: dict[ActionKind, dict[str, Action]] = {}

    def register_action(
        self,
        kind: ActionKind,
        name: str,
        fn: Callable,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        span_metadata: dict[str, str] | None = None,
    ) -> Action:
        """Register an action.

        Args:
            kind: The kind of the action.
            name: The name of the action.
            fn: The function to call when the action is executed.
            description: The description of the action.
            metadata: The metadata of the action.
            span_metadata: The span metadata of the action.

        Returns:
            The registered action.
        """
        action = Action(
            kind=kind,
            name=name,
            fn=fn,
            description=description,
            metadata=metadata,
            span_metadata=span_metadata,
        )
        if kind not in self.actions:
            self.actions[kind] = {}
        self.actions[kind][name] = action
        return action

    def lookup_action(self, kind: ActionKind, name: str) -> Action | None:
        """Lookup an action by its kind and name.

        Args:
            kind: The kind of the action.
            name: The name of the action.

        Returns:
            The action if found, otherwise None.
        """
        if kind in self.actions and name in self.actions[kind]:
            return self.actions[kind][name]

    def lookup_action_by_key(self, key: str) -> Action | None:
        """Lookup an action by its key.

        The key is of the form:
        <kind>/<name>

        Args:
            key: The key to lookup the action by.

        Returns:
            The action if found, otherwise None.

        Raises:
            ValueError: If the key format is invalid.
        """
        kind, name = parse_action_key(key)
        return self.lookup_action(kind, name)
