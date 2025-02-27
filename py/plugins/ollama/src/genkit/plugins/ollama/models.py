# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import logging

from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.ollama.constants import (
    DEFAULT_OLLAMA_SERVER_URL,
    OllamaAPITypes,
)
from genkit.plugins.ollama.mixins import BaseOllamaModelMixin
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
    use_async_api: bool = Field(default=True)


class OllamaModel(BaseOllamaModelMixin):
    def __init__(
        self, client: ollama_api.Client, model_definition: ModelDefinition
    ):
        self.client = client
        self.model_definition = model_definition

    def generate(
        self, request: GenerateRequest, ctx: ActionRunContext | None
    ) -> GenerateResponse:
        txt_response = 'Failed to get response from Ollama API'

        if self.model_definition.api_type == OllamaAPITypes.CHAT:
            api_response = self._chat_with_ollama(request=request, ctx=ctx)
            if api_response:
                txt_response = api_response.message.content
        else:
            api_response = self._generate_ollama_response(
                request=request, ctx=ctx
            )
            if api_response:
                txt_response = api_response.response

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=[TextPart(text=txt_response)],
            )
        )

    def _chat_with_ollama(
        self, request: GenerateRequest, ctx: ActionRunContext | None = None
    ) -> ollama_api.ChatResponse | None:
        messages = self.build_chat_messages(request)
        streaming_request = self.is_streaming_request(ctx=ctx)

        chat_response = self.client.chat(
            model=self.model_definition.name,
            messages=messages,
            options=self.build_request_options(config=request.config),
            stream=streaming_request,
        )

        if streaming_request:
            for chunk in chat_response:
                ctx.send_chunk(chunk=chunk)
        else:
            return chat_response

    def _generate_ollama_response(
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

        generate_response = self.client.generate(**request_kwargs)

        if streaming_request:
            for chunk in generate_response:
                ctx.send_chunk(chunk=chunk)
        else:
            return generate_response


class AsyncOllamaModel(BaseOllamaModelMixin):
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
            async for chunk in chat_response:
                ctx.send_chunk(chunk=chunk)
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
            async for chunk in generate_response:
                ctx.send_chunk(chunk=chunk)
        else:
            return generate_response
