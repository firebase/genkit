# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for Genkit plugins."""

from __future__ import annotations

import abc
import typing

if typing.TYPE_CHECKING:
    # TODO: Must point to an abstraction, not an actual implementation,
    #       which should resolve the circular import problem.
    from genkit.veneer import Genkit


class Plugin(abc.ABC):
    """
    Abstract base class for plugins.
    """

    @abc.abstractmethod
    def initialize(self, ai: Genkit) -> None:
        """
        Entrypoint for attaching the plugin to the Genkit Veneer.
        """
        pass
