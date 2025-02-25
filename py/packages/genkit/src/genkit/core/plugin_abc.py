# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins.

This module defines the base plugin interface that all plugins must implement.
It provides a way to initialize and register plugin functionality.
"""

import abc

from genkit.core.registry import Registry


class Plugin(abc.ABC):
    """Abstract base class for implementing Genkit plugins.

    This class defines the interface that all plugins must implement.  Plugins
    provide a way to extend functionality by registering new actions, models, or
    other capabilities.

    Attributes:
        registry: Registry for plugin functionality.
    """

    @abc.abstractmethod
    def initialize(self, registry: Registry) -> None:
        """Initialize the plugin with the given registry.

        Args:
            registry: Registry to register plugin functionality.

        Returns:
            None
        """
        pass
