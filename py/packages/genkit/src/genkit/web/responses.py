# SPDX-License-Identifier: Apache-2.0


"""Helper functions for creating HTTP responses."""

import json
from typing import Any

from genkit.codec import dump_json
from genkit.web.enums import HTTPHeader

from .typing import HTTPScope, Receive, Send


async def json_response(
    scope: HTTPScope,
    receive: Receive,
    send: Send,
    data: Any,
    status_code: int = 200,
    headers: list[tuple[bytes, bytes]] = None,
    encoding: str = 'utf-8',
    more_body: bool = False,
) -> None:
    """Sends a JSON response.

    Args:
        scope: ASGI HTTP scope.
        receive: ASGI receive function.
        send: ASGI send function.
        data: The data to serialize as JSON.
        status_code: HTTP status code for the response.
        headers: The headers of the response.
        encoding: The encoding of the response.
        more_body: Whether to send more body.
    """
    if headers is None:
        headers = []
    await send({
        'type': 'http.response.start',
        'status': status_code,
        'headers': [
            (b'content-type', b'application/json'),
        ]
        + headers,
    })
    body = json.dumps(data).encode(encoding)
    await send({
        'type': 'http.response.body',
        'body': body,
        'more_body': more_body,
    })


async def json_response2(
    body: Any, status: int = 200, headers: dict[str, str] | None = None
) -> tuple[dict, dict]:
    """Create a JSON response.

    Args:
        body: The body of the response.
        status: The status code of the response.
        headers: The headers of the response.

    Returns:
        A tuple of the response and the body.
    """
    response_headers = [
        (HTTPHeader.CONTENT_TYPE, b'application/json'),
    ]
    if headers:
        response_headers.extend([
            (k.encode(), v.encode()) for k, v in headers.items()
        ])

    return {
        'type': 'http.response.start',
        'status': status,
        'headers': response_headers,
    }, {
        'type': 'http.response.body',
        'body': json.dumps(body).encode(),
    }


def json_chunk_response(chunk, encoding='utf-8'):
    """Create a JSON chunk response.

    Args:
        chunk: The chunk to send.
        encoding: The encoding of the response.

    Returns:
        A tuple of the response and the body.
    """
    chunk_data = dump_json(chunk).encode(encoding) + b'\n'
    return {
        'type': 'http.response.body',
        'body': chunk_data,
        'more_body': True,
    }


async def empty_response(status: int = 200) -> tuple[dict, dict]:
    """Create an empty response.

    Args:
        status: The status code of the response.

    Returns:
        A tuple of the response and the body.
    """
    return {
        'type': 'http.response.start',
        'status': status,
        'headers': [],
    }, {
        'type': 'http.response.body',
        'body': b'',
    }
