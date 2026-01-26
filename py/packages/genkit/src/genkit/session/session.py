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

"""Session implementation."""

import time
import uuid
from typing import TYPE_CHECKING, Any

from genkit.blocks.model import GenerateResponseWrapper
from genkit.types import Message, Part

if TYPE_CHECKING:
    from genkit.ai import Genkit

from .store import SessionData, SessionStore


class Session:
    """Represents a stateful session.

    **Overview:**

    A `Session` maintains the conversation history and state for a multi-turn
    interaction. It is associated with a `SessionStore` for persistence.
    You generally create or load sessions via `Genkit.create_session` or
    `Genkit.load_session`.

    **Key Operations:**

    *   `chat`: Send a message to the model within this session context.
    *   `update_state`: Modify the custom state associated with the session.
    *   `save`: Persist the session manually (auto-called by `chat`).

    **Examples:**

    ```python
    session = ai.create_session(initial_state={'user': 'John'})
    response = await session.chat('Hello, my name is John.')
    print(response.text)
    # > "Hello John! How can I help you today?"
    ```
    """

    def __init__(
        self,
        ai: 'Genkit',
        store: SessionStore,
        id: str | None = None,
        data: SessionData | None = None,
    ) -> None:
        """Initialize a new session.

        Args:
            ai: The Genkit instance used for generation.
            store: The session store for persistence.
            id: The session ID. If not provided, a new UUID is generated.
            data: Existing session data (if loading).
        """
        self._ai = ai
        self._store = store
        if data:
            self._id = data['id']
            self._state = data.get('state') or {}
            self._messages = data.get('messages') or []
            self._created_at = data.get('created_at') or time.time()
            self._updated_at = data.get('updated_at') or time.time()
        else:
            self._id = id or str(uuid.uuid4())
            self._state = {}
            self._messages = []
            self._created_at = time.time()
            self._updated_at = time.time()

    @property
    def id(self) -> str:
        """The session ID."""
        return self._id

    @property
    def state(self) -> dict[str, Any]:
        """The session state."""
        return self._state

    @property
    def messages(self) -> list[Message]:
        """The session message history."""
        return self._messages

    async def save(self) -> None:
        """Persist the current session state to the store."""
        self._updated_at = time.time()
        data: SessionData = {
            'id': self._id,
            'state': self._state,
            'messages': self._messages,
            'created_at': self._created_at,
            'updated_at': self._updated_at,
        }
        await self._store.save(self._id, data)

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update session state.

        Args:
            updates: Dictionary of state updates to apply.
        """
        self._state.update(updates)

    def add_message(self, message: Message) -> None:
        """Add a message to the session history.

        Args:
            message: The message to add.
        """
        self._messages.append(message)

    async def chat(
        self,
        prompt: str | Part | list[Part] | None = None,
        tool_responses: list[Part] | None = None,
        **kwargs: Any,  # noqa: ANN401 - Forwarding arbitrary generation arguments.
    ) -> GenerateResponseWrapper:
        """Sends a message to the model in the context of this session.

        This method appends the user's prompt (or tool responses) to the session history,
        calls the model, updates the history with the model's response, and saves
        the session.

        Args:
            prompt: The user prompt (string or parts).
            tool_responses: Optional tool responses (if resuming after tool call).
            **kwargs: Additional arguments to pass to `ai.generate()`.

        Returns:
            The model response (GenerateResponseWrapper).

        Examples:
            >>> response = await session.chat('Who are you?')
            >>> print(response.text)
        """
        response = await self._ai.generate(
            prompt=prompt,
            tool_responses=tool_responses,
            messages=self._messages,
            **kwargs,
        )
        self._messages = response.messages
        await self.save()
        return response
