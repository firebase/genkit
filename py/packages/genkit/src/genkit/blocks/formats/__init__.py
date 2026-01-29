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


"""Genkit format package. Provides implementation for various formats like json, jsonl, etc.

Genkit includes built-in formats to handle common output patterns. These formats can be
specified in `GenerateActionOptions` or `OutputConfig`.

| Format | Description | Constraints |
| :--- | :--- | :--- |
| `json` | JSON object. Default when a schema is provided. | Enforced by `constrained: true`. |
| `text` | Returns the raw text output from the model. | No constraints. |
| `array` | JSON array of items. Useful for generating lists. | Enforced by `constrained: true`. |
| `enum` | Parses output as a single enum value. | Enforced by `constrained: true`. |
| `jsonl` | Newline-delimited JSON. Useful for streaming lists. | No constraints. |

Usage Example:

    # JSON Format (default with schema)
    ai.generate(
        output=OutputConfig(
            schema={'type': 'object', 'properties': {'foo': {'type': 'string'}}}
        )
    )

    # Array Format
    ai.generate(
        output=OutputConfig(
            format='array',
            schema={'type': 'array', 'items': {'type': 'string'}}
        )
    )

    # Enum Format
    ai.generate(
        output=OutputConfig(
            format='enum',
            schema={'type': 'string', 'enum': ['cat', 'dog']}
        )
    )
"""

from genkit.blocks.formats.array import ArrayFormat
from genkit.blocks.formats.enum import EnumFormat
from genkit.blocks.formats.json import JsonFormat
from genkit.blocks.formats.jsonl import JsonlFormat
from genkit.blocks.formats.text import TextFormat
from genkit.blocks.formats.types import FormatDef, Formatter, FormatterConfig


def package_name() -> str:
    """Get the fully qualified package name."""
    return 'genkit.blocks.formats'


built_in_formats = [
    ArrayFormat(),
    EnumFormat(),
    JsonFormat(),
    JsonlFormat(),
    TextFormat(),
]


__all__ = [
    'ArrayFormat',
    'EnumFormat',
    'FormatDef',
    'Formatter',
    'FormatterConfig',
    'JsonFormat',
    'JsonlFormat',
    'TextFormat',
    'package_name',
]
