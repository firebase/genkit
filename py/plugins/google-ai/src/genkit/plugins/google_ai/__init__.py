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


"""Google AI Plugin for Genkit.

This plugin provides integration with Google AI services and models.
"""

from genkit.plugins.google_ai.google_ai import (
    GoogleAi,
    GoogleAiPluginOptions,
    googleai_name,
)


def package_name() -> str:
    """Get the package name for the Google AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.google_ai'


__all__ = ['package_name', 'GoogleAi', 'GoogleAiPluginOptions', 'googleai_name']
