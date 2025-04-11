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

"""OpenAI Compatible Models for Genkit."""

from collections.abc import Callable

from openai import OpenAI, pydantic_function_tool
from openai.lib._pydantic import _ensure_strict_json_schema

from genkit.ai import ActionKind, GenkitRegistry
from genkit.plugins.compat_oai.models.model_info import SUPPORTED_OPENAI_MODELS
from genkit.plugins.compat_oai.models.utils import DictMessageAdapter, MessageAdapter, MessageConverter
from genkit.plugins.compat_oai.typing import SupportedOutputFormat
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    OutputConfig,
    Role,
    ToolDefinition,
)


class OpenAIModel:
    """Handles OpenAI API interactions for the Genkit plugin."""

    def __init__(self, model: str, client: OpenAI, registry: GenkitRegistry):
        """Initializes the OpenAIModel instance with the specified model and OpenAI client parameters.

        Args:
            model: The OpenAI model to use for generating responses.
            client: OpenAI client instance.
            registry: The registry where OpenAI models will be registered.
        """
        self._model = model
        self._openai_client = client
        self._registry = registry

    @property
    def name(self) -> str:
        """The name of the OpenAI model."""
        return self._model

    def _get_messages(self, messages: list[Message]) -> list[dict]:
        """Converts the request messages into the format required by OpenAI's API.

        Args:
            messages: A list of the user messages.

        Returns:
            A list of dictionaries, where each dictionary represents a message
            with 'role' and 'content' fields.

        Raises:
            ValueError: If no messages are provided in the request.
        """
        openai_messages = []
        for message in messages:
            openai_messages.extend(MessageConverter.to_openai(message=message))
        return openai_messages

    def _get_tools_definition(self, tools: list[ToolDefinition]) -> list[dict]:
        """Converts the provided tools into OpenAI-compatible function call format.

        Args:
            tools: A list of tool definitions.

        Returns:
            A list of dictionaries representing the formatted tools.
        """
        result = []
        for tool_definition in tools:
            action = self._registry.registry.lookup_action(ActionKind.TOOL, tool_definition.name)
            function_call = pydantic_function_tool(
                model=action.input_type._type,
                name=tool_definition.name,
                description=tool_definition.description,
            )
            result.append(function_call)
        return result

    def _get_response_format(self, output: OutputConfig) -> dict | None:
        """Determines the response format configuration based on the output settings.

        Args:
            output: The output configuration specifying the desired format and optional schema.

        Returns:
            A dictionary representing the response format, which may include:
            - 'type': 'json_schema' and a validated JSON Schema if a schema is provided.
            - 'type': 'json_object' if the model supports JSON mode and no schema is provided.
            - 'type': 'text' as the default fallback.
        """
        if output.format == 'json':
            if output.schema_:
                return {
                    'type': 'json_schema',
                    'json_schema': {
                        'name': output.schema_.get('title', 'Response'),
                        'schema': _ensure_strict_json_schema(output.schema_, path=(), root=output.schema_),
                        'strict': True,
                    },
                }

            model = SUPPORTED_OPENAI_MODELS[self._model]
            if SupportedOutputFormat.JSON_MODE in model.supports.output:
                return {'type': 'json_object'}

        return {'type': 'text'}

    def _get_openai_request_config(self, request: GenerateRequest) -> dict:
        """Get the OpenAI request configuration.

        Args:
            request: The request containing messages and configurations.

        Returns:
            A dictionary representing the OpenAI request configuration.
        """
        openai_config = {
            'messages': self._get_messages(request.messages),
            'model': self._model,
        }
        if request.tools:
            openai_config['tools'] = self._get_tools_definition(request.tools)
        if request.output:
            openai_config['response_format'] = self._get_response_format(request.output)
        if request.config:
            openai_config.update(**request.config.model_dump(exclude_none=True))
        return openai_config

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Processes the request using OpenAI's chat completion API and returns the generated response.

        Args:
            request: The GenerateRequest object containing the input text and configuration.

        Returns:
            A GenerateResponse object containing the generated message.
        """
        response = self._openai_client.chat.completions.create(**self._get_openai_request_config(request=request))

        return GenerateResponse(
            request=request,
            message=MessageConverter.to_genkit(response.choices[0].message),
        )

    def generate_stream(self, request: GenerateRequest, callback: Callable) -> GenerateResponse:
        """Streams responses from the OpenAI client and sends chunks to a callback.

        Args:
            request: The GenerateRequest object containing generation parameters.
            callback: A function to receive streamed GenerateResponseChunk objects.

        Returns:
            GenerateResponse: A final message with accumulated content after streaming is complete.
        """
        openai_config = self._get_openai_request_config(request=request)
        openai_config['stream'] = True

        stream = self._openai_client.chat.completions.create(**openai_config)

        tool_calls = {}
        accumulated_content = []
        for chunk in stream:
            delta = chunk.choices[0].delta

            # Text content chunk
            if delta.content:
                message = MessageConverter.to_genkit(MessageAdapter(delta))
                accumulated_content.extend(message.content)
                callback(
                    GenerateResponseChunk(
                        role=Role.MODEL,
                        content=message.content,
                    )
                )

            # Tool call chunk (partial function call)
            elif delta.tool_calls:
                for tool_call in delta.tool_calls:
                    # Accumulate fragmented tool call arguments
                    tool_calls.setdefault(tool_call.index, tool_call).function.arguments += tool_call.function.arguments
                content = [
                    MessageConverter.tool_call_to_genkit(
                        tool_calls[tool_call.index], args_segment=tool_call.function.arguments
                    )
                    for tool_call in delta.tool_calls
                ]
                callback(GenerateResponseChunk(role=Role.MODEL, content=content))

        if tool_calls:
            message = MessageConverter.to_genkit(
                DictMessageAdapter({'tool_calls': tool_calls.values(), 'role': Role.MODEL})
            )
            accumulated_content.extend(message.content)

        return GenerateResponse(
            request=request,
            message=Message(role=Role.MODEL, content=accumulated_content),
        )
