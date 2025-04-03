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

"""Abstract base class for Genkit plugins.

This module defines the base plugin interface that all plugins must implement.
It provides a way to initialize and register plugin functionality.
"""

import abc

from genkit.ai.registry import GenkitRegistry
from genkit.core.registry import ActionKind


class Plugin(abc.ABC):
    """Abstract base class for implementing Genkit plugins.

    This class defines the interface that all plugins must implement.  Plugins
    provide a way to extend functionality by registering new actions, models, or
    other capabilities.
    """

    def plugin_name(self):
        """The name of the plugin.

        Returns:
            The name of the plugin.
        """
        return self.name

    # TODO: https://github.com/firebase/genkit/issues/2438
    # @abc.abstractmethod
    def resolve_action(self, ai: GenkitRegistry, kind: ActionKind, name: str) -> None:
        """Resolves an action by adding it to the provided GenkitRegistry.

        Args:
            ai: The Genkit registry.
            kind: The kind of action to resolve.
            name: The name of the action to resolve.

        Returns:
            None, action resolution is done by side-effect on the registry.
        """
        pass

    @abc.abstractmethod
    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin with the given registry.

        Args:
            ai: Registry to register plugin functionality.

        Returns:
            None, initialization is done by side-effect on the registry.
        """
        pass
