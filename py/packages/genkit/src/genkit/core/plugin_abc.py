# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from genkit.core.schema_types import GenerateRequest, GenerateResponse

if TYPE_CHECKING:
    from genkit.veneer import Genkit


class Plugin(abc.ABC):
    """
    Abstract class defining common interface
    for the Genkit Plugin implementation

    NOTE: Any plugin defined for the Genkit must inherit from this class
    """

    @abc.abstractmethod
    def attach_to_veneer(self, veneer: Genkit) -> None:
        """
        Entrypoint for attaching the plugin to the requested Genkit Veneer

        Implementation must be provided for any inheriting plugin.

        Args:
            veneer: requested `genkit.veneer.Genkit` instance

        Returns:
            None
        """
        pass

    def _add_model_to_veneer(
        self, veneer: Genkit, name: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Defines plugin's model in the Genkit Registry

        Uses self._model_callback as a generic callback wrapper

        Args:
            veneer: requested `genkit.veneer.Genkit` instance
            name: name of the model to attach
            metadata: metadata information associated
                      with the provided model (optional)

        Returns:
            None
        """
        if not metadata:
            metadata = {}
        veneer.define_model(
            name=name, fn=self._model_callback, metadata=metadata
        )

    @abc.abstractmethod
    def _model_callback(self, request: GenerateRequest) -> GenerateResponse:
        """
        Wrapper around any plugin's model callback.

        Is considered an entrypoint for any model's request.
        Implementation must be provided for any inheriting plugin.

        Args:
            request: incoming request as generic
                     `genkit.core.schemas.GenerateRequest` instance

        Returns:
            Model response represented as generic
            `genkit.core.schemas.GenerateResponse` instance
        """
        pass
