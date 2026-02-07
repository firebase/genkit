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

"""Mistral AI model integration for Genkit.

This module provides the model implementation for Mistral AI,
converting between Genkit and Mistral SDK formats.
"""

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from mistralai import Mistral as MistralClient
from mistralai.models import (
    AssistantMessage,
    ChatCompletionChoice,
    ChatCompletionResponse,
    CompletionChunk,
    CompletionEvent,
    Function,
    FunctionCall,
    SystemMessage,
    TextChunk,
    Tool,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from pydantic import BaseModel, Field

from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    Message,
    OutputConfig,
    Part,
    Role,
    TextPart,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)
from genkit.plugins.mistral.model_info import (
    SUPPORTED_MISTRAL_MODELS,
    get_default_model_info,
)

MISTRAL_PLUGIN_NAME = 'mistral'


def mistral_name(name: str) -> str:
    """Create a Mistral action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Mistral action name.
    """
    return f'{MISTRAL_PLUGIN_NAME}/{name}'


class MistralConfig(BaseModel):
    """Configuration options for Mistral AI models.

    Attributes:
        temperature: Controls randomness (0.0-1.0). Lower = more deterministic.
        max_tokens: Maximum number of tokens to generate.
        top_p: Nucleus sampling parameter (0.0-1.0).
        random_seed: Seed for reproducible outputs.
        safe_prompt: Whether to inject safety prompt (deprecated, use safe_mode).
        safe_mode: Whether to enable safe mode for content filtering.
    """

    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    random_seed: int | None = None
    safe_prompt: bool | None = None
    safe_mode: bool | None = None


