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

"""Tool utilities for MCP plugin.

This module contains helper functions for converting between MCP tools
and Genkit actions, processing tool results, and registering tools.
"""

import json
from typing import Any, cast

import structlog

from mcp.types import (
    AudioContent,
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
    TextContent,
)

logger = structlog.get_logger(__name__)


def to_text(content: list[object]) -> str:
    """Extract text from MCP CallToolResult content.

    Args:
        content: List of content parts from CallToolResult (dict or Pydantic objects)

    Returns:
        Concatenated text from all text parts
    """
    text_parts: list[str] = []
    for part in content:
        if isinstance(part, dict):
            part_dict = cast(dict[str, Any], part)
            text_parts.append(str(part_dict.get('text', '')))
        elif hasattr(part, 'text'):
            text_parts.append(str(getattr(part, 'text', '')))
    return ''.join(text_parts)


def process_result(result: CallToolResult) -> object:
    """Process MCP CallToolResult and extract/parse content.

    Handles different result types:
    - Error results return error dict
    - Text-only results attempt JSON parsing
    - Single content results return the content directly
    - Otherwise returns the full result

    Args:
        result: The CallToolResult from MCP server

    Returns:
        Processed result (parsed JSON, text, or raw content)

    Raises:
        RuntimeError: If the tool execution failed (isError=True)
    """
    if result.isError:
        return {'error': to_text(list(result.content))}

    # Check if all content parts are text
    if all(hasattr(c, 'text') and c.text for c in result.content):
        text = to_text(list(result.content))
        # Try to parse as JSON if it looks like JSON
        text_stripped = text.strip()
        if text_stripped.startswith('{') or text_stripped.startswith('['):
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError):
                return text
        return text

    # Single content item
    if len(result.content) == 1:
        return result.content[0]

    # Return full result for complex cases
    return result


def process_tool_result(result: CallToolResult) -> object:
    """Process MCP CallToolResult and extract content.

    This is an alias for process_result() for backwards compatibility.

    Args:
        result: The CallToolResult from MCP server

    Returns:
        Extracted text content from the result

    Raises:
        RuntimeError: If the tool execution failed
    """
    return process_result(result)


def convert_tool_schema(mcp_schema: dict[str, object]) -> dict[str, object]:
    """Convert MCP tool input schema (JSONSchema7) to Genkit format.

    Args:
        mcp_schema: MCP tool input schema

    Returns:
        Genkit-compatible JSON schema

    Note:
        Currently returns the schema as-is since both use JSON Schema.
        Future enhancements may add validation or transformation.
    """
    # MCP and Genkit both use JSON Schema, so minimal conversion needed
    return mcp_schema


def to_mcp_tool_result(
    result: object,
) -> list[TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource]:
    """Convert tool execution result to MCP CallToolResult content.

    Args:
        result: The result from tool execution (can be string, dict, or other).

    Returns:
        List of MCP content items.
    """
    if isinstance(result, str):
        return [TextContent(type='text', text=result)]
    elif isinstance(result, dict):
        result_dict = cast(dict[str, Any], result)
        # If it's already in MCP format, return as-is
        if 'type' in result_dict and 'text' in result_dict:
            return [TextContent(type='text', text=str(result_dict['text']))]
        # Otherwise, serialize to JSON
        return [TextContent(type='text', text=json.dumps(result_dict))]
    else:
        # Convert to string for other types
        return [TextContent(type='text', text=str(result))]
