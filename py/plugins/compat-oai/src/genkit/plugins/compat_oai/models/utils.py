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

import json
from collections.abc import Callable

from genkit.types import (
    Message,
    Part,
    Role,
    TextPart,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)


class DictMessageAdapter:
    """Adapter for dictionary-based chat message objects with OpenAI-compatible fields."""

    def __init__(self, data: dict):
        """Initializes the adapter with a dictionary.

        Args:
            data: Dictionary with keys like 'content', 'tool_calls', and 'role'.
        """
        self._data = data

    @property
    def content(self) -> str | None:
        """Returns the 'content' of the message if available.

        Returns:
            The message content or None.
        """
        return self._data.get('content', None)

    @property
    def tool_calls(self) -> list | None:
        """Returns the 'tool_calls' list if present in the message.

        Returns:
            A list of tool calls or None.
        """
        return self._data.get('tool_calls', None)

    @property
    def role(self) -> str | None:
        """Returns the role of the message.

        Returns:
            The role string or None.
        """
        return self._data.get('role', None)


class MessageAdapter:
    """Adapter for object-based chat message objects with OpenAI-compatible fields."""

    def __init__(self, data: object):
        """Initializes the adapter with an object.

        Args:
            data: An object expected to have attributes 'content', 'tool_calls', and 'role'.
        """
        self._data = data

    @property
    def content(self) -> str | None:
        """Returns the 'content' attribute of the message if available.

        Returns:
            The message content or None.
        """
        return getattr(self._data, 'content', None)

    @property
    def tool_calls(self) -> list | None:
        """Returns the 'tool_calls' attribute of the message if available.

        Returns:
            A list of tool calls or None.
        """
        return getattr(self._data, 'tool_calls', None)

    @property
    def role(self) -> str | None:
        """Returns the 'role' attribute of the message if available.

        Returns:
            The role string or None.
        """
        return getattr(self._data, 'role', None)


ChatCompletionMessageAdapter = DictMessageAdapter | MessageAdapter


class MessageConverter:
    """Converts between internal `Message` objects and OpenAI-compatible chat message dicts."""

    _openai_role_map = {Role.MODEL: 'assistant'}
    _genkit_role_map = {'assistant': Role.MODEL}

    @classmethod
    def to_openai(cls, message: Message) -> list[dict]:
        """Converts an internal `Message` object to OpenAI-compatible chat messages.

        Args:
            message: The internal `Message` instance.

        Returns:
            A list of OpenAI-compatible message dictionaries.
        """
        text_parts = []
        tool_calls = []
        tool_messages = []

        for part in message.content:
            root: Part = part.root

            if isinstance(root, TextPart):
                text_parts.append(root.text)

            elif isinstance(root, ToolRequestPart):
                tool_calls.append({
                    'id': root.tool_request.ref,
                    'type': 'function',
                    'function': {
                        'name': root.tool_request.name,
                        'arguments': json.dumps(root.tool_request.input),
                    },
                })

            elif isinstance(root, ToolResponsePart):
                tool_call = root.tool_response
                tool_messages.append({
                    'role': cls._openai_role_map.get(message.role, message.role),
                    'tool_call_id': tool_call.ref,
                    'content': str(tool_call.output),
                })

        result = []

        if text_parts:
            result.append({
                'role': cls._openai_role_map.get(message.role, message.role),
                'content': ''.join(text_parts),
            })

        if tool_calls:
            result.append({
                'role': cls._openai_role_map.get(message.role, message.role),
                'tool_calls': tool_calls,
            })

        result.extend(tool_messages)
        return result

    @classmethod
    def to_genkit(cls, message: ChatCompletionMessageAdapter) -> Message:
        """Converts an OpenAI-style message into a Genkit `Message` object.

        Args:
            message: A ChatCompletionMessageAdapter instance.

        Returns:
            A Genkit `Message` object.

        Raises:
            ValueError: If neither content nor tool_calls are present in the message.
        """
        if message.content:
            content = [cls.text_part_to_genkit(message.content)]
        elif message.tool_calls:
            content = [cls.tool_call_to_genkit(tool_call, args_parser=json.loads) for tool_call in message.tool_calls]
        else:
            raise ValueError('Unable to determine content part')

        role = message.role or Role.MODEL
        return Message(role=cls._genkit_role_map.get(role, role), content=content)

    @classmethod
    def text_part_to_genkit(cls, content: str) -> Part:
        """Converts plain text to a Genkit `Part`.

        Args:
            content: The text content.

        Returns:
            A `Part` instance containing the text.
        """
        return Part(text=content)

    @classmethod
    def tool_call_to_genkit(
        cls, tool_call: object, args_segment: str | None = None, args_parser: Callable[[str], dict] | None = None
    ) -> Part:
        """Converts a tool call into a Genkit `Part`.

        Args:
            tool_call: The tool call object containing function info.
            args_segment: Optional pre-parsed arguments string.
            args_parser: Optional parser to deserialize arguments.

        Returns:
            A `Part` instance containing a `ToolRequest`.
        """
        args_segment = args_segment if args_segment is not None else tool_call.function.arguments
        args_segment = args_parser(args_segment) if args_parser else args_segment

        return Part(
            tool_request=ToolRequest(
                ref=tool_call.id,
                name=tool_call.function.name,
                input=args_segment,
            )
        )
