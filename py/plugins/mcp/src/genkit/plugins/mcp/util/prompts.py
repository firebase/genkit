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

"""Prompt utilities for MCP plugin.

This module contains helper functions for converting between MCP prompts
and Genkit prompts, including schema and message conversion.
"""

from typing import Any

import structlog

from mcp.types import GetPromptResult

logger = structlog.get_logger(__name__)


def to_schema(arguments: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Convert MCP prompt arguments to JSON schema format.

    Args:
        arguments: List of MCP prompt argument definitions with 'name',
                  'description', and 'required' fields

    Returns:
        JSON schema representing the prompt arguments
    """
    if not arguments:
        return {}

    schema: dict[str, Any] = {'type': 'object', 'properties': {}, 'required': []}

    for arg in arguments:
        arg_name = arg.get('name', '')
        schema['properties'][arg_name] = {
            'type': 'string',
            'description': arg.get('description', ''),
        }
        if arg.get('required', False):
            schema['required'].append(arg_name)

    return schema


def convert_prompt_arguments_to_schema(arguments: list[Any]) -> dict[str, Any]:
    """Convert MCP prompt arguments to JSON schema format.

    This is an alias for to_schema() for backwards compatibility.

    Args:
        arguments: List of MCP prompt argument definitions

    Returns:
        JSON schema representing the prompt arguments
    """
    return to_schema(arguments)


def convert_mcp_prompt_messages(prompt_result: GetPromptResult) -> list[dict[str, Any]]:
    """Convert MCP prompt messages to Genkit message format.

    Args:
        prompt_result: The GetPromptResult from MCP server containing messages

    Returns:
        List of Genkit-formatted messages
    """
    from .message import from_mcp_prompt_message  # noqa: PLC0415

    if not hasattr(prompt_result, 'messages') or not prompt_result.messages:
        return []

    return [from_mcp_prompt_message(msg) for msg in prompt_result.messages]


def to_mcp_prompt_arguments(input_schema: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    """Convert Genkit input schema to MCP prompt arguments.

    MCP prompts only support string arguments. This function validates that
    all properties in the schema are strings.

    Args:
        input_schema: The Genkit input JSON schema.

    Returns:
        List of MCP prompt argument definitions, or None if no schema.

    Raises:
        ValueError: If the schema is not an object type.
        ValueError: If any property is not a string type.
    """
    if not input_schema:
        return None

    # Handle empty schemas - if no properties, return None instead of raising
    properties = input_schema.get('properties')
    if not properties:
        # Empty schema is valid - prompt has no parameters
        return None

    args: list[dict[str, Any]] = []
    required = input_schema.get('required', [])

    for name, prop in properties.items():
        prop_type = prop.get('type')

        # Check if type is string or includes string (for union types)
        is_string = prop_type == 'string' or (isinstance(prop_type, list) and 'string' in prop_type)

        if not is_string:
            raise ValueError(
                f"MCP prompts may only take string arguments, but property '{name}' has type '{prop_type}'."
            )

        args.append({
            'name': name,
            'description': prop.get('description'),
            'required': name in required,
        })

    return args
