# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from typing import Any

from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Media1,
    MediaPart,
    Message,
    ModelInfo,
    Role,
    Supports,
)
from vertexai.preview.vision_models import ImageGenerationModel


class ImagenVersion(StrEnum):
    IMAGEN3 = 'imagen-3.0-generate-002'
    IMAGEN3_FAST = 'imagen-3.0-fast-generate-001'
    IMAGEN2 = 'imagegeneration@006'


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

    def handle_request(self, request: GenerateRequest) -> GenerateResponse:
        parts: list[str] = []
        for m in request.messages:
            for p in m.content:
                if p.root.text is not None:
                    parts.append(p.root.text)
                else:
                    raise Exception('unsupported part type')

        prompt = ' '.join(parts)
        images = self.model.generate_images(
            prompt=prompt,
            number_of_images=1,
            language='en',
            aspect_ratio='1:1',
            safety_filter_level='block_some',
            person_generation='allow_adult',
        )

        media_content = [
            MediaPart(
                media=Media1(
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

    @property
    def model_metadata(self) -> dict[str, Any]:
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }
