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
from typing import Any, cast

from openai import OpenAI
from openai.lib._pydantic import _ensure_strict_json_schema

from genkit.core.action._action import ActionRunContext
from genkit.plugins.compat_oai.models.model_info import SUPPORTED_OPENAI_MODELS
from genkit.plugins.compat_oai.models.utils import DictMessageAdapter, MessageAdapter, MessageConverter
from genkit.plugins.compat_oai.typing import OpenAIConfig, SupportedOutputFormat
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    OutputConfig,
    Part,
    Role,
    ToolDefinition,
)


class OpenAIModel:
    """Handles OpenAI API interactions for the Genkit plugin."""

    def __init__(self, model: str, client: OpenAI) -> None:
        """Initializes the OpenAIModel instance with the specified model and OpenAI client parameters.

        Args:
            model: The OpenAI model to use for generating responses.
            client: OpenAI client instance.
        """
        self._model = model
        self._openai_client = client

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

    async def _get_tools_definition(self, tools: list[ToolDefinition]) -> list[dict]:
        """Converts the provided tools into OpenAI-compatible function call format.

        Args:
            tools: A list of tool definitions.

        Returns:
            A list of dictionaries representing the formatted tools.
        """
        result = []
        for tool_definition in tools:
            # Get the schema and ensure it has additionalProperties: false for strict mode
            parameters = tool_definition.input_schema or {}
            if parameters and 'additionalProperties' not in parameters:
                parameters = {**parameters, 'additionalProperties': False}

            # Construct the OpenAI function tool format using the schema from tool_definition
            function_call = {
                'type': 'function',
                'function': {
                    'name': tool_definition.name,
                    'description': tool_definition.description or '',
                    'parameters': parameters,
                    'strict': True,
                },
            }
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
            # Special handling for DeepSeek models: always use 'json_object' for structured output
            if self._model.startswith('deepseek'):
                return {'type': 'json_object'}
            if output.schema:
                return {
                    'type': 'json_schema',
                    'json_schema': {
                        'name': output.schema.get('title', 'Response'),
                        'schema': _ensure_strict_json_schema(output.schema, path=(), root=output.schema),
                        'strict': True,
                    },
                }

            model = SUPPORTED_OPENAI_MODELS[self._model]
            if model.supports and model.supports.output and SupportedOutputFormat.JSON_MODE in model.supports.output:
                return {'type': 'json_object'}

        return {'type': 'text'}

    async def _get_openai_request_config(self, request: GenerateRequest) -> dict:
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
            openai_config['tools'] = await self._get_tools_definition(request.tools)
        if any(msg.role == Role.TOOL for msg in request.messages):
            # After a tool response, stop forcing additional tool calls.
            openai_config['tool_choice'] = 'none'
        elif request.tool_choice:
            openai_config['tool_choice'] = request.tool_choice
        if request.output:
            response_format = self._get_response_format(request.output)
            if response_format:
                # pyrefly: ignore[bad-typed-dict-key] - response_format dict is valid for OpenAI API
                openai_config['response_format'] = response_format
        if request.config:
            openai_config.update(**request.config.model_dump(exclude_none=True))
        return openai_config

    async def _generate(self, request: GenerateRequest) -> GenerateResponse:
        """Processes the request using OpenAI's chat completion API and returns the generated response.

        Args:
            request: The GenerateRequest object containing the input text and configuration.

        Returns:
            A GenerateResponse object containing the generated message.
        """
        openai_config = await self._get_openai_request_config(request=request)
        response = self._openai_client.chat.completions.create(**openai_config)

        return GenerateResponse(
            request=request,
            message=MessageConverter.to_genkit(response.choices[0].message),
        )

    async def _generate_stream(
        self, request: GenerateRequest, callback: Callable[[GenerateResponseChunk], None]
    ) -> GenerateResponse:
        """Streams responses from the OpenAI client and sends chunks to a callback.

        Args:
            request: The GenerateRequest object containing generation parameters.
            callback: A function to receive streamed GenerateResponseChunk objects.

        Returns:
            GenerateResponse: A final message with accumulated content after streaming is complete.
        """
        openai_config = await self._get_openai_request_config(request=request)
        openai_config['stream'] = True

        stream = self._openai_client.chat.completions.create(**openai_config)

        tool_calls: dict[int, Any] = {}
        accumulated_content: list[Part] = []
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
                    if tool_call.index not in tool_calls:
                        tool_calls[tool_call.index] = tool_call
                    else:
                        existing = tool_calls[tool_call.index]
                        if hasattr(existing, 'function') and existing.function and tool_call.function:
                            existing.function.arguments += tool_call.function.arguments
                content = [
                    MessageConverter.tool_call_to_genkit(
                        tool_calls[tool_call.index],
                        args_segment=tool_call.function.arguments if tool_call.function else None,
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

    async def generate(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Processes the request using OpenAI's chat completion API.

        Args:
            request: The request containing messages and configurations.
            ctx: The context of the action run.

        Returns:
            A GenerateResponse containing the model's response.
        """
        request.config = self.normalize_config(request.config)

        if ctx.is_streaming:
            return await self._generate_stream(request, ctx.send_chunk)
        else:
            return await self._generate(request)

    @staticmethod
    def normalize_config(config: object) -> OpenAIConfig:
        """Ensures the config is an OpenAIConfig instance."""
        if isinstance(config, OpenAIConfig):
            return config

        if isinstance(config, GenerationCommonConfig):
            return OpenAIConfig(
                temperature=config.temperature,
                max_tokens=int(config.max_output_tokens) if config.max_output_tokens is not None else None,
                top_p=config.top_p,
                stop=config.stop_sequences,
            )

        if isinstance(config, dict):
            config_dict = cast(dict[str, Any], config)
            if config_dict.get('topK'):
                del config_dict['topK']
            if config_dict.get('topP'):
                config_dict['top_p'] = config_dict['topP']
                del config_dict['topP']
            return OpenAIConfig(**config_dict)

        raise ValueError(f'Expected request.config to be a dict or OpenAIConfig, got {type(config).__name__}.')
