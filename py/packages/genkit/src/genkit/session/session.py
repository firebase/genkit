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

"""Session implementation matching JavaScript parity.

In JavaScript, `session.chat()` returns a Chat object for multi-turn conversations.
This module implements the same pattern for Python.

Example (matching JS):
    ```python
    session = ai.create_session()

    # Create chats for different threads
    lawyer_chat = session.chat('lawyer', system='Talk like a lawyer')
    pirate_chat = session.chat('pirate', system='Talk like a pirate')

    # Send messages
    await lawyer_chat.send('Tell me a joke')
    await pirate_chat.send('Tell me a joke')
    ```
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

from genkit.types import Message

if TYPE_CHECKING:
    from genkit.ai import Genkit
    from genkit.blocks.prompt import ExecutablePrompt

from .chat import Chat, ChatOptions
from .store import MAIN_THREAD, SessionData, SessionStore


class Session:
    """Represents a stateful session with thread support.

    **Overview:**

    A `Session` maintains the conversation history and state for multi-turn
    interactions. It supports multiple conversation threads within a single
    session, allowing parallel conversations that share the same state.

    This matches the JavaScript Session API where `session.chat()` returns
    a Chat object for multi-turn conversations.

    **Key Concepts:**

    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Term          │ Description                                             │
    ├───────────────┼─────────────────────────────────────────────────────────┤
    │ Session       │ Container for state and multiple conversation threads   │
    │ Thread        │ Named conversation with its own message history         │
    │ MAIN_THREAD   │ Default thread name ('main')                            │
    │ State         │ Custom data shared across all threads                   │
    │ Chat          │ Object for sending messages within a thread             │
    └───────────────┴─────────────────────────────────────────────────────────┘

    **Key Operations:**

    *   `chat()`: Create a Chat object for a thread (returns Chat, matching JS)
    *   `get_messages`: Get messages for a specific thread.
    *   `update_messages`: Update messages for a specific thread.
    *   `update_state`: Modify the custom state associated with the session.
    *   `save`: Persist the session manually (auto-called by Chat.send).

    **Examples:**

    ```python
    # Create a session
    session = ai.create_session(initial_state={'user': 'John'})

    # Get a Chat object (matching JS session.chat())
    chat = session.chat(system='You are helpful.')
    response = await chat.send('Hello!')
    print(response.text)

    # Multiple threads in the same session
    lawyer = session.chat('lawyer', system='Talk like a lawyer')
    pirate = session.chat('pirate', system='Talk like a pirate')
    await lawyer.send('Tell me a joke')
    await pirate.send('Tell me a joke')
    ```
    """

    def __init__(
        self,
        ai: Genkit,
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
            # Load threads, with backward compat for legacy 'messages' field
            self._threads: dict[str, list[Message]] = data.get('threads') or {}
            if not self._threads and data.get('messages'):
                # Migrate legacy messages to main thread
                self._threads[MAIN_THREAD] = data.get('messages') or []
            self._created_at = data.get('created_at') or time.time()
            self._updated_at = data.get('updated_at') or time.time()
        else:
            self._id = id or str(uuid.uuid4())
            self._state = {}
            self._threads = {}
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
        """The main thread message history (for backward compatibility)."""
        return self.get_messages(MAIN_THREAD)

    @property
    def threads(self) -> dict[str, list[Message]]:
        """All thread message histories."""
        return self._threads

    def get_messages(self, thread: str = MAIN_THREAD) -> list[Message]:
        """Get messages for a specific thread.

        Args:
            thread: The thread name (defaults to MAIN_THREAD).

        Returns:
            List of messages for the thread, or empty list if thread doesn't exist.
        """
        return self._threads.get(thread, [])

    def update_messages(self, thread: str, messages: list[Message]) -> None:
        """Update messages for a specific thread.

        Args:
            thread: The thread name.
            messages: The new message list for the thread.
        """
        self._threads[thread] = messages

    async def save(self) -> None:
        """Persist the current session state to the store."""
        self._updated_at = time.time()
        data: SessionData = {
            'id': self._id,
            'state': self._state,
            'threads': self._threads,
            'messages': self._threads.get(MAIN_THREAD),  # Legacy compat
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

    def chat(
        self,
        thread_or_preamble_or_options: str | ExecutablePrompt | ChatOptions | None = None,
        preamble_or_options: ExecutablePrompt | ChatOptions | None = None,
        options: ChatOptions | None = None,
    ) -> Chat:
        """Create a Chat object for multi-turn conversation (matching JS API).

        This method returns a Chat object that can be used to send messages.
        It supports multiple call patterns matching the JavaScript API:

        1. `session.chat()` - basic chat on main thread
        2. `session.chat(options)` - chat with options on main thread
        3. `session.chat(preamble)` - chat with ExecutablePrompt preamble
        4. `session.chat('thread')` - chat on named thread
        5. `session.chat('thread', options)` - named thread with options
        6. `session.chat('thread', preamble)` - named thread with preamble
        7. `session.chat('thread', preamble, options)` - all three

        Args:
            thread_or_preamble_or_options: Thread name (str), ExecutablePrompt,
                or ChatOptions dict.
            preamble_or_options: ExecutablePrompt or ChatOptions (when first
                arg is thread name).
            options: ChatOptions (when first two args are thread and preamble).

        Returns:
            A Chat object for sending messages.

        Example:
            ```python
            # Basic usage
            chat = session.chat({'system': 'You are helpful.'})
            response = await chat.send('Hello!')

            # With thread name
            lawyer = session.chat('lawyer', {'system': 'Talk like a lawyer'})
            pirate = session.chat('pirate', {'system': 'Talk like a pirate'})

            # With ExecutablePrompt
            agent = ai.define_prompt(name='agent', system='...')
            chat = session.chat(agent)
            ```
        """
        from .chat import Chat

        # Resolve arguments (matching JS pattern)
        thread_name = MAIN_THREAD
        chat_options: ChatOptions | None = None

        # Check if first arg is a thread name (string)
        if isinstance(thread_or_preamble_or_options, str):
            thread_name = thread_or_preamble_or_options
            # Second arg could be preamble or options
            if preamble_or_options is not None:
                if self._is_executable_prompt(preamble_or_options):
                    chat_options = options
                else:
                    chat_options = preamble_or_options  # type: ignore[assignment]
        elif thread_or_preamble_or_options is not None:
            # First arg is preamble or options
            if self._is_executable_prompt(thread_or_preamble_or_options):
                chat_options = preamble_or_options  # type: ignore[assignment]
            else:
                chat_options = thread_or_preamble_or_options  # type: ignore[assignment]

        # Build request_base from options (matching JS pattern)
        # In JS, this is done as: requestBase = Promise.resolve(baseOptions)
        request_base: dict[str, Any] = {}
        if chat_options:
            # Copy generate-related options to request_base
            for key in ('system', 'model', 'config', 'tools', 'tool_choice'):
                if key in chat_options:
                    request_base[key] = chat_options[key]

        # TODO: Handle preamble rendering (JS pre-renders preamble here)
        # For now, preamble support is deferred

        # Get messages for this thread
        thread_messages = self.get_messages(thread_name)

        return Chat(
            session=self,
            request_base=request_base if request_base else None,
            thread=thread_name,
            messages=thread_messages if thread_messages else None,
        )

    def _is_executable_prompt(self, obj: Any) -> bool:  # noqa: ANN401
        """Check if an object is an ExecutablePrompt."""
        # Import here to avoid circular imports
        from genkit.blocks.prompt import ExecutablePrompt

        return isinstance(obj, ExecutablePrompt)
