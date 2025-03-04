# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
from collections.abc import Callable
from typing import Any

from genkit.ai.formats import FormatDef, Formatter
from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    MessageWrapper,
)
from genkit.core.codec import dump_dict
from genkit.core.registry import Action, ActionKind, Registry
from genkit.core.typing import (
    GenerateActionOptions,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Metadata,
    OutputConfig,
    Part,
    Role,
    TextPart,
    ToolDefinition,
    ToolResponse1,
    ToolResponsePart,
)

logger = logging.getLogger(__name__)

StreamingCallback = Callable[[GenerateResponseChunkWrapper], None]

DEFAULT_MAX_TURNS = 5


async def generate_action(
    registry: Registry,
    raw_request: GenerateActionOptions,
    on_chunk: StreamingCallback | None = None,
    message_index: int = 0,
    current_turn: int = 0,
) -> GenerateResponseWrapper:
    # TODO: middleware

    model, tools, format_def = resolve_parameters(registry, raw_request)

    raw_request, formatter = apply_format(raw_request, format_def)

    assert_valid_tool_names(tools)

    # TODO: interrupts

    request = await action_to_generate_request(raw_request, tools, model)

    prev_chunks: list[GenerateResponseChunk] = []

    chunk_role: Role = Role.MODEL

    def make_chunk(
        role: Role, chunk: GenerateResponseChunk
    ) -> GenerateResponseChunk:
        """Convenience method to create a full chunk from role and data, append
        the chunk to the previousChunks array, and increment the message index
        as needed"""
        nonlocal chunk_role, message_index

        if role != chunk_role and len(prev_chunks) > 0:
            message_index += 1

        chunk_role = role

        prev_to_send = copy.copy(prev_chunks)
        prev_chunks.append(chunk)

        def chunk_parser(chunk: GenerateResponseChunkWrapper):
            """Parse a chunk using the current formatter."""
            return formatter.parse_chunk(chunk)

        return GenerateResponseChunkWrapper(
            chunk,
            index=message_index,
            previous_chunks=prev_to_send,
            chunk_parser=chunk_parser if formatter else None,
        )

    def wrap_chunks(chunk):
        """Wrap and process a model response chunk.

        This function prepares model response chunks for the stream callback.

        Args:
            chunk: The original model response chunk.

        Returns:
            The result of passing the processed chunk to the callback.
        """
        return on_chunk(make_chunk(Role.MODEL, chunk))

    model_response = (
        await model.arun(
            input=request, on_chunk=wrap_chunks if on_chunk else None
        )
    ).response

    def message_parser(msg: MessageWrapper):
        """Parse a message using the current formatter.

        Args:
            msg: The message to parse.

        Returns:
            The parsed message content.
        """
        return formatter.parse_message(msg)

    response = GenerateResponseWrapper(
        model_response,
        request,
        message_parser=message_parser if formatter else None,
    )

    response.assert_valid()
    generated_msg = response.message

    tool_requests = [x for x in response.message.content if x.root.tool_request]

    if raw_request.return_tool_requests or len(tool_requests) == 0:
        if len(tool_requests) == 0:
            response.assert_valid_schema()
        return response

    max_iters = (
        raw_request.max_turns if raw_request.max_turns else DEFAULT_MAX_TURNS
    )

    if current_turn + 1 > max_iters:
        raise GenerationResponseError(
            response=response,
            message=f'Exceeded maximum tool call iterations ({max_iters})',
            status='ABORTED',
            details={'request': request},
        )

    (
        revised_model_msg,
        tool_msg,
        transfer_preamble,
    ) = await resolve_tool_requests(registry, raw_request, generated_msg)

    # if an interrupt message is returned, stop the tool loop and return a response
    if revised_model_msg:
        interrupted_resp = GenerateResponseWrapper(
            response,
            request,
            message_parser=message_parser if formatter else None,
        )
        interrupted_resp.finish_reason = 'interrupted'
        interrupted_resp.finish_message = (
            'One or more tool calls resulted in interrupts.'
        )
        interrupted_resp.message = revised_model_msg
        return interrupted_resp

    # if the loop will continue, stream out the tool response message...
    if on_chunk:
        on_chunk(
            make_chunk(
                'tool',
                GenerateResponseChunk(
                    role=tool_msg.role, content=tool_msg.content
                ),
            )
        )

    next_request = copy.copy(raw_request)
    nextMessages = copy.copy(raw_request.messages)
    nextMessages.append(generated_msg)
    nextMessages.append(tool_msg)
    next_request.messages = nextMessages
    next_request = apply_transfer_preamble(next_request, transfer_preamble)

    # then recursively call for another loop
    return await generate_action(
        registry,
        raw_request=next_request,
        # middleware: middleware,
        current_turn=current_turn + 1,
        message_index=message_index + 1,
        on_chunk=on_chunk,
    )


