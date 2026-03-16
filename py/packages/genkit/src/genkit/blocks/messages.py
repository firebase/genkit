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

"""Utilities for working with messages."""

from typing import Any

from genkit.core.typing import (
    Message,
    Metadata,
    Part,
    Role,
    TextPart,
)


def _get_metadata_dict(metadata: Metadata | dict[str, Any] | None) -> dict[str, Any]:
    """Safely extracts the dict from a Metadata RootModel or returns the dict directly.

    Args:
        metadata: The metadata, which can be a Metadata RootModel, a dict, or None.

    Returns:
        The underlying dict, or an empty dict if metadata is None.
    """
    if metadata is None:
        return {}
    if isinstance(metadata, Metadata):
        return metadata.root
    return metadata


def _is_output_part(part: Part, require_pending: bool = False, require_non_pending: bool = False) -> bool:
    """Check if a part has output purpose metadata.

    Args:
        part: The part to check.
        require_pending: If True, only match pending output parts.
        require_non_pending: If True, only match non-pending output parts.

    Returns:
        True if the part matches the criteria.
    """
    metadata_dict = _get_metadata_dict(part.root.metadata)
    if metadata_dict.get('purpose') != 'output':
        return False
    if require_pending:
        return metadata_dict.get('pending', False) is True
    if require_non_pending:
        return not metadata_dict.get('pending', False)
    return True


def inject_instructions(messages: list[Message], instructions: str) -> list[Message]:
    """Injects instructions as a new Part into a list of messages.

    This function attempts to add the provided `instructions` string as a new
    text Part with `metadata={'purpose': 'output'}` into the message history.

    Injection Logic:
    - If `instructions` is empty, the original list is returned.
    - If any message already contains a non-pending output Part, the original list is returned.
    - Otherwise, it looks for a target message:
        1. The first message containing a Part marked as pending output.
        2. If none, the first system message.
        3. If none, the last user message.
    - If a target message is found:
        - If the target contains a pending output Part, it's replaced by the new instruction Part.
        - Otherwise, the new instruction Part is appended to the target message's content.
    - A *new* list containing the potentially modified message is returned.

    Args:
        messages: A list of Message objects representing the conversation history.
        instructions: The text instructions to inject. If empty, no injection occurs.

    Returns:
        A new list of Message objects with the instructions injected into the
        appropriate message, or a copy of the original list if no suitable place
        for injection was found or if instructions were empty.
    """
    if not instructions:
        return messages

    # bail out if a non-pending output part is already present
    if any(any(_is_output_part(part, require_non_pending=True) for part in message.content) for message in messages):
        return messages

    new_part = Part(TextPart(text=instructions, metadata=Metadata({'purpose': 'output'})))

    # find first message with purpose=output and pending=True
    target_index = next(
        (
            i
            for i, message in enumerate(messages)
            if any(_is_output_part(part, require_pending=True) for part in message.content)
        ),
        -1,  # Default to -1 if not found
    )
    # find the system message or the last user message
    if target_index < 0:
        target_index = next(
            (i for i, message in enumerate(messages) if message.role == Role.SYSTEM),
            -1,  # Default to -1 if not found
        )
    if target_index < 0:
        target_index = next(
            (i for i, message in reversed(list(enumerate(messages))) if message.role == 'user'),
            -1,  # Default to -1 if not found
        )
    if target_index < 0:
        return messages

    m = Message(
        role=messages[target_index].role,
        # Create a copy of the content
        content=messages[target_index].content[:],
    )

    part_index = next(
        (i for i, part in enumerate(m.content) if _is_output_part(part, require_pending=True)),
        -1,  # Default to -1 if not found
    )
    if part_index >= 0:
        m.content[part_index] = new_part
    else:
        m.content.append(new_part)

    out_messages = messages[:]  # Create a copy of the messages list
    out_messages[target_index] = m

    return out_messages
