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

"""Microsoft Foundry model implementation for Genkit.

This module implements the model interface for Microsoft Foundry chat completions
using the OpenAI-compatible API.

See:
- Microsoft Foundry: https://ai.azure.com/
- Model Catalog: https://ai.azure.com/catalog/models
- SDK Overview: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview

Key features:
- Chat completions with GPT-4o, GPT-4, GPT-3.5, o1/o3/o4 series, GPT-5 series
- Claude, DeepSeek, Grok, Llama, Mistral models
- Tool/function calling support
- Streaming responses
- Multimodal inputs (images with visual_detail_level control)
- JSON output mode
"""

import json
from typing import Any

from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessage

from genkit.ai import ActionRunContext
from genkit.plugins.msfoundry.models.model_info import MODELS_SUPPORTING_RESPONSE_FORMAT, get_model_info
from genkit.plugins.msfoundry.typing import MSFoundryConfig, VisualDetailLevel
from genkit.types import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    GenerationUsage,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)

# Mapping from OpenAI finish reasons to Genkit finish reasons
FINISH_REASON_MAP: dict[str, FinishReason] = {
    'stop': FinishReason.STOP,
    'length': FinishReason.LENGTH,
    'tool_calls': FinishReason.STOP,
    'content_filter': FinishReason.BLOCKED,
    'function_call': FinishReason.STOP,
}