def apply_format(
    raw_request: GenerateActionOptions, format_def: FormatDef | None
) -> tuple[GenerateActionOptions, Formatter | None]:
    """Apply the format (if set) to the request."""
    if not format_def:
        return raw_request, None

    out_request = copy.deepcopy(raw_request)

    formatter = format_def(
        raw_request.output.json_schema if raw_request.output else None
    )

    instructions = resolve_instructions(
        formatter,
        raw_request.output.instructions if raw_request.output else None,
    )

    if (
        format_def.config.default_instructions != False
        or raw_request.output.instructions
        if raw_request.output
        else False
    ):
        out_request.messages = inject_instructions(
            out_request.messages, instructions
        )

    if format_def.config.constrained is not None:
        out_request.output.constrained = format_def.config.constrained
    if raw_request.output.constrained is not None:
        out_request.output.constrained = raw_request.output.constrained

    if format_def.config.content_type is not None:
        out_request.output.content_type = format_def.config.content_type
    if format_def.config.format is not None:
        out_request.output.format = format_def.config.format

    return (out_request, formatter)


def inject_instructions(
    messages: list[Message], instructions: str
) -> list[Message]:
    """
    Injects instructions into a list of messages.

    Args:
        messages: A list of MessageData objects.
        instructions: The instructions to inject, or False or None to skip injection.

    Returns:
        A new list of MessageData objects with the instructions injected,
        or the original list if injection was skipped.
    """
    if not instructions:
        return messages

    # bail out if a non-pending output part is already present
    if any(
        any(
            part.root.metadata
            and part.root.metadata['purpose'] == 'output'
            and not part.root.metadata['pending']
            for part in message.content
        )
        for message in messages
    ):
        return messages

    new_part = Part(
        TextPart(text=instructions, metadata=Metadata({'purpose': 'output'}))
    )

    # find the system message or the last user message
    target_index = next(
        (i for i, message in enumerate(messages) if message.role == 'system'),
        -1,  # Default to -1 if not found
    )
    if target_index < 0:
        target_index = next(
            (
                i
                for i, message in reversed(list(enumerate(messages)))
                if message.role == 'user'
            ),
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
        (
            i
            for i, part in enumerate(m.content)
            if part.root.metadata
            and part.root.metadata['purpose'] == 'output'
            and part.root.metadata['pending']
        ),
        -1,  # Default to -1 if not found
    )
    if part_index >= 0:
        m.content[part_index] = new_part
    else:
        m.content.append(new_part)

    out_messages = messages[:]  # Create a copy of the messages list
    out_messages[target_index] = m

    return out_messages


def resolve_instructions(
    formatter: Formatter, instructions_opt: bool | str | None
):
    """Resolve instructions based on formatter and instruction options.

    Args:
        formatter: The formatter to use for resolving instructions.
        instructions_opt: The instruction options: True/False, a string, or None.

    Returns:
        The resolved instructions or None if no instructions should be used.
    """
    if isinstance(instructions_opt, str):
        # user provided instructions
        return instructions_opt
    if instructions_opt == False:
        # user says no instructions
        return None
    if not formatter:
        return None
    return formatter.instructions


def apply_transfer_preamble(
    next_request: GenerateActionOptions, preamble: GenerateActionOptions
):
    """Apply transfer preamble to the next request.

    Copies relevant properties from the preamble request to the next request.

    Args:
        next_request: The request to apply the preamble to.
        preamble: The preamble containing properties to transfer.

    Returns:
        The updated request with preamble properties applied.
    """
    # TODO: implement me
    return next_request


