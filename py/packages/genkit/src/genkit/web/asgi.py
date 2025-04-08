"""ASGI utilities for the Genkit framework."""

import urllib.parse
from collections.abc import AsyncGenerator

from .typing import HTTPScope, Receive, Send


async def send_response(send: Send, status: int, headers: list[tuple[bytes, bytes]], body: bytes = b'') -> None:
    """Sends a standard HTTP response via ASGI send channel."""
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers,
    })
    await send({'type': 'http.response.body', 'body': body})


async def send_streaming_response(
    send: Send,
    status: int,
    headers: list[tuple[bytes, bytes]],
    body_generator: AsyncGenerator[bytes, None],
) -> None:
    """Sends a streaming HTTP response via ASGI send channel."""
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers,
    })
    async for chunk in body_generator:
        await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
    await send({'type': 'http.response.body', 'body': b'', 'more_body': False})


async def read_body(receive: Receive) -> bytes:
    """Reads the request body from an ASGI receive channel."""
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    return body


def is_streaming_requested_from_scope(scope: HTTPScope) -> bool:
    """Check if streaming is requested based on ASGI scope.

    Streaming is requested if the query parameter 'stream' is set to 'true' or
    if the Accept header is 'text/event-stream'.

    Args:
        scope: The ASGI HTTPScope dictionary.

    Returns:
        True if streaming is requested, False otherwise.
    """
    # Check header
    accept_header = ''
    for key, value in scope.get('headers', []):
        if key.lower() == b'accept':
            accept_header = value.decode('latin-1')  # Headers use latin-1
            break
    by_header = accept_header == 'text/event-stream'

    # Check query parameter
    query_string = scope.get('query_string', b'')
    query_params = urllib.parse.parse_qs(query_string.decode('ascii'))  # Query strings are typically ASCII
    by_query = query_params.get('stream', ['false'])[0] == 'true'

    return by_header or by_query
