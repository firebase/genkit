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

"""xAI model implementations."""

import asyncio
import json
from typing import Any

from xai_sdk import Client as XAIClient
from xai_sdk.proto.v6 import chat_pb2

from genkit.ai import ActionRunContext
from genkit.blocks.model import get_basic_usage_stats
from genkit.core.schema import to_json_schema
from genkit.plugins.xai.model_info import get_model_info
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
    ToolRequestPart,
    ToolResponsePart,
)

__all__ = ['XAIModel']

DEFAULT_MAX_OUTPUT_TOKENS = 4096

FINISH_REASON_MAP = {
    'STOP': 'stop',
    'LENGTH': 'length',
    'TOOL_CALLS': 'stop',
    'CONTENT_FILTER': 'other',
}

ROLE_MAP = {
    Role.SYSTEM: chat_pb2.MessageRole.ROLE_SYSTEM,
    Role.USER: chat_pb2.MessageRole.ROLE_USER,
    Role.MODEL: chat_pb2.MessageRole.ROLE_ASSISTANT,
    Role.TOOL: chat_pb2.MessageRole.ROLE_TOOL,
}


class XAIModel:
    """xAI Grok model for Genkit."""

    def __init__(self, model_name: str, client: XAIClient) -> None:
        model_info = get_model_info(model_name)
        self.model_name = model_info.versions[0] if model_info.versions else model_name
        self.client = client

    async def generate(self, request: GenerateRequest, ctx: ActionRunContext | None = None) -> GenerateResponse:
        params = self._build_params(request)
        streaming = ctx and ctx.is_streaming

        if streaming:
            return await self._generate_streaming(params, request, ctx)

        def _sample():
            chat = self.client.chat.create(**params)
            return chat.sample()

        response = await asyncio.to_thread(_sample)
        content = self._to_genkit_content(response)
        response_message = Message(role=Role.MODEL, content=content)
        basic_usage = get_basic_usage_stats(input_=request.messages, response=response_message)

        return GenerateResponse(
            message=response_message,
            usage=GenerationUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                input_characters=basic_usage.input_characters,
                output_characters=basic_usage.output_characters,
                input_images=basic_usage.input_images,
                output_images=basic_usage.output_images,
            ),
            finish_reason=FINISH_REASON_MAP.get(response.finish_reason, 'unknown'),
        )

    def _build_params(self, request: GenerateRequest) -> dict[str, Any]:
        """Build xAI API parameters from request."""
        config = request.config
        if isinstance(config, dict):
            max_tokens = config.get('max_output_tokens') or DEFAULT_MAX_OUTPUT_TOKENS
            temperature = config.get('temperature')
            top_p = config.get('top_p')
            stop = config.get('stop_sequences')
            frequency_penalty = config.get('frequency_penalty')
            presence_penalty = config.get('presence_penalty')
            web_search_options = config.get('web_search_options')
            deferred = config.get('deferred')
            reasoning_effort = config.get('reasoning_effort')
        else:
            max_tokens = (config.max_output_tokens if config else None) or DEFAULT_MAX_OUTPUT_TOKENS
            temperature = getattr(config, 'temperature', None) if config else None
            top_p = getattr(config, 'top_p', None) if config else None
            stop = getattr(config, 'stop_sequences', None) if config else None
            frequency_penalty = getattr(config, 'frequency_penalty', None) if config else None
            presence_penalty = getattr(config, 'presence_penalty', None) if config else None
            web_search_options = getattr(config, 'web_search_options', None) if config else None
            deferred = getattr(config, 'deferred', None) if config else None
            reasoning_effort = getattr(config, 'reasoning_effort', None) if config else None

        params: dict[str, Any] = {
            'model': self.model_name,
            'messages': self._to_xai_messages(request.messages),
            'max_tokens': int(max_tokens),
        }

        if temperature is not None:
            params['temperature'] = temperature
        if top_p is not None:
            params['top_p'] = top_p
        if stop:
            params['stop'] = stop
        if frequency_penalty is not None:
            params['frequency_penalty'] = frequency_penalty
        if presence_penalty is not None:
            params['presence_penalty'] = presence_penalty
        if web_search_options is not None:
            params['web_search_options'] = web_search_options
        if deferred is not None:
            params['deferred'] = deferred
        if reasoning_effort is not None:
            params['reasoning_effort'] = reasoning_effort

        if request.tools:
            params['tools'] = [
                chat_pb2.Tool(
                    function=chat_pb2.Function(
                        name=t.name,
                        description=t.description or '',
                        parameters=json.dumps(to_json_schema(t.input_schema)),
                    ),
                )
                for t in request.tools
            ]

        return params

    async def _generate_streaming(
        self, params: dict[str, Any], request: GenerateRequest, ctx: ActionRunContext
    ) -> GenerateResponse:
        def _sync_stream():
            accumulated_content = []
            final_response = None

            chat = self.client.chat.create(**params)
            for response, chunk in chat.stream():
                final_response = response

                if chunk.content:
                    ctx.send_chunk(
                        GenerateResponseChunk(
                            role=Role.MODEL,
                            index=0,
                            content=[Part(root=TextPart(text=chunk.content))],
                        )
                    )
                    accumulated_content.append(Part(root=TextPart(text=chunk.content)))

                for choice in chunk.choices:
                    if choice.tool_calls:
                        for tool_call in choice.tool_calls:
                            if tool_call.function:
                                tool_input = tool_call.function.arguments
                                if isinstance(tool_input, str):
                                    try:
                                        tool_input = json.loads(tool_input)
                                    except (json.JSONDecodeError, TypeError):
                                        pass

                                accumulated_content.append(
                                    ToolRequestPart(
                                        tool_request={
                                            'ref': tool_call.id,
                                            'name': tool_call.function.name,
                                            'input': tool_input,
                                        }
                                    )
                                )

            response_message = Message(role=Role.MODEL, content=accumulated_content)
            basic_usage = get_basic_usage_stats(input_=request.messages, response=response_message)

            finish_reason = (
                FINISH_REASON_MAP.get(final_response.finish_reason, 'unknown') if final_response else 'unknown'
            )

            return GenerateResponse(
                message=response_message,
                usage=GenerationUsage(
                    input_tokens=final_response.usage.prompt_tokens if final_response else 0,
                    output_tokens=final_response.usage.completion_tokens if final_response else 0,
                    total_tokens=final_response.usage.total_tokens if final_response else 0,
                    input_characters=basic_usage.input_characters,
                    output_characters=basic_usage.output_characters,
                    input_images=basic_usage.input_images,
                    output_images=basic_usage.output_images,
                ),
                finish_reason=finish_reason,
            )

        return await asyncio.to_thread(_sync_stream)

    def _to_xai_messages(self, messages: list[Message]) -> list[chat_pb2.Message]:
        result = []

        for msg in messages:
            role = ROLE_MAP.get(msg.role, chat_pb2.MessageRole.ROLE_USER)
            content = []
            tool_calls = []

            for part in msg.content:
                actual_part = part.root if isinstance(part, Part) else part

                if isinstance(actual_part, TextPart):
                    content.append(chat_pb2.Content(text=actual_part.text))
                elif isinstance(actual_part, MediaPart):
                    if not actual_part.media.url:
                        raise ValueError('xAI models require a URL for media parts.')
                    content.append(chat_pb2.Content(image_url=chat_pb2.ImageURL(url=actual_part.media.url)))
                elif isinstance(actual_part, ToolRequestPart):
                    tool_calls.append(
                        chat_pb2.ToolCall(
                            id=actual_part.tool_request.ref,
                            type=chat_pb2.ToolCallType.FUNCTION,
                            function=chat_pb2.Function(
                                name=actual_part.tool_request.name,
                                arguments=actual_part.tool_request.input,
                            ),
                        )
                    )
                elif isinstance(actual_part, ToolResponsePart):
                    result.append(
                        chat_pb2.Message(
                            role=chat_pb2.MessageRole.ROLE_TOOL,
                            tool_call_id=actual_part.tool_response.ref,
                            content=[chat_pb2.Content(text=str(actual_part.tool_response.output))],
                        )
                    )
                    continue

            pb_message = chat_pb2.Message(role=role, content=content)
            if tool_calls:
                pb_message.tool_calls.extend(tool_calls)

            result.append(pb_message)

        return result

    def _to_genkit_content(self, response) -> list[Part]:
        content = []

        if response.content:
            content.append(Part(root=TextPart(text=response.content)))

        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_input = tool_call.function.arguments
                if isinstance(tool_input, str):
                    try:
                        tool_input = json.loads(tool_input)
                    except (json.JSONDecodeError, TypeError):
                        pass

                content.append(
                    Part(
                        root=ToolRequestPart(
                            tool_request={
                                'ref': tool_call.id,
                                'name': tool_call.function.name,
                                'input': tool_input,
                            }
                        )
                    )
                )

        return content
