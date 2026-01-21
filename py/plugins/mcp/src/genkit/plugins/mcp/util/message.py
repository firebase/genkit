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

"""
Message utilities for MCP plugin.

This module contains helper functions for converting between MCP message
formats and Genkit message formats.
"""

from typing import Any, Dict

import structlog

from genkit.core.typing import Message
from mcp.types import ImageContent, PromptMessage, TextContent

logger = structlog.get_logger(__name__)

# Role mapping from MCP to Genkit
ROLE_MAP = {
    'user': 'user',
    'assistant': 'model',
}


def from_mcp_prompt_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP PromptMessage to Genkit MessageData format.

    This involves mapping MCP roles (user, assistant) to Genkit roles (user, model)
    and transforming the MCP content part into a Genkit Part.

    Args:
        message: MCP PromptMessage with 'role' and 'content' fields

    Returns:
        Genkit MessageData object with 'role' and 'content' fields
    """
    return {
        'role': ROLE_MAP.get(message.get('role', 'user'), 'user'),
        'content': [from_mcp_part(message.get('content', {}))],
    }


def from_mcp_part(part: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP message content part to Genkit Part.

    Handles different content types:
    - Text parts are directly mapped
    - Image parts are converted to Genkit media parts with data URL
    - Resource parts are mapped to Genkit resource format

    Args:
        part: MCP PromptMessage content part

    Returns:
        Genkit Part object
    """
    part_type = part.get('type', '')

    if part_type == 'text':
        return {'text': part.get('text', '')}

    elif part_type == 'image':
        mime_type = part.get('mimeType', 'image/png')
        data = part.get('data', '')
        return {
            'media': {
                'contentType': mime_type,
                'url': f'data:{mime_type};base64,{data}',
            }
        }

    elif part_type == 'resource':
        return {
            'resource': {
                'uri': str(part.get('uri', '')),
            }
        }

    # Default case for unknown types
    return {}


def _get_part_data(part: Any) -> Dict[str, Any]:
    """Extract data from a Part, handling potential 'root' nesting."""
    if isinstance(part, str):
        return {'text': part}
    part_dict = part if isinstance(part, dict) else part.model_dump()
    if 'root' in part_dict and isinstance(part_dict['root'], dict):
        return part_dict['root']
    return part_dict


def _parse_media_part(media: Dict[str, Any]) -> ImageContent:
    """Extract MIME type and base64 data from a media part."""
    url = media.get('url', '')
    content_type = media.get('contentType', '')

    if not url.startswith('data:'):
        raise ValueError('MCP prompt messages only support base64 data images.')

    # Extract MIME type and base64 data
    try:
        mime_type = content_type or url[url.index(':') + 1 : url.index(';')]
        data = url[url.index(',') + 1 :]
    except ValueError as e:
        raise ValueError(f'Invalid data URL format: {url}') from e

    return ImageContent(type='image', data=data, mimeType=mime_type)


def to_mcp_prompt_message(message: Message) -> PromptMessage:
    """Convert a Genkit Message to an MCP PromptMessage.

    MCP only supports 'user' and 'assistant' roles. Genkit's 'model' role
    is mapped to 'assistant'.

    Args:
        message: The Genkit Message to convert.

    Returns:
        An MCP PromptMessage.

    Raises:
        ValueError: If the message role is not 'user' or 'model'.
        ValueError: If media is not a base64 data URL.
    """
    # Map Genkit roles to MCP roles
    role_map = {'model': 'assistant', 'user': 'user'}

    if message.role not in role_map:
        raise ValueError(
            f"MCP prompt messages do not support role '{message.role}'. Only 'user' and 'model' messages are supported."
        )

    mcp_role = role_map[message.role]

    # First, look for any media content as MCP content is currently single-part
    if message.content:
        for part in message.content:
            data = _get_part_data(part)
            if data.get('media'):
                return PromptMessage(role=mcp_role, content=_parse_media_part(data['media']))

    # If no media, aggregate all text content
    text_content = []
    if message.content:
        for part in message.content:
            data = _get_part_data(part)
            if data.get('text'):
                text_content.append(data['text'])

    return PromptMessage(role=mcp_role, content=TextContent(type='text', text=''.join(text_content)))
