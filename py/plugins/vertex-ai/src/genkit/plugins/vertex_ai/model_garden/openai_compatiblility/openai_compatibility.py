# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pdb
from enum import StrEnum
from genkit.core.typing import (
    ModelInfo,
    Supports,
    GenerationCommonConfig,
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
    GenerateResponseChunk
)
from genkit.core.action import ActionRunContext
from openai import OpenAI as OpenAIClient
from google.auth import default, transport
from typing import Annotated

from pydantic import BaseModel, ConfigDict

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    role: str
    content: str


class OpenAIConfig(GenerationCommonConfig):
    """Config for OpenAI model."""
    frequency_penalty: Annotated[float, range(-2, 2)] | None = None
    logit_bias: dict[str, Annotated[float, range(-100, 100)]] | None = None
    logprobs: bool | None = None
    presence_penalty: Annotated[float, range(-2, 2)] | None = None
    seed: int | None = None
    top_logprobs: Annotated[int, range(0, 20)] | None = None
    user: str | None = None


class ChatCompletionRole(StrEnum):
    """Available roles supported by openai-compatible models."""
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'
    TOOL = 'tool'


class OpenAICompatibleModel:
    "Handles openai compatible model support in model_garden"""

    def __init__(self, model: str, project_id: str, location: str):
        self._model = model
        self._client = self.client_factory(location, project_id)

    def client_factory(self, location: str, project_id: str) -> OpenAIClient:
        """Initiates an openai compatible client object and return it."""
        if project_id:
            credentials, _ = default()
        else:
            credentials, project_id = default()

        credentials.refresh(transport.requests.Request())
        base_url = f'https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/endpoints/openapi'
        return OpenAIClient(api_key=credentials.token, base_url=base_url)


    def to_openai_messages(self, messages: list[Message]) -> list[ChatMessage]:
        if not messages:
            raise ValueError('No messages provided in the request.')
        return [
            ChatMessage(
                role=OpenAICompatibleModel.to_openai_role(m.role.value),
                content=''.join(
                    part.root.text
                    for part in m.content
                    if part.root.text is not None
                ),
            )
            for m in messages
        ]
    def generate(
        self, request: GenerateRequest, ctx: ActionRunContext
    ) -> GenerateResponse:
        openai_config: dict = {
            'messages': self.to_openai_messages(request.messages),
            'model': self._model
        }
        if ctx.is_streaming:
            openai_config['stream'] = True
            stream = self._client.chat.completions.create(**openai_config)
            for chunk in stream:
                choice = chunk.choices[0]
                if not choice.delta.content:
                    continue

                response_chunk = GenerateResponseChunk(
                    role=Role.MODEL,
                    index=choice.index,
                    content=[TextPart(text=choice.delta.content)],
                )

                ctx.send_chunk(response_chunk)

        else:
            response = self._client.chat.completions.create(**openai_config)
            return GenerateResponse(
                request=request,
                message=Message(
                role=Role.MODEL,
                content=[TextPart(text=response.choices[0].message.content)],
            ),
        )

    @staticmethod
    def to_openai_role(role: Role) -> ChatCompletionRole:
        """Converts Role enum to corrosponding OpenAI Compatible role."""
        match role:
            case Role.USER:
                return ChatCompletionRole.USER
            case Role.MODEL:
                return ChatCompletionRole.ASSISTANT  # "model" maps to "assistant"
            case Role.SYSTEM:
                return ChatCompletionRole.SYSTEM
            case Role.TOOL:
                return ChatCompletionRole.TOOL
            case _:
                raise ValueError(f"Role '{role}' doesn't map to an OpenAI role.")
