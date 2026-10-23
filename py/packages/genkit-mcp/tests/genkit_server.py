# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# SPDX-License-Identifier: Apache-2.0

"""A Genkit app served over MCP stdio, driven by the round-trip tests."""

import asyncio

import structlog
from genkit_mcp import create_mcp_server
from pydantic import BaseModel

from genkit import Genkit, GenkitError, MultipartToolResponse, Part
from genkit._core._typing import Resource

logger = structlog.get_logger(__name__)

IMAGE_URL = 'data:image/png;base64,aW1n'
AUDIO_URL = 'data:audio/wav;base64,c25k'
PDF_URL = 'data:application/pdf;base64,cGRm'
RESOURCE_URI = 'https://example.com/manual'

SERVER_NAME = 'roundtrip'

ai = Genkit()


class Shelf(BaseModel):
    """Output of the one tool whose schema MCP can advertise."""

    title: str
    count: int


@ai.tool()
async def plain_text() -> str:
    """Return a string."""
    await logger.ainfo('serving plain text')
    return 'plain text'


@ai.tool()
async def mapping() -> object:
    """Return an object."""
    return {'a': 1, 'b': [1, 2]}


@ai.tool()
async def listing() -> object:
    """Return an array."""
    return [1, 'x']


@ai.tool()
async def media() -> MultipartToolResponse:
    """Return one content part of every kind MCP has a block for."""
    return MultipartToolResponse(
        output='t',
        content=[
            Part.from_media(url=IMAGE_URL, content_type='image/png'),
            Part.from_media(url=AUDIO_URL, content_type='audio/wav'),
            Part.from_media(url=PDF_URL, content_type='application/pdf'),
            Part(resource=Resource(uri=RESOURCE_URI)),
        ],
    )


@ai.tool()
async def annotated() -> MultipartToolResponse:
    """Return output and metadata together."""
    return MultipartToolResponse(output={'k': 1}, metadata={'m': 2})


@ai.tool()
async def explode() -> str:
    """Fail."""
    raise ValueError('boom')


@ai.tool()
async def reject() -> str:
    """Fail with a message meant for the model, caused by one that is not."""
    raise GenkitError(
        status='INVALID_ARGUMENT',
        message='date must be in the future',
        cause=RuntimeError('GET https://api.example.com/v1?key=SECRET failed'),
    )


@ai.tool()
async def accented() -> str:
    """Return text outside ASCII."""
    return 'café 東京'


@ai.tool()
async def noted_object() -> MultipartToolResponse:
    """Return an object with a text part beside it."""
    return MultipartToolResponse(output={'k': 1}, content=[Part(text='note')])


@ai.tool()
async def noted_array() -> MultipartToolResponse:
    """Return an array with a text part beside it."""
    return MultipartToolResponse(output=[1, 2], content=[Part(text='note')])


@ai.tool()
async def text_parts() -> MultipartToolResponse:
    """Return text parts and no output."""
    return MultipartToolResponse(content=[Part(text='first '), Part(text='second')])


@ai.tool()
async def shelf() -> Shelf:
    """Return a typed object."""
    return Shelf(title='Poetry', count=3)


server = create_mcp_server(ai, SERVER_NAME)

logger.info('genkit_server imported')

if __name__ == '__main__':
    asyncio.run(server.start())
