# Copyright 2026 Google LLC
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

"""Google Cloud Veo Model Support."""

import asyncio
from typing import Any, cast

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, ConfigDict, Field

from genkit.ai import ActionRunContext
from genkit.core.tracing import tracer
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    Media,
    MediaPart,
    Message,
    ModelInfo,
    Part,
    Role,
    Supports,
    TextPart,
)


class VeoConfigSchema(BaseModel):
    """Veo Config Schema."""

    model_config = ConfigDict(extra='allow')
    negative_prompt: str | None = Field(default=None, description='Negative prompt for video generation.')
    aspect_ratio: str | None = Field(
        default=None, description='Desired aspect ratio of the output video (e.g. "16:9").'
    )
    person_generation: str | None = Field(default=None, description='Person generation mode.')
    duration_seconds: int | None = Field(default=None, description='Length of video in seconds.')
    enhance_prompt: bool | None = Field(default=None, description='Enable prompt enhancement.')


DEFAULT_VEO_SUPPORT = Supports(
    media=True,
    multiturn=False,
    tools=False,
    system_role=False,
    output=['media'],
)


def veo_model_info(
    version: str,
) -> ModelInfo:
    """Generates a ModelInfo object for Veo.

    Args:
        version: Version of the model.

    Returns:
        ModelInfo object.
    """
    return ModelInfo(
        label=f'Google AI - {version}',
        supports=DEFAULT_VEO_SUPPORT,
    )


class VeoModel:
    """Veo text-to-video model."""

    def __init__(self, version: str, client: genai.Client) -> None:
        """Initialize Veo model.

        Args:
            version: Veo version
            client: Google AI client
        """
        self._version = version
        self._client = client

    def _build_prompt(self, request: GenerateRequest) -> str:
        """Build prompt request from Genkit request."""
        prompt = []
        for message in request.messages:
            for part in message.content:
                if isinstance(part.root, TextPart):
                    prompt.append(part.root.text)
                else:
                    # TODO: Support image input if Veo supports it (e.g. for image-to-video)
                    # For now, strict text text-to-video
                    pass
        return ' '.join(prompt)

    async def generate(self, request: GenerateRequest, _: ActionRunContext) -> GenerateResponse:
        """Handle a generation request.

        Args:
            request: The generation request.
            _: action context

        Returns:
            The model's response.
        """
        prompt = self._build_prompt(request)
        config = self._get_config(request)

        with tracer.start_as_current_span('generate_videos'):
            operation = await self._client.aio.models.generate_videos(model=self._version, prompt=prompt, config=config)

            # Handling LRO. Using cast(Any) to avoid strict type definition issues for operation.result()
            op = cast(Any, operation)
            if hasattr(op, 'result'):
                # Check if result is a coroutine (awaitable) or direct value
                res = op.result()
                if asyncio.iscoroutine(res):
                    response = await res
                else:
                    response = res
            else:
                response = op

            content = self._contents_from_response(cast(genai_types.GenerateVideosResponse, response))

        return GenerateResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            )
        )

    def _get_config(self, request: GenerateRequest) -> genai_types.GenerateVideosConfigOrDict | None:
        cfg = None
        if request.config:
            # Simple cast/validate
            cfg = request.config
        return cfg

    def _contents_from_response(self, response: genai_types.GenerateVideosResponse) -> list[Part]:
        content = []
        if response.generated_videos:
            for video in response.generated_videos:
                # Video URI is typically in video.video.uri
                if video.video and video.video.uri:
                    uri = video.video.uri
                    content.append(
                        Part(
                            root=MediaPart(
                                media=Media(
                                    url=uri,
                                    content_type='video/mp4',
                                )
                            )
                        )
                    )
        return content

    @property
    def metadata(self) -> dict:
        """Model metadata."""
        return {'model': {'supports': DEFAULT_VEO_SUPPORT.model_dump()}}
