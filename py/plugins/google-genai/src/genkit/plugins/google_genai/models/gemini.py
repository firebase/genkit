# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from functools import cached_property

from google import genai

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


class GeminiModel:
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

        reqest_contents: list[genai.types.Content] = []
        for msg in request.messages:
            content_parts: list[genai.types.Part] = []
            for p in msg.content:
                content_parts.append(PartConverter.to_gemini(p))
            reqest_contents.append(
                genai.types.Content(parts=content_parts, role=msg.role)
            )

        return reqest_contents

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
            types: Genkit request

        Returns:
            Google Ai request config or None
        """

        cfg = None

        if request.config:
            request_config = (
                request.config
                if isinstance(request.config, GenerationCommonConfig)
                else GenerationCommonConfig(**request.config)
            )
            cfg = genai.types.GenerateContentConfig(
                max_output_tokens=request_config.max_output_tokens,
                top_k=request_config.top_k,
                top_p=request_config.top_p,
                temperature=request_config.temperature,
                stop_sequences=request_config.stop_sequences,
            )
        if request.output:
            response_mime_type = (
                'application/json' if request.output.format == 'json' else None
            )
            if not cfg:
                cfg = genai.types.GenerateContentConfig(
                    response_mime_type=response_mime_type
                )
            else:
                cfg.response_mime_type = response_mime_type
        return cfg
