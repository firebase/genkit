# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import sys
from typing import Any, Callable, Dict, List, Tuple

from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
)
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
from genkit.core.utils import dump_dict

logger = logging.getLogger(__name__)

StreamingCallback = Callable[[GenerateResponseChunkWrapper], None]


async def generate_action(
    registry: Registry,
    rawRequest: GenerateActionOptions,
    on_chunk: StreamingCallback | None = None,
    messageIndex: int = 0,
    currentTurn: int = 0,
) -> GenerateResponseWrapper:
    # TODO: formats
    # TODO: middleware

    model, tools = resolve_parameters(registry, rawRequest)

    assert_valid_tool_names(tools)

    # TODO: interrupts

    request = await action_to_generate_request(rawRequest, tools, model)

    previousChunks: List[GenerateResponseChunk] = []

    chunkRole: Role = 'model'

    def makeChunk(
        role: Role, chunk: GenerateResponseChunk
    ) -> GenerateResponseChunk:
        """convenience method to create a full chunk from role and data, append the chunk
        to the previousChunks array, and increment the message index as needed"""

        if role != chunkRole and len(previousChunks.length) > 0:
            messageIndex += 1

        chunkRole = role

        prevToSend = copy.copy(previousChunks)
        previousChunks.append(chunk)

        return GenerateResponseChunkWrapper(
            chunk, index=messageIndex, previousChunks=prevToSend
        )

    model_response = (
        await model.arun(input=request, on_chunk=on_chunk)
    ).response
    response = GenerateResponseWrapper(model_response, request)

    response.assert_valid()
    generatedMessage = response.message

    toolRequests = [
        x for x in response.message.content if x.root.tool_request != None
    ]

    if rawRequest.return_tool_requests or len(toolRequests) == 0:
        if len(toolRequests) == 0:
            response.assert_valid_schema()
        return response

    maxIterations = rawRequest.max_turns if rawRequest.max_turns != None else 5

    if currentTurn + 1 > maxIterations:
        raise GenerationResponseError(
            response=response,
            message=f'Exceeded maximum tool call iterations ({maxIterations})',
            status='ABORTED',
            details={'request': request},
        )

    (
        revisedModelMessage,
        toolMessage,
        transferPreamble,
    ) = await resolve_tool_requests(registry, rawRequest, generatedMessage)

    # if an interrupt message is returned, stop the tool loop and return a response
    if revisedModelMessage != None:
        interruptedResponse = GenerateResponseWrapper(response, request)
        interruptedResponse.finish_reason = 'interrupted'
        interruptedResponse.finish_message = (
            'One or more tool calls resulted in interrupts.'
        )
        interruptedResponse.message = revisedModelMessage
        return interruptedResponse

    # if the loop will continue, stream out the tool response message...
    if on_chunk != None:
        on_chunk(
            makeChunk(
                'tool', GenerateResponseChunk(content=toolMessage.content)
            )
        )

    nextRequest = copy.copy(rawRequest)
    nextMessages = copy.copy(rawRequest.messages)
    nextMessages.append(generatedMessage)
    nextMessages.append(toolMessage)
    nextRequest.messages = nextMessages
    nextRequest = apply_transfer_preamble(nextRequest, transferPreamble)

    # then recursively call for another loop
    return await generate_action(
        registry,
        rawRequest=nextRequest,
        # middleware: middleware,
        currentTurn=currentTurn + 1,
        messageIndex=messageIndex + 1,
    )


def apply_transfer_preamble(
    nextRequest: GenerateActionOptions, preamble: GenerateActionOptions
) -> GenerateActionOptions:
    # TODO: implement me
    return nextRequest


def assert_valid_tool_names(rawRequest: GenerateActionOptions):
    # TODO: implement me
    pass


def resolve_parameters(
    registry: Registry, request: GenerateActionOptions
) -> Tuple[Action, list[Action]]:
    model = (
        request.model if request.model is not None else registry.defaultModel
    )
    if model is None:
        raise Exception('No model configured.')

    model_action = registry.lookup_action(ActionKind.MODEL, model)
    if model_action is None:
        raise Exception(f'Failed to to resolve model {model}')

    tools: list[Action] = []
    if request.tools != None:
        for toolName in request.tools:
            tool_action = registry.lookup_action(ActionKind.TOOL, toolName)
            if tool_action is None:
                raise Exception(f'Unable to resolve tool {toolName}')
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
) -> Tuple[Message, Message, GenerateActionOptions]:
    # TODO: interrupts
    # TODO: prompt transfer

    tool_requests = [
        x.root.tool_request
        for x in message.content
        if x.root.tool_request != None
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
        details: Dict[str, any],
    ):
        self.response = response
        self.message = message
        self.status = status
        self.details = details
