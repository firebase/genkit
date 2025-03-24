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


"""Genkit format package. Provides implementation for various formats like json, jsonl, etc."""

from genkit.blocks.formats.json import JsonFormat
from genkit.blocks.formats.types import FormatDef, Formatter, FormatterConfig


def package_name() -> str:
    """Get the fully qualified package name."""
    return 'genkit.blocks.formats'


built_in_formats = [JsonFormat()]


__all__ = [
    FormatDef.__name__,
    Formatter.__name__,
    FormatterConfig.__name__,
    JsonFormat.__name__,
    package_name.__name__,
]
