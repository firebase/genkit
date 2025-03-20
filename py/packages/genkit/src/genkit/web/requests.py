# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.

"""Helper functions for reading JSON request bodies."""

import json

from genkit.web.typing import Receive


async def read_json_body(receive: Receive, encoding='utf-8') -> dict:
    """Helper to read JSON request body.

    Args:
        receive: The receive function.
        encoding: The encoding of the request body.

    Returns:
        The JSON request body.
    """
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'').decode(encoding)
        more_body = message.get('more_body', False)

    return json.loads(body) if body else {}
