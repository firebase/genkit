# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins.

This module defines the base plugin interface that all plugins must implement.
It provides a way to initialize and register plugin functionality.
"""

import abc
from functools import cached_property

from genkit.core.registry import ActionKind
from genkit.veneer.registry import GenkitRegisry


class Plugin(abc.ABC):
    """Abstract base class for implementing Genkit plugins.

    This class defines the interface that all plugins must implement.  Plugins
    provide a way to extend functionality by registering new actions, models, or
    other capabilities.

    Attributes:
        registry: Registry for plugin functionality.
    """

    @abc.abstractmethod
    @cached_property
    def name(self):
        pass

    def resolve_action(
        self, ai: GenkitRegisry, kind: ActionKind, name: str
    ) -> None:
        pass

    def initialize(self, ai: GenkitRegisry) -> None:
        """Initialize the plugin with the given registry.

        Args:
            registry: Registry to register plugin functionality.

        Returns:
            None
        """
        pass
