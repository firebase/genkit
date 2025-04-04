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
import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from functools import cached_property
from typing import Any

from google import genai
from google.genai import types as genai_types
from pydantic import TypeAdapter, ValidationError

from genkit.ai import ActionRunContext
from genkit.codec import dump_dict, dump_json
from genkit.core.tracing import tracer
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    Media,
    Message,
    ModelInfo,
    Part,
    Role,
    Supports,
    TextPart,
)


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


class ImagenModel:
    def __init__(self, version: str | ImagenVersion, client: genai.Client):
        """Initialize Imagen model.

        Args:
            version: Imagen version
            client: Google AI client
        """
        self._version = version
        self._client = client

    def _build_prompt(self, request: GenerateRequest) -> str:
        """Build prompt request from Genkit request.

        Args:
            request: Genkit request.

        Returns:
            prompt for Imagen
        """
        prompt = []
        for message in request.messages:
            for part in message.content:
                if isinstance(part.root, TextPart):
                    prompt.append(part.root.text)
                else:
                    raise ValueError('Non-text messages are not supported')
        return ' '.join(prompt)

    async def generate(self, request: GenerateRequest, _: ActionRunContext) -> GenerateResponse:
        """Handle a generation request.

        Args:
            request: The generation request containing messages and parameters.
            _: action context

        Returns:
            The model's response to the generation request.
        """
        prompt = self._build_prompt(request)
        config = self._get_config(request.config) if request.config else None

        with tracer.start_as_current_span('generate_images') as span:
            span.set_attribute(
                'genkit:input',
                dump_json({
                    'config': dump_dict(config),
                    'contents': prompt,
                    'model': self._version,
                }),
            )
            response = await self._client.aio.models.generate_images(model=self._version, prompt=prompt, config=config)
            span.set_attribute('genkit:output', dump_json(response))

        content = self._contents_from_response(response)

        return GenerateResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            )
        )

    def _get_config(self, config: dict[str, Any]) -> genai_types.GenerateImagesConfigOrDict:
        ta = TypeAdapter(genai_types.GenerateImagesConfigOrDict)
        try:
            result = ta.validate_python(config)
            return result
        except ValidationError as e:
            raise ValueError(
                'The configuration dictionary is invalid. Refer the documentation for available fields'
            ) from e

    def _contents_from_response(self, response: genai_types.GenerateImagesResponse) -> list:
        """Retrieve contents from google-genai response.

        Args:
            response: google-genai response.

        Returns:
            list of generated contents.
        """
        content = []
        if response.generated_images:
            for image in response.generated_images:
                content.append(
                    Part(
                        media=Media(
                            url=base64.b64encode(image.image.image_bytes),
                            contentType=image.image.mime_type,
                        )
                    )
                )

        return content

    @cached_property
    def metadata(self) -> dict:
        """Get model metadata.

        Returns:
            model metadata.
        """
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }
