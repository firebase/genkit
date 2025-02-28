# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins.

This module defines the base plugin interface that all plugins must implement.
It provides a way to initialize and register plugin functionality.
"""

import abc
from functools import cached_property

from genkit.core.registry import ActionKind
from genkit.veneer.registry import GenkitRegistry


class Plugin(abc.ABC):
    """Abstract base class for implementing Genkit plugins.

    This class defines the interface that all plugins must implement.  Plugins
    provide a way to extend functionality by registering new actions, models, or
    other capabilities.

    Attributes:
        registry: Registry for plugin functionality.
    """

    def plugin_name(self):
        """The name of the plugin.

        Returns:
            The name of the plugin.
        """
        return self.name

    def resolve_action(
        self, ai: GenkitRegistry, kind: ActionKind, name: str
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

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin with the given registry.

        Args:
            registry: Registry to register plugin functionality.

        Returns:
            None, initialization is done by side-effect on the registry.
        """
        pass
