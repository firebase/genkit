# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""The registry is used to store and lookup resources."""

from genkit.core.action import Action, ActionKind


class Registry:
    """Stores actions, trace stores, flow state stores, plugins, and schemas."""

    actions: dict[ActionKind, dict[str, Action]] = {}

    def register_action(self, action: Action) -> None:
        """Register an action.

        Args:
            action: The action to register.

        Raises:
            ValueError: If the action kind is not supported.
        """
        kind = action.kind
        if kind not in self.actions:
            self.actions[kind] = {}
        self.actions[kind][action.name] = action

    def lookup_action(self, kind: str, name: str) -> Action | None:
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
        # TODO: Use pattern matching to validate the key format
        # and verify whether the key can have only 2 parts.
        tokens = key.split('/')
        if len(tokens) != 2:
            msg = (
                f'Invalid action key format: `{key}`. '
                'Expected format: `<kind>/<name>`'
            )
            raise ValueError(msg)
        kind, name = tokens
        return self.lookup_action(kind, name)
