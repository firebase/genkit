# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import logging
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel
from vertexai.preview.vision_models import ImageGenerationModel

from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Media,
    MediaPart,
    Message,
    ModelInfo,
    Role,
    Supports,
    TextPart,
)

LOG = logging.getLogger(__name__)


class ImagenVersion(StrEnum):
    IMAGEN3 = 'imagen-3.0-generate-002'
    IMAGEN3_FAST = 'imagen-3.0-fast-generate-001'
    IMAGEN2 = 'imagegeneration@006'


class ImagenOptions(BaseModel):
    number_of_images: int = 1
    language: Literal[
        'auto', 'en', 'es', 'hi', 'ja', 'ko', 'pt', 'zh-TW', 'zh', 'zh-CN'
    ] = 'auto'
    aspect_ratio: Literal['1:1', '9:16', '16:9', '3:4', '4:3'] = '1:1'
    safety_filter_level: Literal[
        'block_most', 'block_some', 'block_few', 'block_fewest'
    ] = 'block_some'
    person_generation: Literal['dont_allow', 'allow_adult', 'allow_all'] = (
        'allow_adult'
    )
    negative_prompt: bool = False


SUPPORTED_MODELS = {
    ImagenVersion.IMAGEN3: ModelInfo(
        label='Vertex AI - Imagen3',
        supports=Supports(
            media=True,
            multiturn=False,
            tools=False,
            systemRole=False,
            output=['media'],
        ),
    ),
    ImagenVersion.IMAGEN3_FAST: ModelInfo(
        label='Vertex AI - Imagen3 Fast',
        supports=Supports(
            media=False,
            multiturn=False,
            tools=False,
            systemRole=False,
            output=['media'],
        ),
    ),
    ImagenVersion.IMAGEN2: ModelInfo(
        label='Vertex AI - Imagen2',
        supports=Supports(
            media=False,
            multiturn=False,
            tools=False,
            systemRole=False,
            output=['media'],
        ),
    ),
}


class Imagen:
    """Imagen - text to image model."""

    def __init__(self, version):
        self._version = version

    @property
    def model(self) -> ImageGenerationModel:
        return ImageGenerationModel.from_pretrained(self._version)

    def generate(
        self, request: GenerateRequest, ctx: ActionRunContext
    ) -> GenerateResponse:
        """Handle a generation request using the Imagen model.

        Args:
            request: The generation request containing messages and parameters.
            ctx: additional context.

        Returns:
            The model's response to the generation request.
        """
        prompt = self.build_prompt(request)

        options = (
            request.config if request.config else ImagenOptions().model_dump()
        )
        options['prompt'] = prompt

        images = self.model.generate_images(**options)

        media_content = [
            MediaPart(
                media=Media(
                    contentType=image._mime_type, url=image._as_base64_string()
                )
            )
            for image in images
        ]

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=media_content,
            )
        )

    def build_prompt(self, request: GenerateRequest) -> str:
        """Creates a single prompt string fom a list of messages and parts in requests.

        Args:
            - request: a packed request for the model

        Returns:
            - a single string with a prompt
        """
        prompt = []
        for message in request.messages:
            for text_part in message.content:
                if isinstance(text_part.root, TextPart):
                    prompt.append(text_part.root.text)
                else:
                    LOG.error('Non-text messages are not supported')
        return ' '.join(prompt)

    @property
    def model_metadata(self) -> dict[str, Any]:
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }
