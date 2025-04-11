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


"""Core foundations for the Genkit framework.

This package provides the fundamental building blocks and abstractions used
throughout the Genkit framework. It includes:

    - Action system for defining and managing callable functions
    - Plugin architecture for extending framework functionality
    - Registry for managing resources and actions
    - Tracing and telemetry for monitoring and debugging
    - Schema types for data validation and serialization
"""

from .constants import GENKIT_CLIENT_HEADER, GENKIT_VERSION


def package_name() -> str:
    """Get the fully qualified package name.

    Returns:
        The string 'genkit.core', which is the fully qualified package name.
    """
    return 'genkit.core'


__all__ = [package_name.__name__, 'GENKIT_CLIENT_HEADER', 'GENKIT_VERSION']
