#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the JSON format."""

from genkit.blocks.formats import JsonFormat
from genkit.blocks.model import GenerateResponseChunkWrapper, MessageWrapper
from genkit.core.typing import GenerateResponseChunk, Message, TextPart


def test_json_format() -> None:
    json = JsonFormat()

    json_format = json.handle({
        'properties': {
            'value': {
                'description': 'value field',
                'type': 'string',
            }
        },
        'type': 'object',
    })

    assert (
        json_format.instructions
        == """Output should be in JSON format and conform to the following schema:

```
{
  "properties": {
    "value": {
      "description": "value field",
      "type": "string"
    }
  },
  "type": "object"
}
```
"""
    )

    assert json_format.parse_message(MessageWrapper(Message(role='user', content=[TextPart(text='{"foo": "bar')]))) == {
        'foo': 'bar'
    }

    assert json_format.parse_chunk(
        GenerateResponseChunkWrapper(
            GenerateResponseChunk(content=[TextPart(text='", "baz": [1,2')]),
            index=0,
            previous_chunks=[
                GenerateResponseChunk(content=[TextPart(text='{"bar":'), TextPart(text='"ba')]),
                GenerateResponseChunk(content=[TextPart(text='z')]),
            ],
        )
    ) == {'bar': 'baz', 'baz': [1, 2]}
