# Copyright 2026 Google LLC
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

"""In-memory session store implementation."""

from genkit.core._compat import override

from .store import SessionData, SessionStore


class InMemorySessionStore(SessionStore):
    """Simple in-memory session store for testing and development.

    **Overview:**

    This implementation stores sessions in a Python dictionary. It is not persistent
    across process restarts and is intended for development, testing, or
    ephemeral use cases.
    """

    def __init__(self, data: dict[str, SessionData] | None = None) -> None:
        """Initialize the in-memory store.

        Args:
            data: Optional initial data to populate the store with.
        """
        self._data: dict[str, SessionData] = data or {}

    @override
    async def get(self, session_id: str) -> SessionData | None:
        """Retrieve a session by ID."""
        return self._data.get(session_id)

    @override
    async def save(self, session_id: str, session_data: SessionData) -> None:
        """Save a session."""
        self._data[session_id] = session_data

    @override
    async def delete(self, session_id: str) -> None:
        """Delete a session by ID."""
        if session_id in self._data:
            del self._data[session_id]
