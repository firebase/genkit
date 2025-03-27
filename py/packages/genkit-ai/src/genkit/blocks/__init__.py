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

"""AI foundations for the Genkit framework.

This package provides the artificial intelligence and machine learning
capabilities of the Genkit framework. It includes:

    - Model interfaces for various AI models
    - Prompt management and templating
    - AI-specific utilities and helpers

The AI package enables seamless integration of AI models and capabilities
into applications built with Genkit.
"""


def package_name() -> str:
    """Get the fully qualified package name.

    Returns:
        The string 'genkit.blocks', which is the fully qualified package name.
    """
    return 'genkit.blocks'


__all__ = [package_name.__name__]