def assert_valid_tool_names(raw_request: GenerateActionOptions):
    """Assert that tool names in the request are valid.

    Args:
        raw_request: The generation request to validate.

    Raises:
        ValueError: If any tool names are invalid.
    """
    # TODO: implement me
    pass


def resolve_parameters(
    registry: Registry, request: GenerateActionOptions
) -> tuple[Action, list[Action], FormatDef | None]:
    model = (
        request.model if request.model is not None else registry.default_model
    )
    if not model:
        raise Exception('No model configured.')

    model_action = registry.lookup_action(ActionKind.MODEL, model)
    if model_action is None:
        raise Exception(f'Failed to to resolve model {model}')

    tools: list[Action] = []
    if request.tools:
        for tool_name in request.tools:
            tool_action = registry.lookup_action(ActionKind.TOOL, tool_name)
            if tool_action is None:
                raise Exception(f'Unable to resolve tool {tool_name}')
            tools.append(tool_action)

    format_def: FormatDef | None = None
    if request.output and request.output.format:
        format_def = registry.lookup_value('format', request.output.format)
        if not format_def:
            raise ValueError(
                f'Unable to resolve format {request.output.format}'
            )

    return (model_action, tools, format_def)


async def action_to_generate_request(
    options: GenerateActionOptions, resolvedTools: list[Action], model: Action
) -> GenerateRequest:
    # TODO: add warning when tools are not supported in ModelInfo
    # TODO: add warning when toolChoice is not supported in ModelInfo

    tool_defs = (
        [to_tool_definition(tool) for tool in resolvedTools]
        if resolvedTools
        else []
    )
    return GenerateRequest(
        messages=options.messages,
        config=options.config if options.config is not None else {},
        docs=options.docs,
        tools=tool_defs,
        tool_choice=options.tool_choice,
        output=OutputConfig(
            content_type=options.output.content_type
            if options.output
            else None,
            format=options.output.format if options.output else None,
            schema_=options.output.json_schema if options.output else None,
            constrained=options.output.constrained if options.output else None,
        ),
    )


def to_tool_definition(tool: Action) -> ToolDefinition:
    original_name: str = tool.name
    name: str = original_name

    if '/' in original_name:
        name = original_name[original_name.rfind('/') + 1 :]

    metadata = None
    if original_name != name:
        metadata = {'originalName': original_name}

    tdef = ToolDefinition(
        name=name,
        description=tool.description,
        inputSchema=tool.input_schema,
        outputSchema=tool.output_schema,
        metadata=metadata,
    )
    return tdef


async def resolve_tool_requests(
    registry: Registry, request: GenerateActionOptions, message: Message
) -> tuple[Message, Message, GenerateActionOptions]:
    # TODO: interrupts
    # TODO: prompt transfer

    tool_requests = [
        x.root.tool_request for x in message.content if x.root.tool_request
    ]
    tool_dict: dict[str, Action] = {}
    for tool_name in request.tools:
        tool_dict[tool_name] = resolve_tool(registry, tool_name)

    response_parts: list[ToolResponsePart] = []
    for tool_request in tool_requests:
        if tool_request.name not in tool_dict:
            raise RuntimeError(f'failed {tool_request.name} not found')
        tool = tool_dict[tool_request.name]
        tool_response = (await tool.arun_raw(tool_request.input)).response
        # TODO: figure out why pydantic generates ToolResponse1
        response_parts.append(
            ToolResponsePart(
                toolResponse=ToolResponse1(
                    name=tool_request.name,
                    ref=tool_request.ref,
                    output=dump_dict(tool_response),
                )
            )
        )

    return (None, Message(role=Role.TOOL, content=response_parts), None)


def resolve_tool(registry: Registry, tool_name: str):
    """Resolve a tool by name from the registry.

    Args:
        registry: The registry to resolve the tool from.
        tool_name: The name of the tool to resolve.

    Returns:
        The resolved tool action.

    Raises:
        ValueError: If the tool could not be resolved.
    """
    return registry.lookup_action(kind=ActionKind.TOOL, name=tool_name)


# TODO: extend GenkitError
class GenerationResponseError(Exception):
    # TODO: use status enum
    def __init__(
        self,
        response: GenerateResponse,
        message: str,
        status: str,
        details: dict[str, Any],
    ):
        self.response = response
        self.message = message
        self.status = status
        self.details = details
