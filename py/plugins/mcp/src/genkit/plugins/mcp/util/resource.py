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
Resource utilities for MCP plugin.

This module contains helper functions for handling MCP resources,
including reading and converting resource content.
"""

from typing import Any, Dict

import structlog

from genkit.core.typing import Part
from mcp.types import BlobResourceContents, ReadResourceResult, Resource, TextResourceContents

logger = structlog.get_logger(__name__)


def from_mcp_resource_part(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP resource content to Genkit Part format.

    Handles different content types:
    - Text content is mapped to text part
    - Blob content is mapped to media part with base64 data

    Args:
        content: MCP resource content part

    Returns:
        Genkit Part representation
    """
    content_type = content.get('type', '')

    if content_type == 'text':
        return {'text': content.get('text', '')}

    elif content_type == 'blob':
        mime_type = content.get('mimeType', 'application/octet-stream')
        blob_data = content.get('blob', '')
        return {
            'media': {
                'contentType': mime_type,
                'url': f'data:{mime_type};base64,{blob_data}',
            }
        }

    # Default case
    return {'text': str(content)}


def process_resource_content(resource_result: ReadResourceResult) -> Any:
    """
    Process MCP ReadResourceResult and extract content.

    Args:
        resource_result: The ReadResourceResult from MCP server

    Returns:
        Extracted resource content as Genkit Parts
    """
    if not hasattr(resource_result, 'contents') or not resource_result.contents:
        return []

    return [from_mcp_resource_part(content) for content in resource_result.contents]


def convert_resource_to_genkit_part(resource: Resource) -> dict[str, Any]:
    """
    Convert MCP resource to Genkit Part format.

    Args:
        resource: MCP resource object

    Returns:
        Genkit Part representation with resource URI
    """
    return {
        'resource': {
            'uri': resource.uri,
            'name': resource.name,
            'description': resource.description if hasattr(resource, 'description') else None,
        }
    }


def to_mcp_resource_contents(uri: str, parts: list[Part]) -> list[TextResourceContents | BlobResourceContents]:
    """Convert Genkit Parts to MCP resource contents.

    Args:
        uri: The URI of the resource.
        parts: List of Genkit Parts to convert.

    Returns:
        List of MCP resource contents (text or blob).

    Raises:
        ValueError: If media is not a base64 data URL.
        ValueError: If part type is not supported.
    """
    contents: list[TextResourceContents | BlobResourceContents] = []

    for part in parts:
        if isinstance(part, dict):
            # Handle media/image content
            if 'media' in part:
                media = part['media']
                url = media.get('url', '')
                content_type = media.get('contentType', '')

                if not url.startswith('data:'):
                    raise ValueError('MCP resource messages only support base64 data images.')

                # Extract MIME type and base64 data
                try:
                    mime_type = content_type or url[url.index(':') + 1 : url.index(';')]
                    blob_data = url[url.index(',') + 1 :]
                except ValueError as e:
                    raise ValueError(f'Invalid data URL format: {url}') from e

                contents.append(BlobResourceContents(uri=uri, mimeType=mime_type, blob=blob_data))

            # Handle text content
            elif 'text' in part:
                contents.append(TextResourceContents(uri=uri, text=part['text']))
            else:
                raise ValueError(
                    f'MCP resource messages only support media and text parts. '
                    f'Unsupported part type: {list(part.keys())}'
                )
        elif isinstance(part, str):
            contents.append(TextResourceContents(uri=uri, text=part))

    return contents
