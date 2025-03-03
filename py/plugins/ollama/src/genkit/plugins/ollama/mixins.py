# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import logging

from genkit.core.action import ActionRunContext, noop_streaming_callback

# Common helpers extracted into a base class or module
from genkit.core.typing import GenerateRequest, GenerationCommonConfig, TextPart

import ollama as ollama_api

LOG = logging.getLogger(__name__)


class BaseOllamaModelMixin:
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
                'role': message.role.value,
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
