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

"""Implementation of JSON output format."""

from typing import Any

from genkit.blocks.formats.types import FormatDef, Formatter, FormatterConfig
from genkit.blocks.model import (
    GenerateResponseWrapper,
    MessageWrapper,
)
from genkit.codec import dump_json
from genkit.core.extract import extract_json


class JsonFormat(FormatDef):
    """Defines a JSON format for use with AI models.

    This class provides functionality for parsing and formatting JSON data
    to interact with AI models, ensuring that the output conforms to a
    specified schema, if provided.
    """

    def __init__(self):
        """Initializes a JsonFormat instance.

        Sets up the format definition with configurations suitable for JSON,
        including content type, constraints, and default instructions.
        """
        super().__init__(
            'json',
            FormatterConfig(
                format='json',
                content_type='application/json',
                constrained=True,
                default_instructions=False,
            ),
        )

    def handle(self, schema: dict[str, Any] | None) -> Formatter:
        """Creates a Formatter for handling JSON data based on an optional schema.

        Args:
            schema: An optional dictionary representing the JSON schema.
                    If provided, the formatter will ensure that the output
                    conforms to this schema.

        Returns:
            A Formatter instance configured for JSON handling, including
            parsers for messages and chunks, and instructions derived from
            the provided schema.
        """

        def message_parser(msg: MessageWrapper):
            """Extracts JSON from a Message object.

            Concatenates the text content of all parts in the message and
            attempts to extract a JSON object from the resulting string.

            Args:
                msg: The Message object to parse.

            Returns:
                A JSON object extracted from the message content.
            """
            return extract_json(msg.text)

        def chunk_parser(chunk: GenerateResponseWrapper):
            """Extracts JSON from a GenerateResponseWrapper object.

            Extracts a JSON object from the accumulated text in the given chunk.

            Args:
                chunk: The GenerateResponseWrapper object to parse.

            Returns:
                A JSON object extracted from the chunk's accumulated text.
            """
            return extract_json(chunk.accumulated_text)

        instructions: str | None = None

        if schema:
            instructions = f"""\
Output should be in JSON format and conform to the following schema:

```
{dump_json(schema, indent=2)}
```
"""

        return Formatter(
            chunk_parser=chunk_parser,
            message_parser=message_parser,
            instructions=instructions,
        )
