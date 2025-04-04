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

from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field, HttpUrl

import ollama as ollama_api
from genkit.ai import ActionRunContext
from genkit.blocks.model import get_basic_usage_stats
from genkit.plugins.ollama.constants import (
    DEFAULT_OLLAMA_SERVER_URL,
    OllamaAPITypes,
)
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    GenerationUsage,
    Media,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)

logger = structlog.get_logger(__name__)


class ModelDefinition(BaseModel):
    name: str
    api_type: OllamaAPITypes = 'chat'


class EmbeddingModelDefinition(BaseModel):
    name: str
    dimensions: int


class OllamaPluginParams(BaseModel):
    models: list[ModelDefinition] = Field(default_factory=list)
    embedders: list[EmbeddingModelDefinition] = Field(default_factory=list)
    server_address: HttpUrl = Field(default=HttpUrl(DEFAULT_OLLAMA_SERVER_URL))
    request_headers: dict[str, str] | None = None


class OllamaModel:
    def __init__(self, client: ollama_api.AsyncClient, model_definition: ModelDefinition):
        self.client = client
        self.model_definition = model_definition

    async def generate(self, request: GenerateRequest, ctx: ActionRunContext | None = None) -> GenerateResponse:
        """Generate a response from Ollama.

        Args:
            request: The request to generate a response for.
            ctx: The context to generate a response for.

        Returns:
            The generated response.
        """
        content = [TextPart(text='Failed to get response from Ollama API')]

        if self.model_definition.api_type == OllamaAPITypes.CHAT:
            api_response = await self._chat_with_ollama(request=request, ctx=ctx)
            if api_response:
                content = self._build_multimodal_chat_response(
                    chat_response=api_response,
                )
        elif self.model_definition.api_type == OllamaAPITypes.GENERATE:
            api_response = await self._generate_ollama_response(request=request, ctx=ctx)
            if api_response:
                content = [TextPart(text=api_response.response)]
        else:
            raise ValueError(f'Unresolved API type: {self.model_definition.api_type}')

        if self.is_streaming_request(ctx=ctx):
            content = []

        response_message = Message(
            role=Role.MODEL,
            content=content,
        )

        basic_generation_usage = get_basic_usage_stats(
            input_=request.messages,
            response=response_message,
        )

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=content,
            ),
            usage=self.get_usage_info(
                basic_generation_usage=basic_generation_usage,
                api_response=api_response,
            ),
        )

    # FIXME: Missing return statement.
    async def _chat_with_ollama(
        self, request: GenerateRequest, ctx: ActionRunContext | None = None
    ) -> ollama_api.ChatResponse | None:
        """Chat with Ollama.

        Args:
            request: The request to chat with Ollama for.
            ctx: The context to chat with Ollama for.

        Returns:
            The chat response from Ollama.
        """
        messages = self.build_chat_messages(request)
        streaming_request = self.is_streaming_request(ctx=ctx)

        if request.output:
            # ollama api either accepts 'json' literal, or the JSON schema
            if request.output.schema_:
                fmt = request.output.schema_
            elif request.output.format:
                fmt = request.output.format
            else:
                fmt = ''
        else:
            fmt = ''

        chat_response = await self.client.chat(
            model=self.model_definition.name,
            messages=messages,
            tools=[
                ollama_api.Tool(
                    function=ollama_api.Tool.Function(
                        name=tool.name,
                        description=tool.description,
                        parameters=_convert_parameters(tool.input_schema),
                    )
                )
                for tool in request.tools or []
            ],
            options=self.build_request_options(config=request.config),
            format=fmt,
            stream=streaming_request,
        )

        if streaming_request:
            idx = 0
            async for chunk in chat_response:
                idx += 1
                role = Role.MODEL if chunk.message.role == 'assistant' else Role.TOOL
                ctx.send_chunk(
                    chunk=GenerateResponseChunk(
                        role=role,
                        index=idx,
                        content=self._build_multimodal_chat_response(chat_response=chunk),
                    )
                )
        else:
            return chat_response

    async def _generate_ollama_response(
        self, request: GenerateRequest, ctx: ActionRunContext | None = None
    ) -> ollama_api.GenerateResponse | None:
        """Generate a response from Ollama.

        Args:
            request: The request to generate a response for.
            ctx: The context to generate a response for.

        Returns:
            The generated response.
        """
        # FIXME: Missing return statement.
        prompt = self.build_prompt(request)
        streaming_request = self.is_streaming_request(ctx=ctx)

        request_kwargs = {
            'model': self.model_definition.name,
            'prompt': prompt,
            'options': self.build_request_options(config=request.config),
            'stream': streaming_request,
        }

        generate_response = await self.client.generate(**request_kwargs)

        if streaming_request:
            idx = 0
            async for chunk in generate_response:
                idx += 1
                ctx.send_chunk(
                    chunk=GenerateResponseChunk(
                        role=Role.MODEL,
                        index=idx,
                        content=[TextPart(text=chunk.response)],
                    )
                )
        else:
            return generate_response

    @staticmethod
    def _build_multimodal_chat_response(
        chat_response: ollama_api.ChatResponse,
    ) -> list[Part]:
        """Build the multimodal chat response.

        Args:
            chat_response: The chat response to build the multimodal response for.

        Returns:
            The multimodal chat response.
        """
        content = []
        chat_response_message = chat_response.message
        if chat_response_message.content:
            content.append(TextPart(text=chat_response.message.content))
        if chat_response_message.images:
            for image in chat_response_message.images:
                content.append(
                    MediaPart(
                        media=Media(
                            content_type=mimetypes.guess_type(image.value, strict=False)[0],
                            url=image.value,
                        )
                    )
                )
        if chat_response_message.tool_calls:
            for tool_call in chat_response_message.tool_calls:
                content.append(
                    ToolRequestPart(
                        tool_request=ToolRequest(
                            name=tool_call.function.name,
                            input=tool_call.function.arguments,
                        )
                    )
                )
        return content

    @staticmethod
    def build_request_options(
        config: GenerationCommonConfig | dict,
    ) -> ollama_api.Options:
        """Build request options for the generate API.

        Args:
            config: The configuration to build the request options for.

        Returns:
            The request options for the generate API.
        """
        if isinstance(config, GenerationCommonConfig):
            config = dict(
                top_k=config.top_k,
                top_p=config.top_p,
                stop=config.stop_sequences,
                temperature=config.temperature,
                num_predict=config.max_output_tokens,
            )
        if config:
            return ollama_api.Options(**config)

    @staticmethod
    def build_prompt(request: GenerateRequest) -> str:
        """Build the prompt for the generate API.

        Args:
            request: The request to build the prompt for.

        Returns:
            The prompt for the generate API.
        """
        prompt = ''
        for message in request.messages:
            for text_part in message.content:
                if isinstance(text_part.root, TextPart):
                    prompt += text_part.root.text
                else:
                    logger.error('Non-text messages are not supported')
        return prompt

    @classmethod
    def build_chat_messages(cls, request: GenerateRequest) -> list[dict[str, str]]:
        """Build the messages for the chat API.

        Args:
            request: The request to build the messages for.

        Returns:
            The messages for the chat API.
        """
        messages = []
        for message in request.messages:
            item = ollama_api.Message(
                role=cls._to_ollama_role(role=message.role),
                content='',
                images=[],
            )
            for text_part in message.content:
                if isinstance(text_part.root, TextPart):
                    item.content += text_part.root.text
                if isinstance(text_part.root, ToolResponsePart):
                    item.content += str(text_part.root.tool_response.output)
                if isinstance(text_part.root, MediaPart):
                    item['images'].append(
                        ollama_api.Image(
                            value=text_part.root.media.url,
                        )
                    )
            messages.append(item)
        return messages

    @staticmethod
    def _to_ollama_role(
        role: Role,
    ) -> Literal['user', 'assistant', 'system', 'tool']:
        match role:
            case Role.USER:
                return 'user'
            case Role.MODEL:
                return 'assistant'
            case Role.TOOL:
                return 'tool'
            case Role.SYSTEM:
                return 'system'
            case _:
                raise ValueError(f'Unknown role: {role}')

    @staticmethod
    def is_streaming_request(ctx: ActionRunContext | None) -> bool:
        return ctx and ctx.is_streaming

    @staticmethod
    def get_usage_info(
        basic_generation_usage: GenerationUsage,
        api_response: ollama_api.GenerateResponse | ollama_api.ChatResponse,
    ) -> GenerationUsage:
        if api_response:
            basic_generation_usage.input_tokens = api_response.prompt_eval_count or 0
            basic_generation_usage.output_tokens = api_response.eval_count or 0
            basic_generation_usage.total_tokens = (
                basic_generation_usage.input_tokens + basic_generation_usage.output_tokens
            )
        return basic_generation_usage


def _convert_parameters(input_schema: dict[str, Any]) -> ollama_api.Tool.Function.Parameters | None:
    """Sanitizes a schema to be compatible with Ollama API."""
    if not input_schema or 'type' not in input_schema:
        return None

    schema = ollama_api.Tool.Function.Parameters()
    if 'required' in input_schema:
        schema.required = input_schema['required']

    if 'type' in input_schema:
        schema_type = input_schema['type']
        schema.type = schema_type

        if schema_type == 'object':
            schema.properties = {}
            properties = input_schema['properties']
            for key in properties:
                schema.properties[key] = ollama_api.Tool.Function.Parameters.Property(
                    type=properties[key]['type'], description=properties[key]['description'] or ''
                )

    return schema
