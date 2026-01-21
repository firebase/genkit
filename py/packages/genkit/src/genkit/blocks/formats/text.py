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

"""Implementation of text output format."""

from typing import Any

from genkit.blocks.formats.types import FormatDef, Formatter, FormatterConfig
from genkit.blocks.model import (
    GenerateResponseWrapper,
    MessageWrapper,
)


class TextFormat(FormatDef):
    """Defines a text format for use with AI models.

    This class provides functionality for parsing and formatting text data
    to interact with AI models.
    """

    def __init__(self):
        """Initializes a TextFormat instance."""
        super().__init__(
            'text',
            FormatterConfig(
                format='text',
                content_type='text/plain',
                constrained=None,
                default_instructions=False,
            ),
        )

    def handle(self, schema: dict[str, Any] | None) -> Formatter:
        """Creates a Formatter for handling text data.

        Args:
            schema: Optional schema (ignored for text).

        Returns:
            A Formatter instance configured for text handling.
        """

        def message_parser(msg: MessageWrapper):
            """Extracts text from a Message object."""
            return msg.text

        def chunk_parser(chunk: GenerateResponseWrapper):
            """Extracts text from a GenerateResponseWrapper object."""
            return chunk.accumulated_text

        return Formatter(
            chunk_parser=chunk_parser,
            message_parser=message_parser,
            instructions=None,
        )
