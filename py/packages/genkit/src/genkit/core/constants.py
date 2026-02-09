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

"""Module containing various core constants.

This module defines version constants and provides functions for managing the
``x-goog-api-client`` header used for API attribution.

The client header follows the JS SDK pattern:
  - ``GENKIT_CLIENT_HEADER`` is the base header (e.g., ``genkit-python/0.3.2``).
  - ``set_client_header()`` appends user-provided attribution.
  - ``get_client_header()`` returns the full header string.
"""

import threading

# The version of Genkit sent over HTTP in the headers.
DEFAULT_GENKIT_VERSION = '0.3.2'

# TODO(#4349): make this dynamic
GENKIT_VERSION = DEFAULT_GENKIT_VERSION

GENKIT_CLIENT_HEADER = f'genkit-python/{DEFAULT_GENKIT_VERSION}'

# Module-level state for additional client header attribution.
# Protected by a lock for thread safety since the reflection server
# runs in a separate thread.
_client_header_lock = threading.Lock()
_additional_client_header: str | None = None


def get_client_header() -> str:
    """Return the full client header including any user-provided attribution.

    The returned value is ``GENKIT_CLIENT_HEADER`` optionally followed by the
    string set via :func:`set_client_header`, separated by a space. This
    mirrors the JS SDK's ``getClientHeader()`` behaviour.

    Returns:
        The full ``x-goog-api-client`` header value.
    """
    with _client_header_lock:
        if _additional_client_header:
            return f'{GENKIT_CLIENT_HEADER} {_additional_client_header}'
        return GENKIT_CLIENT_HEADER


def set_client_header(header: str | None) -> None:
    """Set or reset additional attribution for the ``x-goog-api-client`` header.

    Passing a string appends it to the base header. Passing ``None`` removes
    any additional attribution. This is typically called by the ``Genkit``
    constructor, mirroring the JS SDK's ``setClientHeader()``.

    Args:
        header: Additional attribution string or ``None`` to reset.
    """
    global _additional_client_header  # noqa: PLW0603
    with _client_header_lock:
        _additional_client_header = header
