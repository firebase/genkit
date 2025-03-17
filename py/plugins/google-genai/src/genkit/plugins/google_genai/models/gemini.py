# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from functools import cached_property
from typing import Any

import google.genai.types as genai_types
from google import genai

from genkit.core.action import ActionKind, ActionRunContext
from genkit.core.typing import (
    CustomPart,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Media,
    MediaPart,
    Message,
    ModelInfo,
    Part,
    Role,
    Supports,
    TextPart,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)
from genkit.veneer.registry import GenkitRegistry

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


class GeminiVersion(StrEnum):
    GEMINI_1_0_PRO = 'gemini-1.0-pro'
    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'


SUPPORTED_MODELS = {
    GeminiVersion.GEMINI_1_0_PRO: gemini10Pro,
    GeminiVersion.GEMINI_1_5_PRO: gemini15Pro,
    GeminiVersion.GEMINI_1_5_FLASH: gemini15Flash,
    GeminiVersion.GEMINI_1_5_FLASH_8B: gemini15Flash8b,
    GeminiVersion.GEMINI_2_0_FLASH: gemini20Flash,
    GeminiVersion.GEMINI_2_0_PRO_EXP_02_05: gemini20ProExp0205,
}


class PartConverter:
    EXECUTABLE_CODE = 'executableCode'
    CODE_EXECUTION_RESULT = 'codeExecutionResult'
    OUTCOME = 'outcome'
    OUTPUT = 'output'
    LANGUAGE = 'language'
    CODE = 'code'
    DATA = 'data:'
    BASE64 = ':base64,'

    @classmethod
    def to_gemini(cls, part: Part) -> genai.types.Part:
        if isinstance(part.root, TextPart):
            return genai.types.Part(text=part.root.text)
        if isinstance(part.root, ToolRequestPart):
            return genai.types.Part(
                function_call=genai.types.FunctionCall(
                    name=part.root.tool_request.name,
                    args=part.root.tool_request.args,
                )
            )
        if isinstance(part.root, ToolResponsePart):
            return genai.types.Part(
                function_response=genai.types.FunctionResponse(
                    name=part.root.tool_request.name,
                    response=part.root.tool_request.output,
                )
            )
        if isinstance(part.root, MediaPart):
            url = part.root.media.url
            return genai.types.Part(
                inline_data=genai.types.Blob(
                    data=url[
                        url.find(cls.DATA) + len(cls.DATA) : url.find(
                            cls.BASE64
                        )
                    ],
                    mime_type=part.root.media.content_type,
                )
            )
        if isinstance(part.root, CustomPart):
            return cls._to_gemini_custom(part)

    @classmethod
    def _to_gemini_custom(cls, part: Part) -> genai.types.Part:
        if cls.EXECUTABLE_CODE in part.root.custom:
            return genai.types.Part(
                executable_code=genai.types.ExecutableCode(
                    code=part.root.custom[cls.EXECUTABLE_CODE][cls.CODE],
                    language=part.root.custom[cls.EXECUTABLE_CODE][
                        cls.LANGUAGE
                    ],
                )
            )
        if cls.CODE_EXECUTION_RESULT in part.root.custom:
            return genai.types.Part(
                code_execution_result=genai.types.CodeExecutionResult(
                    outcome=part.root.custom[cls.CODE_EXECUTION_RESULT][
                        cls.OUTCOME
                    ],
                    output=part.root.custom[cls.CODE_EXECUTION_RESULT][
                        cls.OUTPUT
                    ],
                )
            )

    @classmethod
    def from_gemini(cls, part: genai.types.Part) -> Part:
        if part.text:
            return TextPart(text=part.text)
        if part.function_call:
            return ToolRequestPart(
                toolRequest=ToolRequest(
                    name=part.function_call.name, args=part.function_call.args
                )
            )
        if part.function_response:
            return ToolResponsePart(
                toolResponse=ToolResponse(
                    name=part.function_response.name,
                    output=part.function_response.response,
                )
            )
        if part.inline_data:
            return MediaPart(
                media=Media(
                    url=f'{cls.DATA}{part.inline_data.mime_type}{cls.BASE64}{part.inline_data.data}',
                    contentType=part.inline_data.mime_type,
                )
            )
        if part.executable_code:
            return {
                cls.EXECUTABLE_CODE: {
                    cls.LANGUAGE: part.executable_code.language,
                    cls.CODE: part.executable_code.code,
                }
            }
        if part.code_execution_result:
            return {
                cls.CODE_EXECUTION_RESULT: {
                    cls.OUTCOME: part.code_execution_result.outcome,
                    cls.OUTPUT: part.code_execution_result.output,
                }
            }


class GeminiModel:
    def __init__(
        self,
        version: str | GeminiVersion,
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

        request_cfg = (
            self._genkit_to_googleai_cfg(request.config)
            if request.config
            else None
        )
        if request.tools:
            tools = self._get_tools(request)
            request_cfg = {} if not request_cfg else request_cfg
            request_cfg['tools'] = tools

            nn_tool_choice = await self._client.aio.models.generate_content(
                model=self._version,
                contents=request_contents,
                config=request_cfg,
            )

            if nn_tool_choice.function_calls:
                for i in range(len(nn_tool_choice.function_calls)):
                    request_contents.append(
                        nn_tool_choice.candidates[i].content
                    )
                    request_contents.append(
                        self._call_tool(nn_tool_choice.function_calls[i])
                    )

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
        request_cfg: genai.types.GenerateContentConfig,
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
        self, genkit_cfg: GenerationCommonConfig
    ) -> genai.types.GenerateContentConfig:
        """Translate GenerationCommonConfig to Google Ai GenerateContentConfig

        Args:
            genkit_cfg: Genkit request config

        Returns:
            Google Ai request config
        """

        return genai.types.GenerateContentConfig(
            max_output_tokens=genkit_cfg.max_output_tokens,
            top_k=genkit_cfg.top_k,
            top_p=genkit_cfg.top_p,
            temperature=genkit_cfg.temperature,
            stop_sequences=genkit_cfg.stop_sequences,
        )
