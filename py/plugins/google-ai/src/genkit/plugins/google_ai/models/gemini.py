# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from functools import cached_property

from genkit.core.action import ActionRunContext
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

        reqest_msgs: list[genai.types.Content] = []
        for msg in request.messages:
            message_parts: list[genai.types.Part] = []
            for p in msg.content:
                message_parts.append(
                    genai.types.Part.from_text(text=p.root.text)
                )
            reqest_msgs.append(
                genai.types.Content(parts=message_parts, role=msg.role)
            )

        request_cfg = (
            self._genkit_to_googleai_cfg(request.config)
            if request.config
            else None
        )

        response = await self._client.aio.models.generate_content(
            model=self._name, contents=reqest_msgs, config=request_cfg
        )

        if ctx.is_streaming:
            ctx.send_chunk(
                chunk=GenerateResponseChunk(
                    content=[TextPart(response.text)], role=Role.MODEL
                )
            )
        else:
            return GenerateResponse(
                message=Message(
                    role=Role.MODEL,
                    content=[TextPart(text=response.text)],
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
