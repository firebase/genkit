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

"""Anthropic model implementations."""

from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message as AnthropicMessage
from genkit.ai import ActionRunContext
from genkit.blocks.model import get_basic_usage_stats
from genkit.plugins.anthropic.model_info import get_model_info
from genkit.types import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)

DEFAULT_MAX_OUTPUT_TOKENS = 4096


class AnthropicModel:
    """Represents an Anthropic language model for use with Genkit.

    Encapsulates interaction logic for a specific Claude model
    enabling its use within Genkit for generative tasks.
    """

    def __init__(self, model_name: str, client: AsyncAnthropic) -> None:
        """Initialize Anthropic model.

        Sets up the client for communicating with the Anthropic API
        and stores the model name.

        Args:
            model_name: Name of the Anthropic model.
            client: AsyncAnthropic client instance.
        """
        model_info = get_model_info(model_name)
        self.model_name = model_info.versions[0] if model_info.versions else model_name
        self.client = client

    async def generate(self, request: GenerateRequest, ctx: ActionRunContext | None = None) -> GenerateResponse:
        """Generate response from Anthropic.

        Args:
            request: Generation request.
            ctx: Action run context for streaming.

        Returns:
            Generated response.
        """
        params = self._build_params(request)
        streaming = ctx and ctx.is_streaming

        if streaming:
            assert ctx is not None  # streaming requires ctx
            response = await self._generate_streaming(params, ctx)
        else:
            response = await self.client.messages.create(**params)

        content = self._to_genkit_content(response.content)

        response_message = Message(role=Role.MODEL, content=content)
        basic_usage = get_basic_usage_stats(input_=request.messages, response=response_message)

        finish_reason_map: dict[str, FinishReason] = {
            'end_turn': FinishReason.STOP,
            'max_tokens': FinishReason.LENGTH,
            'stop_sequence': FinishReason.STOP,
            'tool_use': FinishReason.STOP,
        }
        stop_reason_str = str(response.stop_reason) if response.stop_reason else ''
        finish_reason = finish_reason_map.get(stop_reason_str, FinishReason.UNKNOWN)

        return GenerateResponse(
            message=response_message,
            usage=GenerationUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                input_characters=basic_usage.input_characters,
                output_characters=basic_usage.output_characters,
                input_images=basic_usage.input_images,
                output_images=basic_usage.output_images,
            ),
            finish_reason=finish_reason,
        )

    def _build_params(self, request: GenerateRequest) -> dict[str, Any]:
        """Build Anthropic API parameters."""
        config = request.config
        params: dict[str, Any] = {}

        if isinstance(config, dict):
            params = config.copy()
        elif config:
            if hasattr(config, 'model_dump'):
                params = config.model_dump(exclude_none=True)
            else:
                params = {k: v for k, v in vars(config).items() if v is not None}

        # Handle mapped parameters
        max_tokens = params.pop('max_output_tokens', None)
        if max_tokens is None:
            max_tokens = params.get('max_tokens', DEFAULT_MAX_OUTPUT_TOKENS)

        params.get('temperature')
        params.get('top_p')
        params.get('stop_sequences')
        thinking = params.pop('thinking', None)
        metadata = params.pop('metadata', None)

        # Standard mapped fields are already in params if they share names (temperature, top_p, stop_sequences)
        # But we ensure they are set correctly if valid
        # Actually, if they are in params, they are good.
        # We just need to handle renaming/logic.

        params['model'] = self.model_name
        params['messages'] = self._to_anthropic_messages(request.messages)
        params['max_tokens'] = int(max_tokens)

        # Remove known genkit keys that don't map directly or are handled
        params.pop('version', None)  # If version was passed through config

        if thinking:
            if isinstance(thinking, dict):
                anthropic_thinking: dict[str, str | int] = {}
                # Handle boolean enabled -> type="enabled"
                if thinking.get('enabled') is True or thinking.get('type') == 'enabled':
                    anthropic_thinking['type'] = 'enabled'

                # Handle camelCase -> snake_case for budget tokens
                tokens = thinking.get('budgetTokens', thinking.get('budget_tokens'))
                if tokens:
                    anthropic_thinking['budget_tokens'] = int(tokens)

                if anthropic_thinking.get('type') == 'enabled':
                    params['thinking'] = anthropic_thinking
                    # Anthropic requires temperature to be None/excluded if thinking is enabled?
                    # Actually standard behavior is: if thinking, extended thinking model rules apply.
                    # We pass it if valid.

        if metadata:
            params['metadata'] = metadata

        system = self._extract_system(request.messages)
        if system:
            params['system'] = system

        if request.tools:
            params['tools'] = [
                {
                    'name': t.name,
                    'description': t.description,
                    'input_schema': t.input_schema,
                }
                for t in request.tools
            ]

            if request.tool_choice:
                if request.tool_choice == 'required':
                    params['tool_choice'] = {'type': 'any'}
                elif request.tool_choice == 'auto':
                    params['tool_choice'] = {'type': 'auto'}
                elif isinstance(request.tool_choice, dict):
                    params['tool_choice'] = request.tool_choice

        return params

    async def _generate_streaming(self, params: dict[str, Any], ctx: ActionRunContext) -> AnthropicMessage:
        """Handle streaming generation."""
        async with self.client.messages.stream(**params) as stream:
            async for chunk in stream:
                if chunk.type == 'content_block_delta' and hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                    ctx.send_chunk(
                        GenerateResponseChunk(
                            role=Role.MODEL,
                            index=0,
                            content=[Part(root=TextPart(text=str(chunk.delta.text)))],
                        )
                    )
            return await stream.get_final_message()

    def _extract_system(self, messages: list[Message]) -> str | None:
        """Extract system prompt from messages."""
        for msg in messages:
            if msg.role == Role.SYSTEM:
                texts = []
                for part in msg.content:
                    actual_part = part.root if isinstance(part, Part) else part
                    if isinstance(actual_part, TextPart):
                        texts.append(actual_part.text)
                return ''.join(texts) if texts else None
        return None

    def _to_anthropic_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Genkit messages to Anthropic format."""
        result = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue
            role = 'assistant' if msg.role == Role.MODEL else 'user'
            content: list[dict[str, Any]] = []
            for part in msg.content:
                actual_part = part.root if isinstance(part, Part) else part
                if isinstance(actual_part, TextPart):
                    content.append({'type': 'text', 'text': actual_part.text})
                elif isinstance(actual_part, MediaPart):
                    content.append(self._to_anthropic_media(actual_part))
                elif isinstance(actual_part, ToolRequestPart):
                    content.append({
                        'type': 'tool_use',
                        'id': actual_part.tool_request.ref,
                        'name': actual_part.tool_request.name,
                        'input': actual_part.tool_request.input,
                    })
                elif isinstance(actual_part, ToolResponsePart):
                    content.append({
                        'type': 'tool_result',
                        'tool_use_id': actual_part.tool_response.ref,
                        'content': str(actual_part.tool_response.output),
                    })
            result.append({'role': role, 'content': content})
        return result

    def _to_anthropic_media(self, media_part: MediaPart) -> dict[str, Any]:
        """Convert media part to Anthropic format."""
        url = media_part.media.url
        if url.startswith('data:'):
            _, base64_data = url.split(',', 1)
            content_type = url.split(':')[1].split(';')[0]
            return {
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': content_type,
                    'data': base64_data,
                },
            }
        return {'type': 'image', 'source': {'type': 'url', 'url': url}}

    def _to_genkit_content(self, content_blocks: list[Any]) -> list[Part]:
        """Convert Anthropic response to Genkit format."""
        parts = []
        for block in content_blocks:
            if block.type == 'text':
                parts.append(Part(root=TextPart(text=block.text)))
            elif block.type == 'tool_use':
                parts.append(
                    Part(
                        root=ToolRequestPart(
                            tool_request=ToolRequest(
                                ref=block.id,
                                name=block.name,
                                input=block.input,
                            )
                        )
                    )
                )
        return parts
