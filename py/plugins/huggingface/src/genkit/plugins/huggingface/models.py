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

"""Hugging Face model integration for Genkit.

This module provides the model implementation for Hugging Face,
using the huggingface_hub InferenceClient.
"""

import json
from collections.abc import Callable
from typing import Any

from huggingface_hub import InferenceClient
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
from genkit.plugins.huggingface.model_info import (
    POPULAR_HUGGINGFACE_MODELS,
    get_default_model_info,
)

HUGGINGFACE_PLUGIN_NAME = 'huggingface'


def huggingface_name(name: str) -> str:
    """Create a Hugging Face action name.

    Args:
        name: Base name for the action (model ID like 'meta-llama/Llama-3.3-70B-Instruct').

    Returns:
        The fully qualified Hugging Face action name.
    """
    return f'{HUGGINGFACE_PLUGIN_NAME}/{name}'


class HuggingFaceConfig(BaseModel):
    """Configuration options for Hugging Face models.

    Attributes:
        temperature: Controls randomness (0.0-2.0). Lower = more deterministic.
        max_tokens: Maximum number of tokens to generate.
        top_p: Nucleus sampling parameter (0.0-1.0).
        top_k: Top-k sampling parameter.
        repetition_penalty: Penalty for repeating tokens (1.0 = no penalty).
        seed: Seed for reproducible outputs.
        provider: Inference provider to use (e.g., 'cerebras', 'groq', 'together').
    """

    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1)
    repetition_penalty: float | None = Field(default=None, ge=0.0)
    seed: int | None = None
    provider: str | None = None


