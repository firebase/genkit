# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
from typing import Any
from collections.abc import Callable
from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
)
from genkit.core.codec import dump_dict
from genkit.core.registry import Action, ActionKind, Registry
from genkit.core.typing import (
    GenerateActionOptions,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    OutputConfig,
    Role,
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
    # TODO: formats
    # TODO: middleware

    model, tools = resolve_parameters(registry, raw_request)

    assert_valid_tool_names(tools)

    # TODO: interrupts

    request = await action_to_generate_request(raw_request, tools, model)

    prev_chunks: list[GenerateResponseChunk] = []

    chunk_role: Role = 'model'

    def make_chunk(
        role: Role, chunk: GenerateResponseChunk
    ) -> GenerateResponseChunk:
        """convenience method to create a full chunk from role and data, append
        the chunk to the previousChunks array, and increment the message index
        as needed"""
        nonlocal chunk_role, message_index

        if role != chunk_role and len(prev_chunks.length) > 0:
            message_index += 1

        chunk_role = role

        prev_to_send = copy.copy(prev_chunks)
        prev_chunks.append(chunk)

        return GenerateResponseChunkWrapper(
            chunk, index=message_index, previous_chunks=prev_to_send
        )

    model_response = (
        await model.arun(input=request, on_chunk=on_chunk)
    ).response
    response = GenerateResponseWrapper(model_response, request)

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
        interrupted_resp = GenerateResponseWrapper(response, request)
        interrupted_resp.finish_reason = 'interrupted'
        interrupted_resp.finish_message = (
            'One or more tool calls resulted in interrupts.'
        )
        interrupted_resp.message = revised_model_msg
        return interrupted_resp

    # if the loop will continue, stream out the tool response message...
    if on_chunk:
        on_chunk(
            make_chunk('tool', GenerateResponseChunk(content=tool_msg.content))
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
    )


def apply_transfer_preamble(
    next_request: GenerateActionOptions, preamble: GenerateActionOptions
) -> GenerateActionOptions:
    # TODO: implement me
    return next_request


def assert_valid_tool_names(raw_request: GenerateActionOptions):
    # TODO: implement me
    pass


def resolve_parameters(
    registry: Registry, request: GenerateActionOptions
) -> tuple[Action, list[Action]]:
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

    return (model_action, tools)


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
        context=options.docs,
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
