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
from functools import cached_property, singledispatch

from google import genai

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


class GoogleAiVersion(StrEnum):
    GEMINI_1_0_PRO = 'gemini-1.0-pro'
    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'


SUPPORTED_MODELS = {
    GoogleAiVersion.GEMINI_1_0_PRO: gemini10Pro,
    GoogleAiVersion.GEMINI_1_5_PRO: gemini15Pro,
    GoogleAiVersion.GEMINI_1_5_FLASH: gemini15Flash,
    GoogleAiVersion.GEMINI_1_5_FLASH_8B: gemini15Flash8b,
    GoogleAiVersion.GEMINI_2_0_FLASH: gemini20Flash,
    GoogleAiVersion.GEMINI_2_0_PRO_EXP_02_05: gemini20ProExp0205,
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
    def __init__(self, client: genai.Client, name: str, model_def: ModelInfo):
        self._client = client
        self._model = model_def
        self._name = name

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

    async def generate_callback(
        self, request: GenerateRequest, ctx: ActionRunContext
    ) -> GenerateResponse:
        """Handle a generation request.

        Args:
            request: The generation request containing messages and parameters.
            ctx: action context

        Returns:
            The model's response to the generation request.
        """

        reqest_contents: list[genai.types.Content] = []
        for msg in request.messages:
            content_parts: list[genai.types.Part] = []
            for p in msg.content:
                content_parts.append(PartConverter.to_gemini(p))
            reqest_contents.append(
                genai.types.Content(parts=content_parts, role=msg.role)
            )

        request_cfg = (
            self._genkit_to_googleai_cfg(request.config)
            if request.config
            else None
        )

        response = await self._client.aio.models.generate_content(
            model=self._name, contents=reqest_contents, config=request_cfg
        )

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
        else:
            return GenerateResponse(
                message=Message(
                    content=content,
                    role=Role.MODEL,
                )
            )

    @cached_property
    def metadata(self) -> dict:
        """Create model metadata.

        Returns:
            Metadata dict
        """
        return {
            'model': {
                'supports': self._model.supports.model_dump(),
            }
        }
