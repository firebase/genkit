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

from enum import StrEnum
from functools import cached_property
from typing import Any

import google.genai.types as genai_types
from google import genai

from genkit.ai.registry import GenkitRegistry
from genkit.core.action import ActionKind, ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    ModelInfo,
    Role,
    Supports,
    TextPart,
    ToolDefinition,
)
from genkit.plugins.google_genai.models.utils import PartConverter

gemini10Pro = ModelInfo(
    label='Google AI - Gemini Pro',
    versions=['gemini-pro', 'gemini-1.0-pro-latest', 'gemini-1.0-pro-001'],
    supports=Supports(
        multiturn=True,
        media=False,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


gemini15Pro = ModelInfo(
    label='Google AI - Gemini 1.5 Pro',
    versions=[
        'gemini-1.5-pro-latest',
        'gemini-1.5-pro-001',
        'gemini-1.5-pro-002',
    ],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


gemini15Flash = ModelInfo(
    label='Google AI - Gemini 1.5 Flash',
    versions=[
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash-001',
        'gemini-1.5-flash-002',
    ],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


gemini15Flash8b = ModelInfo(
    label='Google AI - Gemini 1.5 Flash',
    versions=['gemini-1.5-flash-8b-latest', 'gemini-1.5-flash-8b-001'],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


gemini20Flash = ModelInfo(
    label='Google AI - Gemini 2.0 Flash',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


gemini20ProExp0205 = ModelInfo(
    label='Google AI - Gemini 2.0 Pro Exp 02-05',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

gemini20FlashExpImaGen = ModelInfo(
    label='Google AI - Gemini 2.0 Flash Experimental',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


class GeminiVersion(StrEnum):
    GEMINI_1_0_PRO = 'gemini-1.0-pro'
    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'


class GeminiApiOnlyVersion(StrEnum):
    GEMINI_2_0_FLASH_EXP = 'gemini-2.0-flash-exp'


SUPPORTED_MODELS = {
    GeminiVersion.GEMINI_1_0_PRO: gemini10Pro,
    GeminiVersion.GEMINI_1_5_PRO: gemini15Pro,
    GeminiVersion.GEMINI_1_5_FLASH: gemini15Flash,
    GeminiVersion.GEMINI_1_5_FLASH_8B: gemini15Flash8b,
    GeminiVersion.GEMINI_2_0_FLASH: gemini20Flash,
    GeminiVersion.GEMINI_2_0_PRO_EXP_02_05: gemini20ProExp0205,
    GeminiApiOnlyVersion.GEMINI_2_0_FLASH_EXP: gemini20FlashExpImaGen,
}


class GeminiModel:
    def __init__(
        self,
        version: str | GeminiVersion | GeminiApiOnlyVersion,
        client: genai.Client,
        registry: GenkitRegistry,
    ):
        self._version = version
        self._client = client
        self._registry = registry

    def _create_vertexai_tool(self, tool: ToolDefinition) -> genai.types.Tool:
        """Create a tool that is compatible with VertexAI API.

        Args:
            - tool: Genkit Tool Definition

        Returns:
            Genai tool compatible with VertexAI API.
        """
        function = genai.types.FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema,
            response=tool.output_schema,
        )
        return genai.types.Tool(function_declarations=[function])

    def _create_gemini_tool(self, tool: ToolDefinition) -> genai.types.Tool:
        """Create a tool that is compatible with Gemini API.

        Args:
            - tool: Genkit Tool Definition

        Returns:
            Genai tool compatible with Gemini API.
        """
        params = self._convert_schema_property(tool.input_schema)
        function = genai.types.FunctionDeclaration(
            name=tool.name, description=tool.description, parameters=params
        )
        return genai.types.Tool(function_declarations=[function])

    def _get_tools(self, request: GenerateRequest) -> list[genai.types.Tool]:
        """Generates VertexAI Gemini compatible tool definitions.

        Args:
            request: The generation request.

         Returns:
             list of Gemini tools
        """
        tools = []
        for tool in request.tools:
            genai_tool = (
                self._create_vertexai_tool(tool)
                if self._client.vertexai
                else self._create_gemini_tool(tool)
            )
            tools.append(genai_tool)

        return tools

    def _convert_schema_property(
        self, input_schema: dict[str, Any]
    ) -> genai.types.Schema | None:
        """Sanitizes a schema to be compatible with Gemini API.

        Args:
            input_schema: a dictionary with input parameters

        Returns:
            Schema or None
        """
        if not input_schema or 'type' not in input_schema:
            return None

        schema = genai.types.Schema()
        if input_schema.get('description'):
            schema.description = input_schema['description']

        if 'type' in input_schema:
            schema_type = genai.types.Type(input_schema['type'])
            schema.type = schema_type

            if schema_type == genai.types.Type.ARRAY:
                schema.items = input_schema['items']

            if schema_type == genai.types.Type.OBJECT:
                schema.properties = {}
                properties = input_schema['properties']
                for key in properties:
                    nested_schema = self._convert_schema_property(
                        properties[key]
                    )
                    schema.properties[key] = nested_schema

        return schema

    def _call_tool(self, call: genai.types.FunctionCall) -> genai.types.Content:
        """Calls tool's function from the registry.

        Args:
            call: FunctionCall from Gemini response

        Returns:
            Gemini message content to add to the message
        """
        tool_function = self._registry.registry.lookup_action(
            ActionKind.TOOL, call.name
        )
        args = tool_function.input_type.validate_python(call.args)
        tool_answer = tool_function.run(args)
        return genai.types.Content(
            parts=[
                genai.types.Part.from_function_response(
                    name=call.name,
                    response={
                        'content': tool_answer.response,
                    },
                )
            ]
        )

    async def generate(
        self, request: GenerateRequest, ctx: ActionRunContext
    ) -> GenerateResponse:
        """Handle a generation request.

        Args:
            request: The generation request containing messages and parameters.
            ctx: action context

        Returns:
            The model's response to the generation request.
        """

        request_contents = self._build_messages(request)

        request_cfg = self._genkit_to_googleai_cfg(request)

        if ctx.is_streaming:
            return await self._streaming_generate(
                request_contents, request_cfg, ctx
            )
        else:
            return await self._generate(request_contents, request_cfg)

    async def _generate(
        self,
        request_contents: list[genai.types.Content],
        request_cfg: genai.types.GenerateContentConfig,
    ) -> GenerateResponse:
        """Call google-genai generate

        Args:
            request_contents: request contents
            request_cfg: request configuration

        Returns:
            genai response
        """

        response = await self._client.aio.models.generate_content(
            model=self._version, contents=request_contents, config=request_cfg
        )

        content = self._contents_from_response(response)

        return GenerateResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            )
        )

    async def _streaming_generate(
        self,
        request_contents: list[genai.types.Content],
        request_cfg: genai.types.GenerateContentConfig | None,
        ctx: ActionRunContext,
    ) -> GenerateResponse:
        """Call google-genai generate for streaming

        Args:
            request_contents: request contents
            request_cfg: request configuration
            ctx:

        Returns:
            empty genai response
        """

        async for (
            response_chunk
        ) in await self._client.aio.models.generate_content_stream(
            model=self._version, contents=request_contents, config=request_cfg
        ):
            content = self._contents_from_response(response_chunk)

            ctx.send_chunk(
                chunk=GenerateResponseChunk(
                    content=content,
                    role=Role.MODEL,
                )
            )
        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=[TextPart(text='')],
            )
        )

    @cached_property
    def metadata(self) -> dict:
        """Get model metadata

        Returns:
            model metadata
        """
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }

    def is_multimode(self):
        return SUPPORTED_MODELS[self._version].supports.media

    def _build_messages(
        self, request: GenerateRequest
    ) -> list[genai.types.Content]:
        """Build google-genai request contents from Genkit request

        Args:
            request: Genkit request

        Returns:
            list of google-genai contents
        """
        request_contents: list[genai.types.Content] = []

        for msg in request.messages:
            content_parts: list[genai.types.Part] = []
            for p in msg.content:
                content_parts.append(PartConverter.to_gemini(p))
            request_contents.append(
                genai.types.Content(parts=content_parts, role=msg.role)
            )

        return request_contents

    def _contents_from_response(
        self, response: genai.types.GenerateContentResponse
    ) -> list:
        """Retrieve contents from google-genai response

        Args:
            response: google-genai response

        Returns:
            list of generated contents
        """

        content = []
        if response.candidates:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    content.append(PartConverter.from_gemini(part=part))

        return content

    def _genkit_to_googleai_cfg(
        self, request: GenerateRequest
    ) -> genai.types.GenerateContentConfig | None:
        """Translate GenerationCommonConfig to Google Ai GenerateContentConfig

        Args:
            request: Genkit request

        Returns:
            Google Ai request config or None
        """
        cfg = None

        if request.config:
            request_config = request.config
            if isinstance(request_config, GenerationCommonConfig):
                cfg = genai.types.GenerateContentConfig(
                    max_output_tokens=request_config.max_output_tokens,
                    top_k=request_config.top_k,
                    top_p=request_config.top_p,
                    temperature=request_config.temperature,
                    stop_sequences=request_config.stop_sequences,
                )
            elif isinstance(request_config, dict):
                cfg = genai.types.GenerateContentConfig(**request_config)

        if request.output:
            if not cfg:
                cfg = genai.types.GenerateContentConfig()

            response_mime_type = (
                'application/json'
                if request.output.format == 'json' and not request.tools
                else None
            )
            cfg.response_mime_type = response_mime_type

        if request.tools:
            if not cfg:
                cfg = genai.types.GenerateContentConfig()

            tools = self._get_tools(request)
            cfg.tools = tools

        return cfg
