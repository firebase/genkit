# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import abc
from enum import StrEnum
from functools import cached_property

from genkit.core.action import ActionRunContext
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
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)
from google import genai

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


class GeminiModel(abc.ABC):
    def __init__(self, version: str | GeminiVersion, client: genai.Client):
        self._version = version
        self._client = client

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

        response = await self._client.aio.models.generate_content(
            model=self._version, contents=request_contents, config=request_cfg
        )

        return self._respond(response, ctx)

    @cached_property
    def metadata(self) -> dict:
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
        reqest_contents: list[genai.types.Content] = []
        for msg in request.messages:
            content_parts: list[genai.types.Part] = []
            for p in msg.content:
                content_parts.append(PartConverter.to_gemini(p))
            reqest_contents.append(
                genai.types.Content(parts=content_parts, role=msg.role)
            )

        return reqest_contents

    def _respond(
        self,
        response: genai.types.GenerateContentResponse,
        ctx: ActionRunContext,
    ) -> GenerateResponse | None:
        content = []
        if response.candidates:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    content.append(PartConverter.from_gemini(part=part))

        if ctx.is_streaming:
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
        else:
            return GenerateResponse(
                message=Message(
                    content=content,
                    role=Role.MODEL,
                )
            )

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
