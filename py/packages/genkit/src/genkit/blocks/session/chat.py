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

r"""Chat session management for Genkit.

This module provides the Chat class for managing stateful chat conversations.
It provides a simpler interface than directly using sessions, automatically
handling message history and state persistence.

Overview:
    The Chat class wraps a Session and provides `send()` and `send_stream()`
    methods for multi-turn conversations. It tracks message history
    automatically and persists state to the session store.

Key Concepts:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Term                │ Description                                       │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ Chat                │ Wrapper for easy multi-turn conversation          │
    │ Session             │ Underlying state storage with messages & state    │
    │ send()              │ Send a message and get complete response          │
    │ send_stream()       │ Send a message and stream response chunks         │
    │ Preamble            │ System/initial messages prepended to each request │
    │ Thread (future)     │ Named conversation within a session               │
    └─────────────────────┴───────────────────────────────────────────────────┘

Chat vs Session:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Session                       │ Chat                                    │
    ├───────────────────────────────┼─────────────────────────────────────────┤
    │ session.chat(prompt, **kw)    │ chat.send(prompt, **kw)                 │
    │ Manual message management     │ Auto-tracks messages                    │
    │ General purpose               │ Optimized for conversations             │
    │ Multiple threads possible     │ Single conversation focus               │
    └───────────────────────────────┴─────────────────────────────────────────┘

Example:
    Basic conversation:

    ```python
    from genkit.ai import Genkit

    ai = Genkit(model='googleai/gemini-2.0-flash')

    # Create a chat with system prompt
    chat = ai.chat(system='You are a helpful pirate.')

    # Send messages
    response = await chat.send('Hello!')
    print(response.text)  # "Ahoy there, matey!"

    response = await chat.send('Tell me a joke')
    print(response.text)  # "Why did the pirate..."
    ```

    Using an ExecutablePrompt as preamble:

    ```python
    support_agent = ai.define_prompt(
        name='support_agent',
        system='You are a customer support agent for TechCorp.',
        config={'temperature': 0.3},
    )

    chat = ai.chat(support_agent)
    response = await chat.send('My laptop won\\'t turn on')
    ```

    Streaming responses:

    ```python
    chat = ai.chat(system='Be verbose.')

    result = chat.send_stream('Explain quantum computing')
    async for chunk in result.stream:
        print(chunk.text, end='', flush=True)

    final = await result.response
    print(f'\\nTotal tokens: {final.usage}')
    ```

Caveats:
    - Chat manages a single conversation thread
    - All messages are persisted through the underlying session
    - Preamble messages (system prompts) are not stored in history

See Also:
    - JavaScript Chat: js/ai/src/chat.ts
    - Session: genkit/blocks/session/session.py
"""
# pyright: reportImportCycles=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from typing import Any, TypedDict

from genkit.aio import Channel
from genkit.blocks.model import GenerateResponseChunkWrapper, GenerateResponseWrapper
from genkit.types import Message, Part, TextPart

from .store import MAIN_THREAD
from .types import SessionLike


class ChatOptions(TypedDict, total=False):
    """Options for creating a Chat instance (matches JS ChatOptions).

    This combines BaseGenerateOptions fields with ChatOptions-specific fields.

    Attributes:
        system: System prompt for the conversation.
        model: Model to use for generation.
        config: Model configuration options.
        tools: Tools available in this chat.
        tool_choice: Tool selection strategy.
        messages: Initial message history.
        store: Session store for persistence.
        session_id: Custom session ID.
        input: Input for prompt rendering (PromptRenderOptions).
    """

    # From BaseGenerateOptions
    system: str | Part | list[Part] | None
    model: str | None
    config: dict[str, Any] | None
    tools: list[str] | None
    tool_choice: str | None
    messages: list[Message] | None
    # ChatOptions specific
    store: Any | None  # SessionStore
    session_id: str | None
    # PromptRenderOptions
    input: Any | None


# Keys that are Chat-specific and should NOT be passed to ai.generate()
_CHAT_ONLY_KEYS = frozenset({'messages', 'store', 'session_id', 'input'})


class ChatStreamResponse:
    """Response from a streaming chat send.

    This class provides access to both the streaming chunks and the
    complete response, matching the JavaScript GenerateStreamResponse.

    Attributes:
        stream: Async iterable of response chunks.
        response: Awaitable that resolves to the complete response.

    Example:
        ```python
        result = chat.send_stream('Hello!')
        async for chunk in result.stream:
            print(chunk.text, end='')
        final = await result.response
        ```
    """

    def __init__(
        self,
        channel: Channel[GenerateResponseChunkWrapper, GenerateResponseWrapper[Any]],
        response_future: asyncio.Future[GenerateResponseWrapper[Any]],
    ) -> None:
        """Initialize the stream response.

        Args:
            channel: The channel providing response chunks.
            response_future: Future resolving to the complete response.
        """
        self._channel: Channel[GenerateResponseChunkWrapper, GenerateResponseWrapper[Any]] = channel
        self._response_future: asyncio.Future[GenerateResponseWrapper[Any]] = response_future

    @property
    def stream(self) -> AsyncIterable[GenerateResponseChunkWrapper]:
        """Get the async iterable of response chunks."""
        return self._channel

    @property
    def response(self) -> asyncio.Future[GenerateResponseWrapper]:
        """Get the awaitable for the complete response."""
        return self._response_future


