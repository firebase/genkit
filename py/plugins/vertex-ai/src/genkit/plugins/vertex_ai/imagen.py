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

import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from typing import Any, Literal

import structlog
from pydantic import BaseModel
from vertexai.preview.vision_models import ImageGenerationModel

from genkit.ai import ActionRunContext
from genkit.types import (
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

logger = structlog.get_logger(__name__)


class ImagenVersion(StrEnum):
    """The version of the Imagen model to use."""

    IMAGEN3 = 'imagen-3.0-generate-002'
    IMAGEN3_FAST = 'imagen-3.0-fast-generate-001'
    IMAGEN2 = 'imagegeneration@006'


class ImagenOptions(BaseModel):
    """Options for the Imagen model."""

    number_of_images: int = 1
    language: Literal['auto', 'en', 'es', 'hi', 'ja', 'ko', 'pt', 'zh-TW', 'zh', 'zh-CN'] = 'auto'
    aspect_ratio: Literal['1:1', '9:16', '16:9', '3:4', '4:3'] = '1:1'
    safety_filter_level: Literal['block_most', 'block_some', 'block_few', 'block_fewest'] = 'block_some'
    person_generation: Literal['dont_allow', 'allow_adult', 'allow_all'] = 'allow_adult'
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
    """Imagen text-to-image model."""

    def __init__(self, version: ImagenVersion):
        """Initialize the Imagen model.

        Args:
            version: The version of the Imagen model to use.
        """
        self._version = version

    @property
    def model(self) -> ImageGenerationModel:
        """Get the Imagen model.

        Returns:
            The Imagen model.
        """
        return ImageGenerationModel.from_pretrained(self._version)

    def generate(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Handle a generation request using the Imagen model.

        Args:
            request: The generation request containing messages and parameters.
            ctx: additional context.

        Returns:
            The model's response to the generation request.
        """
        prompt = self.build_prompt(request)

        options = request.config if request.config else ImagenOptions().model_dump()
        options['prompt'] = prompt

        images = self.model.generate_images(**options)

        media_content = [
            MediaPart(media=Media(contentType=image._mime_type, url=image._as_base64_string())) for image in images
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
            request: a packed request for the model

        Returns:
            a single string with a prompt
        """
        prompt = []
        for message in request.messages:
            for text_part in message.content:
                if isinstance(text_part.root, TextPart):
                    prompt.append(text_part.root.text)
                else:
                    logger.error('Non-text messages are not supported')
        return ' '.join(prompt)

    @property
    def model_metadata(self) -> dict[str, Any]:
        """Get the metadata for the Imagen model.

        Returns:
            The metadata for the Imagen model.
        """
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }
