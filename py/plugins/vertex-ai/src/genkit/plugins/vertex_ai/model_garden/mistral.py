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

"""Mistral Models for VertexAI Model Garden."""

import json
from typing import Any, cast

from genkit.core.action import Action
from genkit.core.action.types import ActionKind
from genkit.plugins.compat_oai.typing import SupportedOutputFormat
from genkit.types import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    GenerationCommonConfig,
    GenerationUsage,
    Message,
    ModelInfo,
    Part,
    Role,
    Supports,
    Supports,
    TextPart,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)
from mistralai_gcp import MistralGoogleCloud
from mistralai_gcp.models import (
    AssistantMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Function,
    FunctionCall,
    SystemMessage,
    Tool,
    ToolCall,
    ToolMessage,
    UserMessage,
)

SUPPORTED_MISTRAL_MODELS: dict[str, ModelInfo] = {
    'mistral-medium-3': ModelInfo(
        label='ModelGarden - Mistral - Medium',
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
    'mistral-ocr-2505': ModelInfo(
        label='ModelGarden - Mistral - OCR',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
    'mistral-small-2503': ModelInfo(
        label='ModelGarden - Mistral - Small',
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
    'codestral-2': ModelInfo(
        label='ModelGarden - Mistral - Codestral',
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
            output=[SupportedOutputFormat.TEXT],
        ),
    ),
}


class MistralModel:
    """Mistral Model Garden implementation."""

    def __init__(self, client: MistralGoogleCloud, model_name: str):
        self.client = client
        self.model_name = model_name

    async def generate(
        self,
        request: GenerateRequest,
        streaming_callback: Any | None = None,
    ) -> GenerateResponse:
        """Generate response from Mistral model."""
        mistral_request = self._to_mistral_request(request)

        if streaming_callback:
            stream_response = await self.client.chat.stream_async(
                model=self.model_name,
                messages=mistral_request.messages,
                tools=mistral_request.tools,
                temperature=mistral_request.temperature,
                top_p=mistral_request.top_p,
                max_tokens=mistral_request.max_tokens,
            )
            # Cast stream to AsyncIterator to satisfy type checker
            from typing import AsyncIterable
            assert isinstance(stream_response, AsyncIterable)
            async for chunk in stream_response:
                data = chunk.data
                parts = self._from_mistral_completion_chunk(data)
                if parts:
                    streaming_callback(
                        GenerateResponse(
                            message=Message(role=Role.MODEL, content=parts)
                        )
                    )
            
            response = await self.client.chat.complete_async(
                model=self.model_name,
                messages=mistral_request.messages,
                tools=mistral_request.tools,
                temperature=mistral_request.temperature,
                top_p=mistral_request.top_p,
                max_tokens=mistral_request.max_tokens,
            )
            if response is None:
                raise ValueError("Mistral response is None")
            return self._from_mistral_response(request, response)

        response = await self.client.chat.complete_async(
            model=self.model_name,
            messages=mistral_request.messages,
            tools=mistral_request.tools,
            temperature=mistral_request.temperature,
            top_p=mistral_request.top_p,
            max_tokens=mistral_request.max_tokens,
        )
        if response is None:
            raise ValueError("Mistral response is None")
        return self._from_mistral_response(request, response)

    def _to_mistral_request(
        self, request: GenerateRequest
    ) -> ChatCompletionRequest:
        messages = []
        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                content = ''.join(p.root.text for p in msg.content if isinstance(p.root, TextPart))
                messages.append(SystemMessage(content=content))
            elif msg.role == Role.USER:
                content = ''.join(p.root.text for p in msg.content if isinstance(p.root, TextPart))
                messages.append(UserMessage(content=content))
            elif msg.role == Role.MODEL:
                # Handle assistant messages (text + tool calls)
                content = ''.join(p.root.text for p in msg.content if isinstance(p.root, TextPart))
                tool_calls = []
                for part in msg.content:
                    if isinstance(part.root, ToolRequestPart):
                        tool_request = part.root.tool_request
                        tool_calls.append(
                            ToolCall(
                                id=tool_request.ref or '',
                                function=FunctionCall(
                                    name=tool_request.name,
                                    arguments=json.dumps(tool_request.input) if isinstance(tool_request.input, (dict, list)) else str(tool_request.input),
                                ),
                            )
                        )
                messages.append(
                    AssistantMessage(content=content, tool_calls=tool_calls or None)
                )
            elif msg.role == Role.TOOL:
                for part in msg.content:
                    if isinstance(part.root, ToolResponsePart):
                        tool_response = part.root.tool_response
                        messages.append(
                            ToolMessage(
                                content=json.dumps(tool_response.output),
                                tool_call_id=tool_response.ref,
                                name=tool_response.name,
                            )
                        )

        tools = None
        if request.tools:
            tools = [
                Tool(
                    function=Function(
                        name=t.name,
                        description=t.description,
                        parameters=t.input_schema or {},
                    )
                )
                for t in request.tools
            ]

        # Use request.config attributes which are optional but typed
        max_tokens = request.config.max_output_tokens if request.config else None
        temperature = request.config.temperature if request.config else None
        top_p = request.config.top_p if request.config else None

        return ChatCompletionRequest(
            model=self.model_name,
            messages=messages,
            tools=tools,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

    def _from_mistral_response(
        self, request: GenerateRequest, response: ChatCompletionResponse
    ) -> GenerateResponse:
        if not response.choices:
            raise ValueError("Mistral response contains no choices")
        choice = response.choices[0]
        message = choice.message
        content_parts = []

        if message.content:
             # handle list or string content
            if isinstance(message.content, str):
                content_parts.append(Part(root=TextPart(text=message.content)))
            elif isinstance(message.content, list):
                 for chunk in message.content:
                     if hasattr(chunk, 'text') and isinstance(chunk.text, str):
                         content_parts.append(Part(root=TextPart(text=chunk.text)))

        if message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                   try:
                       tool_input = json.loads(args)
                   except json.JSONDecodeError:
                       tool_input = args
                else:
                   tool_input = args

                content_parts.append(
                    Part(
                        root=ToolRequestPart(
                            toolRequest=ToolRequest(
                                ref=tc.id,
                                name=tc.function.name,
                                input=tool_input,
                            )
                        )
                    )
                )

        finish_reason = FinishReason.UNKNOWN
        if choice.finish_reason == 'stop':
            finish_reason = FinishReason.STOP
        elif choice.finish_reason == 'length':
            finish_reason = FinishReason.LENGTH
        elif choice.finish_reason == 'tool_calls':
            finish_reason = FinishReason.STOP

        return GenerateResponse(
            message=Message(role=Role.MODEL, content=content_parts),
            finishReason=cast(FinishReason, finish_reason),
            usage=GenerationUsage(
                inputTokens=response.usage.prompt_tokens,
                outputTokens=response.usage.completion_tokens,
                totalTokens=response.usage.total_tokens,
            ),
        )
    
    def _from_mistral_completion_chunk(self, chunk: Any) -> list[Part]:
        # Helper to convert streaming chunk to parts
        parts = []
        delta = chunk.choices[0].delta
        if delta.content:
             if isinstance(delta.content, str):
                parts.append(Part(root=TextPart(text=delta.content)))
        # Note: Tool calls in streaming are complex to reconstruct from raw chunks 
        # without stateful accumulation. For now, we rely on the final complete call
        # for robust tool handling, matching JS strategy partially (JS sends chunks but refetches full).
        return parts