def _normalize_prompt_parts(prompt: str | Part | list[Part]) -> list[Part]:
    """Normalize prompt input into a list of Parts."""
    if isinstance(prompt, str):
        # Part is a RootModel, so we pass content via the 'root' parameter.
        return [Part(root=TextPart(text=prompt))]
    if isinstance(prompt, list):
        return list(prompt)
    if isinstance(prompt, Part):  # pyright: ignore[reportUnnecessaryIsInstance]
        return [prompt]
    return []


class Chat:
    """A stateful chat conversation.

    Chat provides a simple interface for multi-turn conversations, automatically
    managing message history and session state. It wraps an underlying Session
    and provides `send()` and `send_stream()` methods.

    Overview:
        Use `ai.chat()` to create a Chat instance. Each call to `send()` or
        `send_stream()` adds the user message and model response to the
        conversation history.

        ┌─────────────────────────────────────────────────────────────────────┐
        │ Chat Methods                                                        │
        ├─────────────────────┬───────────────────────────────────────────────┤
        │ send(message)       │ Send message, return complete response        │
        │ send_stream(msg)    │ Send message, return streaming response       │
        │ messages            │ Property: current conversation history        │
        │ session             │ Property: underlying Session object           │
        └─────────────────────┴───────────────────────────────────────────────┘

    Attributes:
        session: The underlying Session object.
        messages: The current conversation message history.

    Example:
        ```python
        # Create via ai.chat()
        chat = ai.chat(system='You are helpful.')

        # Simple send
        response = await chat.send('Hello!')
        print(response.text)

        # Continue conversation
        response = await chat.send('What did I just say?')
        print(response.text)  # Remembers context

        # Access history
        for msg in chat.messages:
            print(f'{msg.role}: {msg.content}')
        ```

    Caveats:
        - Preamble (system prompt) is not stored in messages property
        - Each send() call persists to the session store
    """

    def __init__(
        self,
        session: SessionLike,
        request_base: dict[str, Any] | None = None,
        *,
        thread: str = MAIN_THREAD,
        messages: list[Message] | None = None,
    ) -> None:
        """Initialize a Chat instance (matches JS Chat constructor).

        In JS, Chat receives:
        - session: Session object
        - requestBase: Promise<BaseGenerateOptions> (pre-rendered options)
        - options: {id, thread, messages}

        Args:
            session: The underlying session for state management.
            request_base: Pre-rendered generation options (system, model, config, etc.).
            thread: Thread name for this conversation (default: 'main').
            messages: Initial messages (from session thread or provided).
        """
        self._session: SessionLike = session
        self._request_base: dict[str, Any] = request_base or {}
        self._thread_name: str = thread

        # Initialize messages: provided messages > session thread messages > empty
        if messages is not None:
            self._messages: list[Message] = list(messages)
        else:
            # Load from session's thread
            self._messages = list(session.get_messages(self._thread_name))

    @property
    def session(self) -> SessionLike:
        """The underlying Session object (readonly, matches JS)."""
        return self._session

    @property
    def session_id(self) -> str:
        """The session ID (matches JS sessionId)."""
        return self._session.id

    @property
    def messages(self) -> list[Message]:
        """The current conversation message history."""
        return self._messages

    async def send(
        self,
        prompt: str | Part | list[Part],
        **kwargs: Any,  # noqa: ANN401 - Forwarding generation arguments.
    ) -> GenerateResponseWrapper:
        """Send a message and get the complete response (matches JS chat.send)."""
        # Append user message to history
        self._messages.append(Message(role='user', content=_normalize_prompt_parts(prompt)))

        # Merge base options and call-specific options
        gen_options = {**self._request_base, **kwargs}
        gen_options['messages'] = self._messages

        # Use session's AI instance to generate response
        response = await self._session._ai.generate(**gen_options)  # pyright: ignore[reportPrivateUsage]

        # Append model response to history
        if response.message is not None:
            self._messages.append(
                Message(
                    role=response.message.role,
                    content=response.message.content,
                    metadata=response.message.metadata,
                )
            )
        self._session.update_messages(self._thread_name, self._messages)
        await self._session.save()

        return response

    def send_stream(
        self,
        prompt: str | Part | list[Part],
        **kwargs: Any,  # noqa: ANN401 - Forwarding generation arguments.
    ) -> ChatStreamResponse:
        """Send a message and stream the response (matches JS chat.sendStream)."""
        # Append user message to history
        self._messages.append(Message(role='user', content=_normalize_prompt_parts(prompt)))

        # Merge base options and call-specific options
        gen_options = {**self._request_base, **kwargs}
        gen_options['messages'] = self._messages

        # Use session's AI instance to generate response (streaming)
        stream, base_response_future = self._session._ai.generate_stream(  # pyright: ignore[reportPrivateUsage]
            **gen_options
        )

        async def _run_stream() -> GenerateResponseWrapper:
            response = await base_response_future
            # Append model response to history
            if response.message is not None:
                self._messages.append(
                    Message(
                        role=response.message.role,
                        content=response.message.content,
                        metadata=response.message.metadata,
                    )
                )
            self._session.update_messages(self._thread_name, self._messages)
            await self._session.save()
            return response

        wrapped_response_future = asyncio.ensure_future(_run_stream())
        return ChatStreamResponse(stream, wrapped_response_future)


def _merge_chat_options(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Merge chat options, filtering out chat-only keys."""
    merged = {**base, **updates}
    for key in _CHAT_ONLY_KEYS:
        merged.pop(key, None)
    return merged
