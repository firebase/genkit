# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0

"""Translation of Genkit tools and their results into MCP shapes."""

import json
import re
from typing import Any

import structlog
from mcp.types import (
    AudioContent,
    BlobResourceContents,
    CallToolResult,
    ContentBlock,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

from genkit import MultipartToolResponse, Part
from genkit.plugin_api import Action

logger = structlog.get_logger(__name__)

_DATA_URL = re.compile(r'^data:(?P<mime>[^;,]+);base64,(?P<data>.*)$', re.DOTALL)

ORIGINAL_OUTPUT_SCHEMA_KEY = 'originalOutputSchema'
"""Where a ``tool.v2`` action keeps the schema a model sees, before the envelope."""

EMPTY_OBJECT_SCHEMA: dict[str, Any] = {'type': 'object', 'properties': {}}
"""What a no-arg tool advertises, since MCP arguments are always an object."""


def tool_to_mcp(action: Action) -> Tool | None:
    """Describe one Genkit tool action as an MCP tool.

    Args:
        action: A registered ``tool.v2`` action.

    Returns:
        The MCP tool description, or ``None`` when the action's input is not an
        object, which MCP cannot express.
    """
    input_schema = _object_schema(dict(action.input_schema or {}))
    if input_schema is None:
        logger.warning(
            'skipping a tool whose input is not an object, which MCP arguments cannot express',
            tool=action.name,
            input_type=(action.input_schema or {}).get('type'),
        )
        return None

    return Tool(
        name=action.name,
        description=action.description,
        inputSchema=input_schema,
        outputSchema=_output_schema(action),
        _meta=_tool_meta(action),  # ty: ignore[unknown-argument]
    )


def multipart_to_call_result(response: MultipartToolResponse, tool_name: str) -> CallToolResult:
    """Convert what a Genkit tool returned into an MCP call result.

    MCP has one text channel, and clients join every text block into the
    output. A text part is therefore sent only when that cannot change the
    output a client reads back: when there is no output, or when the output is
    an object carried as ``structuredContent``. Otherwise it is dropped with a
    warning.

    Args:
        response: The envelope a ``tool.v2`` action returned.
        tool_name: Name of the tool, used to mint a URI for binary content that
            has no URI of its own.

    Returns:
        The result to send back over MCP.
    """
    metadata = dict(response.metadata) if response.metadata else {}
    if metadata.get('isError') is True:
        return error_result(_error_text(response.output), meta=_without_error_flag(metadata))

    output = response.output
    structured = _as_object(output) if isinstance(output, dict) else None
    content: list[ContentBlock] = []
    if output is not None:
        content.append(TextContent(type='text', text=_output_text(output)))
    for index, part in enumerate(response.content or []):
        if part.text is not None and output is not None and structured is None:
            logger.warning('dropping a text part that would change the text output', tool=tool_name, index=index)
            continue
        block = _part_to_block(part, tool_name, index)
        if block is not None:
            content.append(block)

    return CallToolResult(
        content=content,
        structuredContent=structured,
        _meta=metadata or None,  # ty: ignore[unknown-argument]
    )


def error_result(message: str, meta: dict[str, Any] | None = None) -> CallToolResult:
    """Build an MCP error result carrying one message.

    Args:
        message: What the model reads. Never a trace id or a stack trace.
        meta: Optional ``_meta`` to carry alongside.

    Returns:
        A result the client folds into an ``error`` output.
    """
    return CallToolResult(
        content=[TextContent(type='text', text=message)],
        isError=True,
        _meta=meta or None,  # ty: ignore[unknown-argument]
    )


def _as_object(value: object) -> dict[str, Any]:
    """Read a metadata value that should be a nested object, or nothing."""
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _object_schema(schema: dict[str, Any]) -> dict[str, Any] | None:
    """Return the schema as an object schema MCP arguments can use, or ``None``.

    pydantic describes a model that refers to itself as a top-level ``$ref``
    into ``$defs``, so that reference is followed first.
    """
    if not schema:
        return dict(EMPTY_OBJECT_SCHEMA)
    ref = schema.get('$ref')
    if isinstance(ref, str) and ref.startswith('#/$defs/'):
        defs = _as_object(schema.get('$defs'))
        target = _as_object(defs.get(ref.removeprefix('#/$defs/')))
        rest = {key: value for key, value in schema.items() if key != '$ref'}
        schema = {**rest, **target}
    if schema.get('type') == 'object':
        return schema
    if 'type' not in schema and isinstance(schema.get('properties'), dict):
        return {**schema, 'type': 'object'}
    return None


def _output_schema(action: Action) -> dict[str, Any] | None:
    """Read the model-facing output schema, kept only when MCP can carry it.

    The SDK rejects any unstructured result for a tool that declares an output
    schema, and ``structuredContent`` is an object, so a non-object schema is
    dropped rather than advertised.
    """
    original = _as_object(action.metadata.get(ORIGINAL_OUTPUT_SCHEMA_KEY))
    return original if original.get('type') == 'object' else None


def _tool_meta(action: Action) -> dict[str, Any] | None:
    """Read the MCP ``_meta`` a re-exported client tool carries from its origin."""
    meta = _as_object(_as_object(action.metadata.get('mcp')).get('_meta'))
    return meta or None


def _without_error_flag(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Drop the flag the client adds on the way in, since ``isError`` already carries it."""
    rest = {key: value for key, value in metadata.items() if key != 'isError'}
    return rest or None


def _error_text(output: object) -> str:
    """Read the message out of the ``{'error': text}`` shape the client produces."""
    error = _as_object(output).get('error')
    return error if isinstance(error, str) else _output_text(output)


def _output_text(output: object) -> str:
    """Render tool output as the text half of a result.

    A string travels as itself. Everything else is JSON, which the client parses
    back only when it begins with ``{`` or ``[``, so scalars return as strings.
    """
    if isinstance(output, str):
        return output
    return json.dumps(output)


def _part_to_block(part: Part, tool_name: str, index: int) -> ContentBlock | None:
    """Convert one Genkit content part into an MCP content block."""
    if part.text is not None:
        return TextContent(type='text', text=part.text)

    if part.media is not None:
        url = part.media.url
        match = _DATA_URL.match(url)
        if match is None:
            uri = _absolute_url(url, tool_name, index)
            if uri is None:
                return None
            return ResourceLink(type='resource_link', uri=uri, name=url, mimeType=part.media.content_type)
        mime_type = match.group('mime')
        data = match.group('data')
        if mime_type.startswith('image/'):
            return ImageContent(type='image', mimeType=mime_type, data=data)
        if mime_type.startswith('audio/'):
            return AudioContent(type='audio', mimeType=mime_type, data=data)
        return _blob_block(tool_name, index, mime_type, data)

    if part.resource is not None:
        url = str(part.resource.uri)
        uri = _absolute_url(url, tool_name, index)
        if uri is None:
            return None
        return ResourceLink(type='resource_link', uri=uri, name=url)

    logger.warning('dropping a tool content part MCP has no block for', tool=tool_name, index=index)
    return None


def _absolute_url(url: str, tool_name: str, index: int) -> AnyUrl | None:
    """Parse a URL a resource link can carry, or warn and return ``None``."""
    try:
        return AnyUrl(url)
    except ValueError:
        logger.warning('dropping a tool content part whose URL is not absolute', tool=tool_name, index=index)
        return None


def _blob_block(tool_name: str, index: int, mime_type: str, data: str) -> ContentBlock:
    """Wrap binary content MCP has no dedicated block for, minting the URI the type requires."""
    return EmbeddedResource(
        type='resource',
        resource=BlobResourceContents(
            uri=AnyUrl(f'genkit://tool/{tool_name}/content/{index}'),
            mimeType=mime_type,
            blob=data,
        ),
    )
