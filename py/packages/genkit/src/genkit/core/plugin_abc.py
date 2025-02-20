# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins."""

import abc

from genkit.core.registry import Registry


class Plugin(abc.ABC):
    """
    Abstract class defining common interface
    for the Genkit Plugin implementation

    NOTE: Any plugin defined for the Genkit must inherit from this class
    """

    @abc.abstractmethod
    def initialize(self, registry: Registry) -> None:
        """
        Entrypoint for initializing the plugin instance in Genkit

        Returns:
            None
        """
        pass
