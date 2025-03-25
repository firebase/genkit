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
import base64

from google import genai

from genkit.core.typing import (
    CustomPart,
    Media,
    MediaPart,
    Part,
    TextPart,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)


class PartConverter:
    EXECUTABLE_CODE = 'executableCode'
    CODE_EXECUTION_RESULT = 'codeExecutionResult'
    OUTCOME = 'outcome'
    OUTPUT = 'output'
    LANGUAGE = 'language'
    CODE = 'code'
    DATA = 'data:'

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
            return genai.types.Part(
                inline_data=genai.types.Blob(
                    data=part.root.media.url,
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
                    url=base64.b64encode(part.inline_data.data),
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
