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

"""Implementation of JSONL output format."""

from typing import Any, cast

import json5

from genkit.blocks.formats.types import FormatDef, Formatter, FormatterConfig
from genkit.blocks.model import (
    GenerateResponseChunkWrapper,
    MessageWrapper,
)
from genkit.codec import dump_json
from genkit.core._compat import override
from genkit.core.error import GenkitError
from genkit.core.extract import extract_json


class JsonlFormat(FormatDef):
    """Defines a JSONL format for use with AI models.

    This format instructs the model to output a sequence of JSON objects, one per line (JSONL).
    It is particularly useful for streaming lists of objects, as each line can be parsed independently
    as soon as it is generated, without waiting for the full array to close.

    The formatter handles:
    1.  Validating that the schema is an array of objects.
    2.  Injecting instructions to output JSONL.
    3.  Parsing the response line-by-line to recover objects.

    Usage:
        ai.generate(
            output=OutputConfig(
                format='jsonl',
                schema={
                    'type': 'array',
                    'items': {'type': 'object', 'properties': ...}
                }
            )
        )
    """

    def __init__(self) -> None:
        """Initializes the JsonlFormat.

        Configures the format with:
        - name: 'jsonl'
        - content_type: 'application/jsonl'
        """
        super().__init__(
            'jsonl',
            FormatterConfig(
                content_type='application/jsonl',
            ),
        )

    @override
    def handle(self, schema: dict[str, object] | None) -> Formatter[Any, Any]:
        """Creates a Formatter for handling JSONL data.

        Args:
            schema: The JSON schema. Must be type 'array' containing 'object' items.

        Returns:
            A Formatter configured to parse JSONL.

        Raises:
            GenkitError: If the schema structure matches expectations for JSONL.
        """
        if schema:
            schema_type = schema.get('type')
            items = schema.get('items')
            items_type: object | None = None
            if isinstance(items, dict):
                items_dict = cast(dict[str, object], items)
                items_type = items_dict.get('type')
            if schema_type != 'array' or items_type != 'object':
                raise GenkitError(
                    status='INVALID_ARGUMENT',
                    message=(
                        "Must supply an 'array' schema type containing 'object' items "
                        "when using the 'jsonl' parser format."
                    ),
                )

        def message_parser(msg: MessageWrapper) -> list[object]:
            """Parses a complete message into a list of objects."""
            lines = [line.strip() for line in msg.text.split('\n') if line.strip().startswith('{')]
            items = []
            for line in lines:
                extracted = extract_json(line, throw_on_bad_json=False)
                if extracted:
                    items.append(extracted)
            return items

        def chunk_parser(chunk: GenerateResponseChunkWrapper) -> list[object]:
            """Parses a streaming chunk into a list of objects found in that chunk."""
            # Calculate the length of text from previous chunks
            previous_text_len = len(chunk.accumulated_text) - len(chunk.text)

            # Find start index: after the last newline in previous text
            start_index = 0
            if previous_text_len > 0:
                last_newline = chunk.accumulated_text[:previous_text_len].rfind('\n')
                if last_newline != -1:
                    start_index = last_newline + 1

            # Process text from the start index onwards
            text_to_process = chunk.accumulated_text[start_index:]

            results = []
            lines = text_to_process.split('\n')
            for line in lines:
                trimmed = line.strip()
                if trimmed.startswith('{'):
                    try:
                        result = json5.loads(trimmed)
                        if result:
                            results.append(result)
                    except ValueError:
                        # Incomplete or invalid JSON line, stop processing this chunk
                        break
            return results

        instructions = None
        if schema and schema.get('items'):
            instructions = (
                'Output should be JSONL format, a sequence of JSON objects (one per line) '
                'separated by a newline `\\n` character. Each line should be a JSON object '
                'conforming to the following schema:\n\n'
                f'```\n{dump_json(schema["items"], indent=2)}\n```\n'
            )
        return Formatter(
            chunk_parser=chunk_parser,
            message_parser=message_parser,
            instructions=instructions,
        )
