# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
Ollama Models for Genkit.
"""

import logging
from typing import Optional, List, Dict


from genkit.core.types import (
    GenerateRequest,
    GenerateResponse,
    TextPart,
    Message,
    Role,
)
from genkit.veneer import Genkit

from genkit.plugins.ollama.models import ModelDefinition, OllamaAPITypes

import ollama as ollama_api

LOG = logging.getLogger(__name__)


def register_ollama_model(
    ai: Genkit,
    model: ModelDefinition,
    client: ollama_api.Client,
) -> None:
    def _execute_ollama_request(request: GenerateRequest) -> GenerateResponse:
        def _chat_with_ollama() -> ollama_api.ChatResponse:
            ollama_messages: List[Dict[str, str]] = []

            for message in request.messages:
                item = {
                    'role': message.role.value,
                    'content': '',
                }
                for text_part in message.content:
                    if isinstance(text_part, TextPart):
                        item['content'] += text_part.text
                    else:
                        LOG.warning(f'Unsupported part of message: {text_part}')
                ollama_messages.append(item)
            return client.chat(model=model.name, messages=ollama_messages)

        def _generate_ollama_response() -> Optional[
            ollama_api.GenerateResponse
        ]:
            request_kwargs = {
                'model': model.name,
                'prompt': '',
            }
            for message in request.messages:
                for text_part in message.content:
                    if isinstance(text_part, TextPart):
                        request_kwargs['prompt'] += text_part.text
                    else:
                        LOG.error('Non-text messages are not supported')
            return client.generate(**request_kwargs)

        txt_response = 'Failed to get response from Ollama API'

        if model.api_type == OllamaAPITypes.CHAT:
            api_response = _chat_with_ollama()
            if api_response:
                txt_response = api_response.message.content
        else:
            api_response = _generate_ollama_response()
            if api_response:
                txt_response = api_response.response

        return GenerateResponse(
            message=Message(
                role=Role.model,
                content=[TextPart(text=txt_response)],
            )
        )

    ai.define_model(
        name=f'ollama/{model.name}',
        fn=_execute_ollama_request,
        metadata={
            'multiturn': model.api_type == OllamaAPITypes.CHAT,
            'system_role': True,
        },
    )
