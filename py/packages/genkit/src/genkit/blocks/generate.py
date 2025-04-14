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

"""Generate action."""

import copy
from collections.abc import Callable
from typing import Any

from genkit.blocks.formats import FormatDef, Formatter
from genkit.blocks.messages import inject_instructions
from genkit.blocks.middleware import augment_with_context
from genkit.blocks.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    MessageWrapper,
    ModelMiddleware,
)
from genkit.blocks.tools import ToolInterruptError
from genkit.codec import dump_dict
from genkit.core.action import ActionRunContext
from genkit.core.error import GenkitError, StatusName
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
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)

StreamingCallback = Callable[[GenerateResponseChunkWrapper], None]

DEFAULT_MAX_TURNS = 5


async def generate_action(
    registry: Registry,
    raw_request: GenerateActionOptions,
    on_chunk: StreamingCallback | None = None,
    message_index: int = 0,
    current_turn: int = 0,
    middleware: list[ModelMiddleware] | None = None,
    context: dict[str, Any] | None = None,
) -> GenerateResponseWrapper:
    """Generate action.

    Args:
        registry: The registry to use for the action.
        raw_request: The raw request to generate.
        on_chunk: The callback to use for the action.
        message_index: The index of the message to use for the action.
        current_turn: The current turn of the action.
        middleware: The middleware to use for the action.
        context: The context to use for the action.

    Returns:
        The generated response.
    """
    model, tools, format_def = resolve_parameters(registry, raw_request)

    raw_request, formatter = apply_format(raw_request, format_def)

    assert_valid_tool_names(tools)

    (
        revised_request,
        interrupted_response,
        resumed_tool_message,
    ) = await _resolve_resume_options(registry, raw_request)

    # NOTE: in the future we should make it possible to interrupt a restart, but
    # at the moment it's too complicated because it's not clear how to return a
    # response that amends history but doesn't generate a new message, so we throw
    if interrupted_response:
        raise GenkitError(
            status='FAILED_PRECONDITION',
            message='One or more tools triggered an interrupt during a restarted execution.',
            details={'message': interrupted_response.message},
        )
    raw_request = revised_request

    request = await action_to_generate_request(raw_request, tools, model)

    prev_chunks: list[GenerateResponseChunk] = []

    chunk_role: Role = Role.MODEL

    def make_chunk(role: Role, chunk: GenerateResponseChunk) -> GenerateResponseChunkWrapper:
        """Creates a GenerateResponseChunkWrapper from role and data.

        This convenience method wraps a raw chunk, adds metadata like the
        current message index and previous chunks, appends the raw chunk
        to the internal `prev_chunks` list, and increments the message index
        if the role changes.

        Args:
            role: The role (e.g., MODEL, TOOL) associated with this chunk.
            chunk: The raw GenerateResponseChunk data.

        Returns:
            A GenerateResponseChunkWrapper containing the chunk and metadata.
        """
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

    def wrap_chunks(role: Role = Role.MODEL):
        """Wrap and process a model response chunk.

        This function prepares model response chunks for the stream callback.

        Args:
            chunk: The original model response chunk.

        Returns:
            The result of passing the processed chunk to the callback.
        """

        def wrapper(chunk):
            on_chunk(make_chunk(role, chunk))

        return wrapper

    if not middleware:
        middleware = []

    supports_context = (
        model.metadata
        and model.metadata.get('model')
        and model.metadata.get('model').get('supports')
        and model.metadata.get('model').get('supports').get('context')
    )
    # if it doesn't support contextm inject context middleware
    if raw_request.docs and not supports_context:
        middleware.append(augment_with_context())

    async def dispatch(index: int, req: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Dispatches model request, passing it through middleware if present.

        Args:
            index: The index of the middleware to use.
            req: The request to dispatch.
            ctx: The context to use for the action.

        Returns:
            The generated response.
        """
        if not middleware or index == len(middleware):
            # end of the chain, call the original model action
            return (
                await model.arun(
                    input=req,
                    context=ctx.context,
                    on_chunk=ctx.send_chunk if ctx.is_streaming else None,
                )
            ).response

        current_middleware = middleware[index]

        async def next_fn(modified_req=None, modified_ctx=None):
            return await dispatch(
                index + 1,
                modified_req if modified_req else req,
                modified_ctx if modified_ctx else ctx,
            )

        return await current_middleware(req, ctx, next_fn)

    # if resolving the 'resume' option above generated a tool message, stream it.
    if resumed_tool_message and on_chunk:
        wrap_chunks('tool')(resumed_tool_message)

    model_response = await dispatch(
        0,
        request,
        ActionRunContext(
            on_chunk=wrap_chunks() if on_chunk else None,
            context=context,
        ),
    )

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

    max_iters = raw_request.max_turns if raw_request.max_turns else DEFAULT_MAX_TURNS

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

    # if an interrupt message is returned, stop the tool loop and return a
    # response.
    if revised_model_msg:
        interrupted_resp = GenerateResponseWrapper(
            response,
            request,
            message_parser=message_parser if formatter else None,
        )
        interrupted_resp.finish_reason = 'interrupted'
        interrupted_resp.finish_message = 'One or more tool calls resulted in interrupts.'
        interrupted_resp.message = MessageWrapper(revised_model_msg)
        return interrupted_resp

    # If the loop will continue, stream out the tool response message...
    if on_chunk:
        on_chunk(
            make_chunk(
                'tool',
                GenerateResponseChunk(role=tool_msg.role, content=tool_msg.content),
            )
        )

    next_request = copy.copy(raw_request)
    next_messages = copy.copy(raw_request.messages)
    next_messages.append(generated_msg)
    next_messages.append(tool_msg)
    next_request.messages = next_messages
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
    """Applies formatting instructions and configuration to the request.

    If a format definition is provided, this function deep copies the request,
    resolves formatting instructions, applies them to the messages, and updates
    output configuration based on the format definition and the request's
    original output settings.

    Args:
        raw_request: The original generation request options.
        format_def: The format definition to apply, or None.

    Returns:
        A tuple containing the potentially modified request options and the
        resolved Formatter instance (or None if no format was applied).
    """
    if not format_def:
        return raw_request, None

    out_request = copy.deepcopy(raw_request)

    formatter = format_def(raw_request.output.json_schema if raw_request.output else None)

    instructions = resolve_instructions(
        formatter,
        raw_request.output.instructions if raw_request.output else None,
    )

    if (
        format_def.config.default_instructions != False or raw_request.output.instructions
        if raw_request.output
        else False
    ):
        out_request.messages = inject_instructions(out_request.messages, instructions)

    if format_def.config.constrained is not None:
        out_request.output.constrained = format_def.config.constrained
    if raw_request.output.constrained is not None:
        out_request.output.constrained = raw_request.output.constrained

    if format_def.config.content_type is not None:
        out_request.output.content_type = format_def.config.content_type
    if format_def.config.format is not None:
        out_request.output.format = format_def.config.format

    return (out_request, formatter)


def resolve_instructions(formatter: Formatter, instructions_opt: bool | str | None):
    """Resolve instructions based on formatter and instruction options.

    Args:
        formatter: The formatter to use for resolving instructions.
        instructions_opt: The instruction options: True/False, a string, or
            None.

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


def apply_transfer_preamble(next_request: GenerateActionOptions, preamble: GenerateActionOptions):
    """Applies relevant properties from a preamble request to the next request.

    This function is intended to copy settings (like model, config, etc.)
    from a preamble, which might be generated by a tool during processing,
    to the subsequent generation request.

    Note: This function is currently a placeholder (TODO).

    Args:
        next_request: The generation request to be modified.
        preamble: The preamble request containing properties to transfer.

    Returns:
        The potentially updated `next_request`.
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
    """Resolve parameters for the generate action.

    Args:
        registry: The registry to use for the action.
        request: The generation request to resolve parameters for.

    Returns:
        A tuple containing the model action, the list of tool actions, and the
        format definition.
    """
    model = request.model if request.model is not None else registry.default_model
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
            raise ValueError(f'Unable to resolve format {request.output.format}')

    return (model_action, tools, format_def)


async def action_to_generate_request(
    options: GenerateActionOptions, resolved_tools: list[Action], model: Action
) -> GenerateRequest:
    """Convert generate action options to a generate request.

    Args:
        options: The generation options to convert.
        resolved_tools: The resolved tools to use for the action.
        model: The model to use for the action.

    Returns:
        The generated request.
    """
    # TODO: add warning when tools are not supported in ModelInfo
    # TODO: add warning when toolChoice is not supported in ModelInfo

    tool_defs = [to_tool_definition(tool) for tool in resolved_tools] if resolved_tools else []
    return GenerateRequest(
        messages=options.messages,
        config=options.config if options.config is not None else {},
        docs=options.docs,
        tools=tool_defs,
        tool_choice=options.tool_choice,
        output=OutputConfig(
            content_type=options.output.content_type if options.output else None,
            format=options.output.format if options.output else None,
            schema_=options.output.json_schema if options.output else None,
            constrained=options.output.constrained if options.output else None,
        ),
    )


def to_tool_definition(tool: Action) -> ToolDefinition:
    """Convert an action to a tool definition.

    Args:
        tool: The action to convert.

    Returns:
        The converted tool definition.
    """
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
    """Resolve tool requests for the generate action.

    Args:
        registry: The registry to use for the action.
        request: The generation request to resolve tool requests for.
        message: The message to resolve tool requests for.

    Returns:
        A tuple containing the revised model message, the tool message, and the
        transfer preamble.
    """
    # TODO: prompt transfer
    tool_dict: dict[str, Action] = {}
    for tool_name in request.tools:
        tool_dict[tool_name] = resolve_tool(registry, tool_name)

    revised_model_message = message._original_message.model_copy(deep=True)

    has_interrupts = False
    response_parts: list[ToolResponsePart] = []
    i = 0
    for tool_request_part in message.content:
        is_tool_request = isinstance(tool_request_part, Part) and isinstance(tool_request_part.root, ToolRequestPart)

        if not is_tool_request:
            i += 1
            continue

        tool_request = tool_request_part.root.tool_request

        if tool_request.name not in tool_dict:
            raise RuntimeError(f'failed {tool_request.name} not found')
        tool = tool_dict[tool_request.name]
        tool_response_part, interrupt_part = await _resolve_tool_request(tool, tool_request_part.root)

        if tool_response_part:
            revised_model_message.content[i] = _to_pending_response(tool_request_part.root, tool_response_part.root)
            response_parts.append(tool_response_part)

        if interrupt_part:
            has_interrupts = True
            revised_model_message.content[i] = interrupt_part

        i += 1

    if has_interrupts:
        return (revised_model_message, None, None)

    return (None, Message(role=Role.TOOL, content=response_parts), None)


def _to_pending_response(request: ToolRequestPart, response: ToolResponsePart) -> ToolRequestPart:
    """Updates a ToolRequestPart to mark it as pending with its response data.

    This is used when a tool call is made, and its response is available,
    but the overall generation loop might continue (e.g., for other tool calls).
    The response output is stored in the request's metadata under 'pendingOutput'.

    Args:
        request: The original ToolRequestPart.
        response: The corresponding ToolResponsePart.

    Returns:
        A new Part containing the original tool request but with updated metadata
        indicating the pending output.
    """
    metadata = request.metadata.root if request.metadata else {}
    metadata['pendingOutput'] = response.tool_response.output
    return Part(tool_request=request.tool_request, metadata=metadata)


async def _resolve_tool_request(tool: Action, tool_request_part: ToolRequestPart) -> tuple[Part, Part]:
    """Executes a tool action and returns its response or interrupt part.

    Calls the tool's `arun_raw` method with the input from the tool request.
    Handles potential ToolInterruptErrors by returning a specific interrupt Part.

    Args:
        tool: The resolved tool Action to execute.
        tool_request_part: The Part containing the tool request details.

    Returns:
        A tuple containing:
            - A Part with the ToolResponse if successful, else None.
            - A Part marking an interrupt if a ToolInterruptError occurred, else None.

    Raises:
        GenkitError: If any error other than ToolInterruptError occurs during
                     tool execution.
    """
    try:
        tool_response = (await tool.arun_raw(tool_request_part.tool_request.input)).response
        return (
            Part(
                tool_response=ToolResponse(
                    name=tool_request_part.tool_request.name,
                    ref=tool_request_part.tool_request.ref,
                    output=dump_dict(tool_response),
                )
            ),
            None,
        )
    except GenkitError as e:
        if e.cause and isinstance(e.cause, ToolInterruptError):
            interrupt_error = e.cause
            return (
                None,
                Part(
                    tool_request=tool_request_part.tool_request,
                    metadata={
                        **(tool_request_part.metadata if tool_request_part.metadata else {}),
                        'interrupt': (interrupt_error.metadata if interrupt_error.metadata else True),
                    },
                ),
            )

        raise e


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


async def _resolve_resume_options(
    registry: Registry, raw_request: GenerateActionOptions
) -> tuple[GenerateActionOptions, GenerateResponse, Message]:
    """Resolves tool calls from a previous turn when resuming generation.

    Handles the `resume` option in GenerateActionOptions. It processes the
    last model message (which should contain tool requests), resolves pending
    outputs or applies provided responses/restarts from the `resume` argument,
    and constructs a tool message to append to the history.

    Args:
        registry: The action registry (unused in current implementation).
        raw_request: The incoming generation request potentially with resume options.

    Returns:
        A tuple containing:
        - revised_request: The request updated with the new tool message in history
                           and the `resume` field cleared.
        - interrupted_response: Currently always None (interrupts during resume
                                are not fully supported yet).
        - tool_message: The constructed tool message with resolved responses,
                        or None if not resuming.

    Raises:
        GenkitError: If the request format is invalid for resuming (e.g., last
                     message is not a model message with tool requests) or if
                     interrupted tool requests are not handled by the resume options.
    """
    if not raw_request.resume:
        return (raw_request, None, None)

    messages = raw_request.messages
    last_message = messages[-1]
    tool_requests = [p for p in last_message.content if p.root.tool_request]
    if not last_message or last_message.role != Role.MODEL or len(tool_requests) == 0:
        raise GenkitError(
            status='FAILED_PRECONDITION',
            message="Cannot 'resume' generation unless the previous message is a model message with at least one tool request.",
        )

    i = 0
    tool_responses = []
    for part in last_message.content:
        if not isinstance(part.root, ToolRequestPart):
            i += 1
            continue

        resumed_request, resumed_response = _resolve_resumed_tool_request(raw_request, part)
        tool_responses.append(resumed_response)
        last_message.content[i] = resumed_request
        i += 1

    if len(tool_responses) != len(tool_requests):
        raise GenkitError(
            status='FAILED_PRECONDITION',
            message=f'Ecxpected {len(tool_requests)} responses, but resolved to {len(tool_responses)}',
        )

    tool_message = Message(
        role=Role.TOOL,
        content=tool_responses,
        metadata={'resumed': (raw_request.resume.metadata if raw_request.resume.metadata else True)},
    )

    revised_request = raw_request.model_copy(deep=True)
    revised_request.resume = None
    revised_request.messages.append(tool_message)

    return (revised_request, None, tool_message)


def _resolve_resumed_tool_request(raw_request: GenerateActionOptions, tool_request_part: Part) -> tuple[Part, Part]:
    """Resolves a single tool request based on resume options.

    Checks if the tool request part has pending output in its metadata or if a
    corresponding response is provided in the `raw_request.resume.respond` list.
    Constructs the appropriate request and response parts for the tool history.

    Args:
        raw_request: The overall generation request containing resume options.
        tool_request_part: The specific tool request Part from the previous turn.

    Returns:
        A tuple containing:
        - request_part: The ToolRequest Part to be kept/added in the history.
                        Metadata might be updated (e.g., 'resolvedInterrupt').
        - response_part: The corresponding ToolResponse Part derived from pending
                         output or provided responses.

    Raises:
        GenkitError: If the tool request cannot be resolved (neither pending
                     output nor a provided response is found).
    """
    if tool_request_part.root.metadata and 'pendingOutput' in tool_request_part.root.metadata.root:
        metadata = tool_request_part.root.metadata.root.copy()
        pending_output = metadata['pendingOutput']
        del metadata['pendingOutput']
        metadata['source'] = 'pending'
        return (
            tool_request_part,
            Part(
                tool_response=ToolResponse(
                    name=tool_request_part.root.tool_request.name,
                    ref=tool_request_part.root.tool_request.ref,
                    output=dump_dict(pending_output),
                ),
                metadata=Metadata(root=metadata),
            ),
        )

    # if there's a corresponding reply, append it to toolResponses
    provided_response = _find_corresponding_tool_response(
        (raw_request.resume.respond if raw_request.resume and raw_request.resume.respond else []),
        tool_request_part.root,
    )
    if provided_response:
        # remove the 'interrupt' but leave a 'resolvedInterrupt'
        metadata = tool_request_part.root.metadata.root if tool_request_part.root.metadata else {}
        interrupt = metadata.get('interrupt')
        if interrupt:
            del metadata['interrupt']
        return (
            Part(
                tool_request=ToolRequest(
                    name=tool_request_part.root.tool_request.name,
                    ref=tool_request_part.root.tool_request.ref,
                    input=tool_request_part.root.tool_request.input,
                ),
                metadata=Metadata(root={**metadata, 'resolvedInterrupt': interrupt}),
            ),
            provided_response,
        )

    raise GenkitError(
        status='INVALID_ARGUMENT',
        message=f"Unresolved tool request '{tool_request_part.root.tool_request.name}' "
        + "was not handled by the 'resume' argument. You must supply replies or "
        + 'restarts for all interrupted tool requests.',
    )


def _find_corresponding_tool_response(responses: list[ToolResponsePart], request: ToolRequestPart) -> Part | None:
    """Finds a response part corresponding to a given request part by name and ref.

    Args:
        responses: A list of ToolResponseParts to search within.
        request: The ToolRequestPart to find a corresponding response for.

    Returns:
        The matching ToolResponsePart as a Part, or None if no match is found.
    """
    for p in responses:
        if p.tool_response.name == request.tool_request.name and p.tool_response.ref == request.tool_request.ref:
            return p
    return None


# TODO: extend GenkitError
class GenerationResponseError(Exception):
    # TODO: use status enum
    """Error for generation responses."""

    def __init__(
        self,
        response: GenerateResponse,
        message: str,
        status: str,
        details: dict[str, Any],
    ):
        """Initialize the GenerationResponseError.

        Args:
            response: The generation response.
            message: The message to display.
            status: The status of the generation response.
            details: The details of the generation response.
        """
        self.response = response
        self.message = message
        self.status = status
        self.details = details
