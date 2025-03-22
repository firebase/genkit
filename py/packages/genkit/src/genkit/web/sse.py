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

"""Server-Sent Events (SSE) utilities for the Genkit web framework."""

import json
from collections.abc import AsyncGenerator
from typing import Any


def format_sse(
    data: dict[str, Any],
    event: str | None = None,
    id: str | None = None,
    retry: int | None = None,
) -> str:
    """Formats a dictionary as a Server-Sent Event (SSE).

    Args:
        data: Dictionary to format as an SSE message.
        event: Optional event name.
        id: Optional event ID.
        retry: Optional retry interval.

    Returns:
        String formatted according to the SSE protocol.
    """
    message = ''
    if id is not None:
        message += f'id: {id}\n'
    if event is not None:
        message += f'event: {event}\n'
    if retry is not None:
        message += f'retry: {retry}\n'

    message += f'data: {json.dumps(data)}\n\n'
    return message


async def sse_wrapper(
    data_generator: AsyncGenerator[dict[str, Any], None],
    event: str | None = None,
    id_prefix: str | None = None,
    retry: int | None = None,
) -> AsyncGenerator[str, None]:
    """Wraps an async generator of dicts and yields formatted SSE events.

    Args:
        data_generator: Async generator of dicts to format.
        event: Optional event name.
        id_prefix: Optional prefix for event IDs.
        retry: Optional retry interval.

    Yields:
        String formatted according to the SSE protocol.
    """
    counter = 0
    async for item in data_generator:
        id_val = f'{id_prefix}-{counter}' if id_prefix else str(counter)
        yield format_sse(item, event=event, id=id_val, retry=retry)
        counter += 1
