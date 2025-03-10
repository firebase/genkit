# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI Compatible Models for Genkit.
"""

from collections.abc import Callable

from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.compat_oai.typing import ChatMessage
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

    def _get_messages(self, messages: list[Message]) -> list[ChatMessage]:
        """
        Converts the request messages into the format required by OpenAI's API.

        :param request: A list of the user messages.
        :return: A list of dictionaries, where each dictionary represents a message
                 with 'role' and 'content' fields.
        :raises ValueError: If no messages are provided in the request.
        """
        if not messages:
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
            for m in messages
        ]

    def _get_openai_config(self, request: GenerateRequest) -> dict:
        openai_config = {
            'messages': self._get_messages(request.messages),
            'model': self._model,
        }
        if request.config:
            openai_config.update(**request.config.model_dump())
        return openai_config

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Processes the request using OpenAI's chat completion API and returns the generated response.

        :param request: The GenerateRequest object containing the input text and configuration.
        :return: A GenerateResponse object containing the generated message.
        """
        response = self._openai_client.chat.completions.create(
            **self._get_openai_config(request=request)
        )

        return GenerateResponse(
            request=request,
            message=Message(
                role=Role.MODEL,
                content=[TextPart(text=response.choices[0].message.content)],
            ),
        )

    def generate_stream(
        self, request: GenerateRequest, callback: Callable
    ) -> GenerateResponse:
        """
        Generates a streaming response from the OpenAI client and processes it in chunks.

        Args:
            request (GenerateRequest): The request object containing generation parameters.
            callback (Callable): A function to handle each chunk of the streamed response.

        Returns:
            GenerateResponse: An empty response message when streaming is complete.
        """
        openai_config = self._get_openai_config(request=request)
        openai_config['stream'] = True

        stream = self._openai_client.chat.completions.create(**openai_config)

        for chunk in stream:
            choice = chunk.choices[0]
            if not choice.delta.content:
                continue

            response_chunk = GenerateResponseChunk(
                role=Role.MODEL,
                index=choice.index,
                content=[TextPart(text=choice.delta.content)],
            )

            callback(response_chunk)

        # Return an empty response when streaming is complete
        return GenerateResponse(
            request=request,
            message=Message(role=Role.MODEL, content=[TextPart(text='')]),
        )
