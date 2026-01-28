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

"""Session store interface for Genkit."""

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from genkit.types import Message


class SessionData(TypedDict, total=False):
    """Data stored in a session.

    Attributes:
        id: Unique session identifier (required).
        state: Custom state data stored with the session.
        threads: Message history per thread (thread_name -> messages).
        messages: Legacy message field (maps to 'main' thread for backward compat).
        created_at: Timestamp when session was created.
        updated_at: Timestamp when session was last updated.
    """

    id: str  # Required
    state: dict[str, Any] | None
    threads: dict[str, list[Message]] | None
    messages: list[Message] | None  # Legacy, maps to 'main' thread
    created_at: float | None
    updated_at: float | None


# Default thread name for conversations
MAIN_THREAD = 'main'


class SessionStore(ABC):
    """Abstract base class for session stores.

    **Overview:**

    The `SessionStore` interface defines the contract for persisting session data.
    Implementations of this class can store session state, messages, and metadata
    in various backends (e.g. database, Redis, file system).

    **Key Operations:**

    *   `get`: Retrieve a session by its unique ID.
    *   `save`: Persist a session (create or update).
    *   `delete`: Remove a session from the store.

    **Examples:**

    ```python
    class MyRedisStore(SessionStore):
        def __init__(self, redis_client):
            self.client = redis_client

        async def get(self, session_id: str) -> SessionData | None:
            data = await self.client.get(f'session:{session_id}')
            return json.loads(data) if data else None

        async def save(self, session_id: str, session_data: SessionData) -> None:
            await self.client.set(f'session:{session_id}', json.dumps(session_data))

        async def delete(self, session_id: str) -> None:
            await self.client.delete(f'session:{session_id}')
    ```
    """

    @abstractmethod
    async def get(self, session_id: str) -> SessionData | None:
        """Retrieves a session by ID.

        Args:
            session_id: The ID of the session to retrieve.

        Returns:
            The session data if found, None otherwise.
        """
        ...

    @abstractmethod
    async def save(self, session_id: str, session_data: SessionData) -> None:
        """Saves a session.

        Args:
            session_id: The ID of the session to save.
            session_data: The session data to save.
        """
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Deletes a session by ID.

        Args:
            session_id: The ID of the session to delete.
        """
        ...
