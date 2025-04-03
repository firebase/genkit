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

"""Utility functions to work with ports."""

import asyncio
import contextlib
import socket


async def is_port_available(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a specific port is available for binding.

    Args:
        port: The port number to check
        host: The host address to bind to (default: '127.0.0.1')

    Returns:
        True if the port is available, False otherwise
    """
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)

    # Set the socket to reuse the address to avoid "Address already in use"
    # errors.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # Use asyncio to handle the non-blocking socket
        await asyncio.get_event_loop().sock_connect(sock, (host, port))
        # If we get here, the port is in use
        return False
    except (ConnectionRefusedError, OSError):
        # Connection refused means the port is available
        return True
    finally:
        # Always close the socket
        with contextlib.suppress(Exception):
            sock.close()


def is_port_available_sync(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a specific port is available for binding.

    Args:
        port: The port number to check
        host: The host address to bind to (default: '127.0.0.1')

    Returns:
        True if the port is available, False otherwise.
    """
    try:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', port))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return True
    except OSError:
        return False


def find_free_port_sync(lower: int, upper: int) -> int:
    """Find an unused port in lower-upper range. If not found raises an exception.

    Args:
        lower: The lower bound of the port range.
        upper: The upper bound of the port range.

    Returns:
        An unused port in the range.

    Raises:
        OSError: If no free port is found in the range.
    """
    for port in range(lower, upper + 1):
        if is_port_available_sync(port):
            return port
    raise OSError(f'Failed to find a free port in range {lower}-{upper}')
