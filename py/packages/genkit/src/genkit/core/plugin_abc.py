# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins."""

from __future__ import annotations

import abc
import typing

if typing.TYPE_CHECKING:
    from genkit.veneer import Genkit


class Plugin(abc.ABC):
    """
    Abstract class defining common interface
    for the Genkit Plugin implementation

    NOTE: Any plugin defined for the Genkit must inherit from this class
    """

    def attach_to_veneer(self, veneer: Genkit) -> None:
        """
        Entrypoint for attaching the plugin to the requested Genkit Veneer

        Implementation must be provided for any inheriting plugin.

        Args:
            veneer: requested `genkit.veneer.Genkit` instance

        Returns:
            None
        """
        self._add_models_to_veneer(veneer=veneer)
        self._add_embedders_to_veneer(veneer=veneer)

    @abc.abstractmethod
    def _add_models_to_veneer(self, veneer: Genkit) -> None:
        """
        Defines plugin's model in the Genkit Registry

        Uses self._model_callback as a generic callback wrapper

        Args:
            veneer: requested `genkit.veneer.Genkit` instance

        Returns:
            None
        """

    @abc.abstractmethod
    def _add_embedders_to_veneer(self, veneer: Genkit) -> None:
        """Defines plugin's embedders in the Genkit Registry.

        Args:
            veneer: requested `genkit.veneer.Genkit` instance

        Returns:
            None
        """
