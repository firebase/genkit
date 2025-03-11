# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import logging

from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.ollama.constants import (
    DEFAULT_OLLAMA_SERVER_URL,
    OllamaAPITypes,
)
from pydantic import BaseModel, Field, HttpUrl

import ollama as ollama_api

LOG = logging.getLogger(__name__)


class ModelDefinition(BaseModel):
    name: str
    api_type: OllamaAPITypes


class EmbeddingModelDefinition(BaseModel):
    name: str
    dimensions: int


class OllamaPluginParams(BaseModel):
    models: list[ModelDefinition] = Field(default_factory=list)
    embedders: list[EmbeddingModelDefinition] = Field(default_factory=list)
    server_address: HttpUrl = Field(default=HttpUrl(DEFAULT_OLLAMA_SERVER_URL))
    request_headers: dict[str, str] | None = None


class OllamaModel:
    def __init__(
        self, client: ollama_api.AsyncClient, model_definition: ModelDefinition
    ):
        self.client = client
        self.model_definition = model_definition

    async def generate(
        self, request: GenerateRequest, ctx: ActionRunContext | None = None
    ) -> GenerateResponse:
        txt_response = 'Failed to get response from Ollama API'

        if self.model_definition.api_type == OllamaAPITypes.CHAT:
            api_response = await self._chat_with_ollama(
                request=request, ctx=ctx
            )
            if api_response:
                txt_response = api_response.message.content
        elif self.model_definition.api_type == OllamaAPITypes.GENERATE:
            api_response = await self._generate_ollama_response(
                request=request, ctx=ctx
            )
            if api_response:
                txt_response = api_response.response
        else:
            LOG.error(f'Unresolved API type: {self.model_definition.api_type}')

        if self.is_streaming_request(ctx=ctx):
            txt_response = 'Response sent to Streaming API'

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=[TextPart(text=txt_response)],
            )
        )

    async def _chat_with_ollama(
        self, request: GenerateRequest, ctx: ActionRunContext | None = None
    ) -> ollama_api.ChatResponse | None:
        messages = self.build_chat_messages(request)
        streaming_request = self.is_streaming_request(ctx=ctx)

        chat_response = await self.client.chat(
            model=self.model_definition.name,
            messages=messages,
            options=self.build_request_options(config=request.config),
            stream=streaming_request,
        )

        if streaming_request:
            idx = 0
            async for chunk in chat_response:
                idx += 1
                role = (
                    Role.MODEL
                    if chunk.message.role == 'assistant'
                    else Role.TOOL
                )
                ctx.send_chunk(
                    chunk=GenerateResponseChunk(
                        role=role,
                        index=idx,
                        content=[TextPart(text=chunk.message.content)],
                    )
                )
        else:
            return chat_response

    async def _generate_ollama_response(
        self, request: GenerateRequest, ctx: ActionRunContext | None = None
    ) -> ollama_api.GenerateResponse | None:
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
    def build_request_options(
        config: GenerationCommonConfig,
    ) -> ollama_api.Options:
        if config:
            return ollama_api.Options(
                top_k=config.top_k,
                top_p=config.top_p,
                stop=config.stop_sequences,
                temperature=config.temperature,
                num_predict=config.max_output_tokens,
            )

    @staticmethod
    def build_prompt(request: GenerateRequest) -> str:
        prompt = ''
        for message in request.messages:
            for text_part in message.content:
                if isinstance(text_part.root, TextPart):
                    prompt += text_part.root.text
                else:
                    LOG.error('Non-text messages are not supported')
        return prompt

    @staticmethod
    def build_chat_messages(request: GenerateRequest) -> list[dict[str, str]]:
        messages = []
        for message in request.messages:
            item = {
                'role': message.role,
                'content': '',
            }
            for text_part in message.content:
                if isinstance(text_part.root, TextPart):
                    item['content'] += text_part.root.text
                else:
                    LOG.error(f'Unsupported part of message: {text_part}')
            messages.append(item)
        return messages

    @staticmethod
    def is_streaming_request(ctx: ActionRunContext | None) -> bool:
        return ctx and ctx.is_streaming