class MistralModel:
    """Manages Mistral AI model integration for Genkit.

    This class provides integration with Mistral's official Python SDK,
    allowing Mistral models to be exposed as Genkit models.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        **mistral_params: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the Mistral model instance.

        Args:
            model: The name of the specific Mistral model.
            api_key: Mistral API key for authentication.
            **mistral_params: Additional parameters for the Mistral client.
        """
        self.name = model
        self.client = MistralClient(api_key=api_key, **mistral_params)

    def get_model_info(self) -> dict[str, Any] | None:
        """Retrieve metadata and supported features for the specified model.

        Returns:
            A dictionary containing the model's 'name' and 'supports' features.
        """
        model_info = SUPPORTED_MISTRAL_MODELS.get(self.name, get_default_model_info(self.name))
        supports_dict = model_info.supports.model_dump() if model_info.supports else {}
        return {
            'name': model_info.label,
            'supports': supports_dict,
        }

    def _convert_messages(
        self, messages: list[Message]
    ) -> list[SystemMessage | UserMessage | AssistantMessage | ToolMessage]:
        """Convert Genkit messages to Mistral message format.

        Args:
            messages: List of Genkit messages.

        Returns:
            List of Mistral SDK message objects.
        """
        mistral_messages: list[SystemMessage | UserMessage | AssistantMessage | ToolMessage] = []

        for msg in messages:
            content_parts: list[str] = []
            tool_calls: list[ToolCall] = []
            tool_responses: list[tuple[str, str, str]] = []  # (ref, name, output)

            for part in msg.content:
                part_root = part.root
                if isinstance(part_root, TextPart):
                    content_parts.append(part_root.text)
                elif isinstance(part_root, ToolRequestPart):
                    # Convert Genkit ToolRequest to Mistral ToolCall
                    tool_req = part_root.tool_request
                    tool_calls.append(
                        ToolCall(
                            id=tool_req.ref or '',
                            type='function',
                            function=FunctionCall(
                                name=tool_req.name,
                                arguments=json.dumps(tool_req.input) if tool_req.input else '{}',
                            ),
                        )
                    )
                elif isinstance(part_root, ToolResponsePart):
                    # Collect tool responses to add as ToolMessage
                    tool_resp = part_root.tool_response
                    output = tool_resp.output
                    if isinstance(output, dict):
                        output_str = json.dumps(output)
                    else:
                        output_str = str(output) if output is not None else ''
                    tool_responses.append((tool_resp.ref or '', tool_resp.name or '', output_str))

            content = '\n'.join(content_parts) if content_parts else ''

            if msg.role == Role.SYSTEM:
                mistral_messages.append(SystemMessage(content=content))
            elif msg.role == Role.USER:
                mistral_messages.append(UserMessage(content=content))
            elif msg.role == Role.MODEL:
                # Assistant message may have text and/or tool calls
                if tool_calls:
                    mistral_messages.append(
                        AssistantMessage(content=content if content else None, tool_calls=tool_calls)
                    )
                else:
                    mistral_messages.append(AssistantMessage(content=content))
            elif msg.role == Role.TOOL:
                # Tool responses become ToolMessage
                for ref, name, output_str in tool_responses:
                    mistral_messages.append(ToolMessage(tool_call_id=ref, name=name, content=output_str))

        return mistral_messages

    def _convert_response(self, response: ChatCompletionResponse) -> GenerateResponse:
        """Convert Mistral response to Genkit GenerateResponse.

        Args:
            response: Mistral chat completion response.

        Returns:
            Genkit GenerateResponse.
        """
        choice: ChatCompletionChoice = response.choices[0]
        content: list[Part] = []

        if choice.message.content:
            # Handle string or list content
            msg_content = choice.message.content
            if isinstance(msg_content, str):
                content.append(Part(root=TextPart(text=msg_content)))
            elif isinstance(msg_content, list):
                # Extract text from content chunks
                for chunk in msg_content:
                    if isinstance(chunk, TextChunk):
                        content.append(Part(root=TextPart(text=chunk.text)))

        # Handle tool calls in the response
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                # Parse arguments from JSON string or dict
                args: dict[str, Any] | str = {}
                if tool_call.function and tool_call.function.arguments:
                    func_args = tool_call.function.arguments
                    if isinstance(func_args, str):
                        try:
                            args = json.loads(func_args)
                        except json.JSONDecodeError:
                            args = func_args
                    elif isinstance(func_args, dict):
                        args = func_args
                    else:
                        args = str(func_args)

                content.append(
                    Part(
                        root=ToolRequestPart(
                            tool_request=ToolRequest(
                                ref=tool_call.id or None,
                                name=tool_call.function.name if tool_call.function else '',
                                input=args,
                            )
                        )
                    )
                )

        message = Message(role=Role.MODEL, content=content)

        usage = None
        if response.usage:
            usage = GenerationUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        # Map Mistral finish reason to Genkit FinishReason
        finish_reason = FinishReason.STOP
        if choice.finish_reason:
            if choice.finish_reason == 'length':
                finish_reason = FinishReason.LENGTH
            elif choice.finish_reason == 'tool_calls' or choice.finish_reason == 'stop':
                finish_reason = FinishReason.STOP
            else:
                finish_reason = FinishReason.OTHER

        return GenerateResponse(
            message=message,
            finish_reason=finish_reason,
            usage=usage,
        )

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[Tool]:
        """Convert Genkit tool definitions to Mistral Tool format.

        Args:
            tools: List of Genkit tool definitions.

        Returns:
            List of Mistral Tool objects.
        """
        mistral_tools: list[Tool] = []
        for tool in tools:
            # Build parameters schema with additionalProperties: false for strict mode
            parameters = tool.input_schema or {}
            if parameters and 'additionalProperties' not in parameters:
                parameters = {**parameters, 'additionalProperties': False}

            mistral_tools.append(
                Tool(
                    type='function',
                    function=Function(
                        name=tool.name,
                        description=tool.description or '',
                        parameters=parameters,
                    ),
                )
            )
        return mistral_tools

    def _get_response_format(self, output: OutputConfig) -> dict[str, Any] | None:
        """Get response format configuration for structured output.

        Args:
            output: Output configuration specifying desired format.

        Returns:
            Response format dict for Mistral API, or None for default.
        """
        if output.format == 'json':
            if output.schema:
                # Use JSON schema mode for structured output
                return {
                    'type': 'json_schema',
                    'json_schema': {
                        'name': output.schema.get('title', 'Response'),
                        'schema': output.schema,
                        'strict': True,
                    },
                }
            # Use basic JSON mode
            return {'type': 'json_object'}
        return None

    async def generate(
        self,
        request: GenerateRequest,
        ctx: ActionRunContext | None = None,
    ) -> GenerateResponse:
        """Generate a response using the Mistral model.

        Args:
            request: The generation request.
            ctx: Optional action run context for streaming.

        Returns:
            The generated response.
        """
        messages = self._convert_messages(request.messages)

        # Build request parameters
        params: dict[str, Any] = {
            'model': self.name,
            'messages': messages,
        }

        # Add tools if provided
        if request.tools:
            params['tools'] = self._convert_tools(request.tools)

        # Handle tool choice
        if any(msg.role == Role.TOOL for msg in request.messages):
            # After a tool response, don't force additional tool calls
            params['tool_choice'] = 'none'
        elif request.tool_choice:
            params['tool_choice'] = request.tool_choice

        # Handle structured output
        if request.output:
            response_format = self._get_response_format(request.output)
            if response_format:
                params['response_format'] = response_format

        # Apply config if provided
        if request.config:
            config = request.config
            if isinstance(config, dict):
                if config.get('temperature') is not None:
                    params['temperature'] = config['temperature']
                if config.get('max_tokens') is not None:
                    params['max_tokens'] = config['max_tokens']
                if config.get('top_p') is not None:
                    params['top_p'] = config['top_p']
                if config.get('random_seed') is not None:
                    params['random_seed'] = config['random_seed']

        # Handle streaming
        if ctx and ctx.send_chunk:
            return await self._generate_streaming(params, ctx)

        # Non-streaming request
        response = await self.client.chat.complete_async(**params)
        if response is None:
            return GenerateResponse(
                message=Message(role=Role.MODEL, content=[Part(root=TextPart(text=''))]),
                finish_reason=FinishReason.STOP,
            )
        return self._convert_response(response)

    async def _generate_streaming(
        self,
        params: dict[str, Any],
        ctx: ActionRunContext,
    ) -> GenerateResponse:
        """Generate a streaming response.

        Args:
            params: Request parameters.
            ctx: Action run context with send_chunk callback.

        Returns:
            The complete generated response.
        """
        full_text = ''
        finish_reason: FinishReason = FinishReason.STOP
        accumulated_content: list[Part] = []

        # Track tool calls being streamed (by index)
        tool_calls: dict[int, dict[str, Any]] = {}

        stream: AsyncIterator[CompletionEvent] = await self.client.chat.stream_async(**params)

        async for event in stream:
            chunk: CompletionChunk = event.data
            if chunk.choices:
                choice = chunk.choices[0]

                # Handle text content
                if choice.delta and choice.delta.content:
                    content = choice.delta.content
                    # Handle TextChunk or string
                    text = content.text if isinstance(content, TextChunk) else str(content)
                    full_text += text

                    # Send chunk to client
                    ctx.send_chunk(
                        GenerateResponseChunk(
                            role=Role.MODEL,
                            content=[Part(root=TextPart(text=text))],
                        )
                    )

                # Handle tool calls in streaming
                if choice.delta and choice.delta.tool_calls:
                    for tool_call in choice.delta.tool_calls:
                        idx: int = tool_call.index if hasattr(tool_call, 'index') and tool_call.index is not None else 0
                        if idx not in tool_calls:
                            tool_calls[idx] = {
                                'id': tool_call.id or '',
                                'name': tool_call.function.name if tool_call.function else '',
                                'arguments': '',
                            }
                        # Accumulate arguments
                        if tool_call.function and tool_call.function.arguments:
                            tool_calls[idx]['arguments'] += tool_call.function.arguments

                if choice.finish_reason:
                    # Map Mistral finish reason to Genkit FinishReason
                    if choice.finish_reason == 'length':
                        finish_reason = FinishReason.LENGTH
                    elif choice.finish_reason in ('stop', 'tool_calls'):
                        finish_reason = FinishReason.STOP
                    else:
                        finish_reason = FinishReason.OTHER

        # Build final content
        if full_text:
            accumulated_content.append(Part(root=TextPart(text=full_text)))

        # Add accumulated tool calls
        for tc in tool_calls.values():
            args: dict[str, Any] | str = {}
            if tc['arguments']:
                try:
                    args = json.loads(tc['arguments'])
                except json.JSONDecodeError:
                    args = tc['arguments']

            tool_part = Part(
                root=ToolRequestPart(
                    tool_request=ToolRequest(
                        ref=tc['id'] or None,
                        name=tc['name'],
                        input=args,
                    )
                )
            )
            accumulated_content.append(tool_part)

            # Send tool call chunk
            ctx.send_chunk(
                GenerateResponseChunk(
                    role=Role.MODEL,
                    content=[tool_part],
                )
            )

        return GenerateResponse(
            message=Message(role=Role.MODEL, content=accumulated_content),
            finish_reason=finish_reason,
        )

    def to_generate_fn(self) -> Callable:
        """Convert the Mistral model into a Genkit-compatible generate function.

        Returns:
            A callable function that can be used by Genkit.
        """
        return self.generate
