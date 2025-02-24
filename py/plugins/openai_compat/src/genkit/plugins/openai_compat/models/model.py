# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI Models for Genkit.
"""

from typing import Any

from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.openai_compat.typing import (
    ChatCompletionRequest,
    ChatMessage,
)
from openai import OpenAI


class OpenAIModel:
    """
    Handles OpenAI API interactions for the Genkit plugin.
    """

    def __init__(self, model: str, client: OpenAI):
        """
        Initializes the OpenAIModel instance with the specified model and OpenAI client parameters.

        :param model: The OpenAI model to use for generating responses.
        :param client: OpenAI client instance.
        """
        self._model = model
        self._openai_client = client

    @property
    def name(self):
        return self._model

    def _build_messages(self, request: GenerateRequest) -> list[ChatMessage]:
        """
        Converts the request messages into the format required by OpenAI's API.

        :param request: The GenerateRequest object containing the user messages.
        :return: A list of dictionaries, where each dictionary represents a message
                 with 'role' and 'content' fields.
        :raises ValueError: If no messages are provided in the request.
        """
        if not request.messages:
            raise ValueError('No messages provided in the request.')
        return [
            ChatMessage(
                role=m.role.value,
                content=''.join(
                    part.root.text
                    for part in m.content
                    if part.root.text is not None
                ),
            )
            for m in request.messages
        ]

    def _get_request_data(
        self, request: GenerateRequest
    ) -> ChatCompletionRequest:
        """
        Constructs the request payload for OpenAI's chat completion API.

        :param request: The GenerateRequest object containing model input parameters.
        :return: A dictionary containing the request payload with model settings.
        """
        chat_completion_request = ChatCompletionRequest(
            model=self._model,
            messages=self._build_messages(request=request),
        )

        if isinstance(request.config, GenerationCommonConfig):
            if request.config.version:
                chat_completion_request.model = request.config.version
            if request.config.top_p:
                chat_completion_request.top_p = request.config.top_p
            if request.config.temperature:
                chat_completion_request.temperature = request.config.temperature
            if request.config.stop_sequences:
                chat_completion_request.stop = request.config.stop_sequences
            if request.config.max_output_tokens:
                chat_completion_request.max_tokens = (
                    request.config.max_output_tokens
                )

        return chat_completion_request

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Processes the request using OpenAI's chat completion API and returns the generated response.

        :param request: The GenerateRequest object containing the input text and configuration.
        :return: A GenerateResponse object containing the generated message.
        """
        response = self._openai_client.chat.completions.create(
            **self._get_request_data(request=request).model_dump()
        )

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=[
                    TextPart(text=choice.message.content)
                    for choice in response.choices
                ],
            )
        )