class HuggingFaceModel:
    """Manages Hugging Face model integration for Genkit.

    This class provides integration with Hugging Face's InferenceClient,
    allowing HF models to be exposed as Genkit models.
    """

    def __init__(
        self,
        model: str,
        token: str,
        provider: str | None = None,
        **hf_params: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the Hugging Face model instance.

        Args:
            model: The model ID (e.g., 'meta-llama/Llama-3.3-70B-Instruct').
            token: Hugging Face API token for authentication.
            provider: Optional inference provider (e.g., 'cerebras', 'groq').
            **hf_params: Additional parameters for the InferenceClient.
        """
        self.name = model
        self.provider = provider
        self.client = InferenceClient(token=token, **hf_params)

    def get_model_info(self) -> dict[str, Any] | None:
        """Retrieve metadata and supported features for the specified model.

        Returns:
            A dictionary containing the model's 'name' and 'supports' features.
        """
        model_info = POPULAR_HUGGINGFACE_MODELS.get(self.name, get_default_model_info(self.name))
        supports_dict = model_info.supports.model_dump() if model_info.supports else {}
        return {
            'name': model_info.label,
            'supports': supports_dict,
        }

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Genkit messages to HF chat format.

        Args:
            messages: List of Genkit messages.

        Returns:
            List of message dicts in HF format.
        """
        hf_messages: list[dict[str, Any]] = []

        for msg in messages:
            content_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []

            for part in msg.content:
                part_root = part.root
                if isinstance(part_root, TextPart):
                    content_parts.append(part_root.text)
                elif isinstance(part_root, ToolRequestPart):
                    # Convert Genkit ToolRequest to HF tool call format
                    tool_req = part_root.tool_request
                    tool_calls.append({
                        'id': tool_req.ref or '',
                        'type': 'function',
                        'function': {
                            'name': tool_req.name,
                            'arguments': json.dumps(tool_req.input) if tool_req.input else '{}',
                        },
                    })
                elif isinstance(part_root, ToolResponsePart):
                    # Tool responses become separate tool messages
                    tool_resp = part_root.tool_response
                    output = tool_resp.output
                    if isinstance(output, dict):
                        output_str = json.dumps(output)
                    else:
                        output_str = str(output) if output is not None else ''
                    hf_messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_resp.ref or '',
                        'content': output_str,
                    })
                    continue  # Don't add another message for this

            content = '\n'.join(content_parts) if content_parts else ''

            role = 'user'
            if msg.role == Role.SYSTEM:
                role = 'system'
            elif msg.role == Role.MODEL:
                role = 'assistant'
            elif msg.role == Role.USER:
                role = 'user'
            elif msg.role == Role.TOOL:
                # Tool messages are handled above in ToolResponsePart
                continue

            message_dict: dict[str, Any] = {'role': role, 'content': content}

            # Add tool calls to assistant message if present
            if tool_calls and role == 'assistant':
                message_dict['tool_calls'] = tool_calls

            hf_messages.append(message_dict)

        return hf_messages

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert Genkit tool definitions to HF tool format.

        Args:
            tools: List of Genkit tool definitions.

        Returns:
            List of tool dicts in HF format.
        """
        hf_tools: list[dict[str, Any]] = []
        for tool in tools:
            # Build parameters schema with additionalProperties: false for strict mode
            parameters = tool.input_schema or {}
            if parameters and 'additionalProperties' not in parameters:
                parameters = {**parameters, 'additionalProperties': False}

            hf_tools.append({
                'type': 'function',
                'function': {
                    'name': tool.name,
                    'description': tool.description or '',
                    'parameters': parameters,
                },
            })
        return hf_tools

    def _get_response_format(self, output: OutputConfig) -> dict[str, Any] | None:
        """Get response format configuration for structured output.

        Args:
            output: Output configuration specifying desired format.

        Returns:
            Response format dict for HF API, or None for default.
        """
        if output.format == 'json':
            if output.schema:
                # Use JSON schema mode for structured output
                return {
                    'type': 'json',
                    'value': output.schema,
                }
            # Use basic JSON mode
            return {'type': 'json'}
        return None

    async def generate(
        self,
        request: GenerateRequest,
        ctx: ActionRunContext | None = None,
    ) -> GenerateResponse:
        """Generate a response using the Hugging Face model.

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

        # Add provider if specified
        if self.provider:
            params['provider'] = self.provider

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
                if config.get('top_k') is not None:
                    params['top_k'] = config['top_k']
                if config.get('seed') is not None:
                    params['seed'] = config['seed']
                # Override provider from config if specified
                if config.get('provider') is not None:
                    params['provider'] = config['provider']

        # Handle streaming
        if ctx and ctx.send_chunk:
            return await self._generate_streaming(params, ctx)

        # Non-streaming request using chat_completion
        response = self.client.chat_completion(**params)

        # Extract content from response
        content: list[Part] = []
        if response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            if choice.message:
                # Handle text content
                if choice.message.content:
                    content.append(Part(root=TextPart(text=choice.message.content)))

                # Handle tool calls
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        args: dict[str, Any] | str = {}
                        if tool_call.function and tool_call.function.arguments:
                            try:
                                args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                args = tool_call.function.arguments

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

        # Build usage info
        usage = None
        if response.usage:
            usage = GenerationUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        return GenerateResponse(
            message=Message(role=Role.MODEL, content=content),
            finish_reason=FinishReason.STOP,
            usage=usage,
        )

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

        # Enable streaming
        params['stream'] = True

        for chunk in self.client.chat_completion(**params):
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]

                # Handle text content
                if choice.delta and choice.delta.content:
                    text = choice.delta.content
                    full_text += text

                    # Send chunk to client
                    ctx.send_chunk(
                        GenerateResponseChunk(
                            role=Role.MODEL,
                            content=[Part(root=TextPart(text=text))],
                        )
                    )

                # Handle tool calls in streaming
                if choice.delta and hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                    for tool_call in choice.delta.tool_calls:
                        idx = tool_call.index if hasattr(tool_call, 'index') else 0
                        if idx not in tool_calls:
                            tool_calls[idx] = {
                                'id': tool_call.id or '' if hasattr(tool_call, 'id') else '',
                                'name': (
                                    tool_call.function.name
                                    if hasattr(tool_call, 'function') and tool_call.function
                                    else ''
                                ),
                                'arguments': '',
                            }
                        # Accumulate arguments
                        if (
                            hasattr(tool_call, 'function')
                            and tool_call.function
                            and hasattr(tool_call.function, 'arguments')
                            and tool_call.function.arguments
                        ):
                            tool_calls[idx]['arguments'] += tool_call.function.arguments

                if choice.finish_reason:
                    # Map HF finish reason to Genkit FinishReason
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
        """Convert the HuggingFace model into a Genkit-compatible generate function.

        Returns:
            A callable function that can be used by Genkit.
        """
        return self.generate
