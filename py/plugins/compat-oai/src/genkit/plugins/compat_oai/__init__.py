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


"""OpenAI-compatible model provider for Genkit."""

from .openai_plugin import OpenAI, openai_model
from .typing import OpenAIConfig


def package_name() -> str:
    """The package name for the OpenAI-compatible model provider."""
    return 'genkit.plugins.compat_oai'


__all__ = ['OpenAI', 'OpenAIConfig', 'openai_model', 'package_name']