class MSFoundryModel:
    """Microsoft Foundry model for chat completions.

    This class handles the conversion between Genkit's message format
    and the Microsoft Foundry/Azure OpenAI chat completion API format.

    Attributes:
        model_name: The model name (e.g., 'gpt-4o', 'DeepSeek-V3.2').
        client: AsyncAzureOpenAI or AsyncOpenAI client instance.
        deployment: Optional deployment name override.
    """

    def __init__(
        self,
        model_name: str,
        client: AsyncAzureOpenAI | AsyncOpenAI,
        deployment: str | None = None,
    ) -> None:
        """Initialize the Microsoft Foundry model.

        Args:
            model_name: Name of the model (e.g., 'gpt-4o', 'DeepSeek-V3.2').
            client: AsyncAzureOpenAI or AsyncOpenAI client instance.
            deployment: Optional deployment name (defaults to model_name).
        """
        self.model_name = model_name
        self.client = client
        self.deployment = deployment or model_name

    async def generate(
        self,
        request: GenerateRequest,
        ctx: ActionRunContext | None = None,
    ) -> GenerateResponse:
        """Generate a response from Azure OpenAI.

        Args:
            request: The generation request containing messages and config.
            ctx: Action run context for streaming support.

        Returns:
            GenerateResponse with the model's output.
        """
        config = self._normalize_config(request.config)
        params = self._build_request_body(request, config)
        streaming = ctx is not None and ctx.is_streaming

        if streaming and ctx is not None:
            return await self._generate_streaming(params, ctx, request)

        # Non-streaming request
        response: ChatCompletion = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        message = choice.message

        # Convert response to Genkit format
        content = self._from_openai_message(message)
        response_message = Message(role=Role.MODEL, content=content)

        # Build usage statistics
        usage = GenerationUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )

        finish_reason = FINISH_REASON_MAP.get(choice.finish_reason or '', FinishReason.UNKNOWN)

        return GenerateResponse(
            message=response_message,
            usage=usage,
            finish_reason=finish_reason,
            request=request,
        )

    async def _generate_streaming(
        self,
        params: dict[str, Any],
        ctx: ActionRunContext,
        request: GenerateRequest,
    ) -> GenerateResponse:
        """Handle streaming generation.

        Args:
            params: Request parameters for the API.
            ctx: Action run context for sending chunks.
            request: Original generation request.

        Returns:
            Final GenerateResponse after streaming completes.
        """
        params['stream'] = True
        params['stream_options'] = {'include_usage': True}

        stream = await self.client.chat.completions.create(**params)

        accumulated_content: list[Part] = []
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        final_usage: GenerationUsage | None = None

        async for chunk in stream:
            chunk: ChatCompletionChunk
            if not chunk.choices:
                # May contain usage info at the end
                if chunk.usage:
                    final_usage = GenerationUsage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens,
                    )
                continue

            delta = chunk.choices[0].delta
            parts: list[Part] = []

            # Handle text content
            if delta.content:
                text_part = Part(root=TextPart(text=delta.content))
                parts.append(text_part)
                accumulated_content.append(text_part)

            # Handle tool calls (accumulated across chunks)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            'id': tc.id or '',
                            'name': tc.function.name if tc.function else '',
                            'arguments': '',
                        }
                    if tc.function and tc.function.arguments:
                        accumulated_tool_calls[idx]['arguments'] += tc.function.arguments

            # Send chunk to callback
            if parts:
                ctx.send_chunk(
                    GenerateResponseChunk(
                        role=Role.MODEL,
                        content=parts,
                        index=chunk.choices[0].index,
                    )
                )

        # Add accumulated tool calls to content
        for tc_data in accumulated_tool_calls.values():
            try:
                args = json.loads(tc_data['arguments']) if tc_data['arguments'] else {}
            except json.JSONDecodeError:
                args = tc_data['arguments']

            accumulated_content.append(
                Part(
                    root=ToolRequestPart(
                        tool_request=ToolRequest(
                            ref=tc_data['id'],
                            name=tc_data['name'],
                            input=args,
                        )
                    )
                )
            )

        return GenerateResponse(
            message=Message(role=Role.MODEL, content=accumulated_content),
            usage=final_usage,
            request=request,
        )

    def _normalize_config(self, config: object) -> MSFoundryConfig:
        """Normalize config to MSFoundryConfig.

        Args:
            config: Request configuration (dict, MSFoundryConfig, or GenerationCommonConfig).

        Returns:
            Normalized MSFoundryConfig instance.
        """
        if config is None:
            return MSFoundryConfig()

        if isinstance(config, MSFoundryConfig):
            return config

        if isinstance(config, GenerationCommonConfig):
            max_tokens = int(config.max_output_tokens) if config.max_output_tokens is not None else None
            return MSFoundryConfig(
                temperature=config.temperature,
                max_tokens=max_tokens,
                top_p=config.top_p,
                stop=config.stop_sequences,
            )

        if isinstance(config, dict):
            # Handle camelCase to snake_case mapping
            mapped: dict[str, Any] = {}
            key_map: dict[str, str] = {
                'maxOutputTokens': 'max_tokens',
                'maxTokens': 'max_tokens',
                'maxCompletionTokens': 'max_completion_tokens',
                'topP': 'top_p',
                'stopSequences': 'stop',
                'frequencyPenalty': 'frequency_penalty',
                'presencePenalty': 'presence_penalty',
                'logitBias': 'logit_bias',
                'logProbs': 'logprobs',
                'topLogProbs': 'top_logprobs',
                'visualDetailLevel': 'visual_detail_level',
                'reasoningEffort': 'reasoning_effort',
                'parallelToolCalls': 'parallel_tool_calls',
                'responseFormat': 'response_format',
            }
            for key, value in config.items():
                # Map camelCase keys to snake_case, or use key as-is
                str_key = str(key)
                mapped_key = key_map.get(str_key, str_key)
                mapped[mapped_key] = value
            return MSFoundryConfig(**mapped)

        return MSFoundryConfig()

    def _build_request_body(
        self,
        request: GenerateRequest,
        config: MSFoundryConfig,
    ) -> dict[str, Any]:
        """Build the Azure OpenAI API request body.

        This follows the same logic as `toOpenAiRequestBody` in the JS plugin.

        Args:
            request: The generation request.
            config: Normalized configuration.

        Returns:
            Dictionary suitable for chat.completions.create().
        """
        visual_detail = config.visual_detail_level or VisualDetailLevel.AUTO

        body: dict[str, Any] = {
            'model': config.model or self.deployment,
            'messages': self._to_openai_messages(request.messages, visual_detail),
        }

        # Add optional parameters
        # Use max_completion_tokens for o-series models, fall back to max_tokens
        if config.max_completion_tokens is not None:
            body['max_completion_tokens'] = config.max_completion_tokens
        elif config.max_tokens is not None:
            body['max_tokens'] = config.max_tokens
        if config.temperature is not None:
            body['temperature'] = config.temperature
        if config.top_p is not None:
            body['top_p'] = config.top_p
        if config.stop is not None:
            body['stop'] = config.stop
        if config.frequency_penalty is not None:
            body['frequency_penalty'] = config.frequency_penalty
        if config.presence_penalty is not None:
            body['presence_penalty'] = config.presence_penalty
        if config.logit_bias is not None:
            body['logit_bias'] = config.logit_bias
        if config.logprobs is not None:
            body['logprobs'] = config.logprobs
        if config.top_logprobs is not None:
            body['top_logprobs'] = config.top_logprobs
        if config.seed is not None:
            body['seed'] = config.seed
        if config.user is not None:
            body['user'] = config.user

        # Number of completions: prefer config.n, fall back to request.candidates
        if config.n is not None:
            body['n'] = config.n
        elif request.candidates:
            body['n'] = request.candidates

        # Output modalities (text, audio)
        if config.modalities is not None:
            body['modalities'] = config.modalities

        # Reasoning model parameters (o1, o3, o4 series)
        if config.reasoning_effort is not None:
            body['reasoning_effort'] = config.reasoning_effort
        if config.verbosity is not None:
            body['verbosity'] = config.verbosity

        # Handle tools
        if request.tools:
            body['tools'] = [self._to_openai_tool(t) for t in request.tools]
            if request.tool_choice:
                body['tool_choice'] = request.tool_choice
            # Allow explicit control over parallel tool calls (defaults to True in API)
            if config.parallel_tool_calls is not None:
                body['parallel_tool_calls'] = config.parallel_tool_calls

        # Handle response format (JSON mode / Structured Outputs)
        # Config response_format takes priority over request.output.format
        if config.response_format is not None:
            body['response_format'] = config.response_format
        elif request.output and request.output.format:
            model_name = config.model or self.model_name
            if model_name in MODELS_SUPPORTING_RESPONSE_FORMAT:
                model_info = get_model_info(model_name)
                output_modes = (model_info.supports.output or []) if model_info.supports else []

                if request.output.format == 'json' and 'json' in output_modes:
                    body['response_format'] = {'type': 'json_object'}
                elif request.output.format == 'text' and 'text' in output_modes:
                    body['response_format'] = {'type': 'text'}

        return body

    def _to_openai_tool(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert a Genkit tool definition to OpenAI format.

        Args:
            tool: Genkit ToolDefinition.

        Returns:
            OpenAI-compatible tool definition.
        """
        parameters = tool.input_schema or {}
        if parameters:
            parameters = {**parameters, 'type': 'object'}

        return {
            'type': 'function',
            'function': {
                'name': tool.name,
                'description': tool.description or '',
                'parameters': parameters,
            },
        }

    def _to_openai_messages(
        self,
        messages: list[Message],
        visual_detail_level: VisualDetailLevel = VisualDetailLevel.AUTO,
    ) -> list[dict[str, Any]]:
        """Convert Genkit messages to OpenAI chat message format.

        This follows the same logic as `toOpenAiMessages` in the JS plugin.

        Args:
            messages: List of Genkit messages.
            visual_detail_level: Detail level for image processing.

        Returns:
            List of OpenAI-compatible message dictionaries.
        """
        openai_msgs: list[dict[str, Any]] = []

        for msg in messages:
            role = self._to_openai_role(msg.role)

            if role == 'system':
                # System messages are text-only
                text_content = self._extract_text(msg)
                openai_msgs.append({'role': 'system', 'content': text_content})

            elif role == 'user':
                # User messages can be multimodal
                content_parts: list[dict[str, Any]] = []
                for part in msg.content:
                    root = part.root if isinstance(part, Part) else part
                    if isinstance(root, TextPart):
                        content_parts.append({'type': 'text', 'text': root.text})
                    elif isinstance(root, MediaPart):
                        content_parts.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': root.media.url,
                                'detail': visual_detail_level.value,
                            },
                        })
                openai_msgs.append({'role': 'user', 'content': content_parts})

            elif role == 'assistant':
                # Assistant messages may contain tool calls
                tool_calls = []
                text_parts = []

                for part in msg.content:
                    root = part.root if isinstance(part, Part) else part
                    if isinstance(root, TextPart):
                        text_parts.append(root.text)
                    elif isinstance(root, ToolRequestPart):
                        tool_calls.append({
                            'id': root.tool_request.ref or '',
                            'type': 'function',
                            'function': {
                                'name': root.tool_request.name,
                                'arguments': json.dumps(root.tool_request.input),
                            },
                        })

                if tool_calls:
                    openai_msgs.append({'role': 'assistant', 'tool_calls': tool_calls})
                else:
                    openai_msgs.append({'role': 'assistant', 'content': ''.join(text_parts)})

            elif role == 'tool':
                # Tool response messages
                for part in msg.content:
                    root = part.root if isinstance(part, Part) else part
                    if isinstance(root, ToolResponsePart):
                        output = root.tool_response.output
                        content = output if isinstance(output, str) else json.dumps(output)
                        openai_msgs.append({
                            'role': 'tool',
                            'tool_call_id': root.tool_response.ref or '',
                            'content': content,
                        })

        return openai_msgs

    def _to_openai_role(self, role: Role | str) -> str:
        """Convert Genkit role to OpenAI role.

        Args:
            role: Genkit message role (can be Role enum or string).

        Returns:
            OpenAI role string.
        """
        # Handle string roles directly
        if isinstance(role, str):
            str_role_map = {
                'user': 'user',
                'model': 'assistant',
                'system': 'system',
                'tool': 'tool',
            }
            return str_role_map.get(role.lower(), 'user')

        role_map = {
            Role.USER: 'user',
            Role.MODEL: 'assistant',
            Role.SYSTEM: 'system',
            Role.TOOL: 'tool',
        }
        return role_map.get(role, 'user')

    def _extract_text(self, msg: Message) -> str:
        """Extract text content from a message.

        Args:
            msg: Message to extract text from.

        Returns:
            Concatenated text content.
        """
        texts = []
        for part in msg.content:
            root = part.root if isinstance(part, Part) else part
            if isinstance(root, TextPart):
                texts.append(root.text)
        return ''.join(texts)

    def _from_openai_message(self, message: ChatCompletionMessage) -> list[Part]:
        """Convert OpenAI response message to Genkit parts.

        Args:
            message: OpenAI ChatCompletionMessage.

        Returns:
            List of Genkit Part objects.
        """
        parts: list[Part] = []

        # Handle text content
        if message.content:
            parts.append(Part(root=TextPart(text=message.content)))

        # Handle tool calls
        if message.tool_calls:
            for tc in message.tool_calls:
                # Skip tool calls without function attribute (custom tool calls)
                func = getattr(tc, 'function', None)
                if func is None:
                    continue

                # Parse arguments
                func_args = getattr(func, 'arguments', None)
                func_name = getattr(func, 'name', 'unknown')
                args: dict[str, Any] | str = {}
                if func_args:
                    try:
                        args = json.loads(func_args)
                    except json.JSONDecodeError:
                        args = func_args

                parts.append(
                    Part(
                        root=ToolRequestPart(
                            tool_request=ToolRequest(
                                ref=tc.id,
                                name=func_name,
                                input=args,
                            )
                        )
                    )
                )

        return parts
