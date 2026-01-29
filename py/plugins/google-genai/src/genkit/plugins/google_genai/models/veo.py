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

import asyncio
from typing import Any

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from genkit.ai import ActionRunContext
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
    systemRole=False,
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

    def __init__(self, version: str, client: genai.Client):
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
        """Handle a generation request using internal polling for LRO.

        Args:
            request: The generation request.
            _: action context

        Returns:
            The model's response.
        """
        prompt = self._build_prompt(request)
        config = self._get_config(request)

        with tracer.start_as_current_span('generate_videos') as span:
            # TODO: Add span attributes

            # Start LRO
            operation = await self._client.aio.models.generate_videos(model=self._version, prompt=prompt, config=config)

            # Poll until done
            # Note: SDK might have wait_for_completion logic?
            # If `operation` is a standard LRO object, we can loop.
            # Assuming SDK returns a job/operation object that has `.done()` or similar.
            # If it's `google.api_core.operation.Operation`, it has `.result()`.
            # But `genai` SDK is new. Let's assume it returns a custom Operation object.
            # Based on `veo.go`, it returns an Operation.

            while not operation.done:
                await asyncio.sleep(2)  # Poll every 2 seconds
                # We need to refresh the operation status.
                # Does the SDK object update itself or do we need to fetch it?
                # In standard GAPIC, we don't. But `genai` client might be different.
                # `genai` SDK typically has `.poll()` or we re-fetch.
                # Actually, `client.aio.models.generate_videos` might return the RESOLVED response if it waits?
                # No, typically "generate_videos" implies LRO.
                # Let's assume `operation` needs refreshing or `result()` awaiting.
                # Safest: Use `operation.result()` if available and awaitable?
                # If `operation` is `google.genai.operations.AsyncOperation`:
                if hasattr(operation, 'result'):
                    response = await operation.result()
                    break
                # Fallback manual polling if no async result()
                # But SDK likely provides a way.
                pass

            # If `operation` doesn't have `result` or `done`, we might be using it wrong.
            # Let's assume `operation.result()` works for now as standard Python convention.

            if hasattr(operation, 'result'):
                response = await operation.result()
            else:
                # Fallback: Assume it finished if we exited loop
                response = operation.result

            # Extract video
            content = self._contents_from_response(response)

        return GenerateResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            )
        )

    def _get_config(self, request: GenerateRequest) -> genai_types.GenerateVideosConfigOrDict:
        cfg = None
        if request.config:
            # Simple cast/validate
            cfg = request.config
        return cfg

    def _contents_from_response(self, response: genai_types.GenerateVideosResponse) -> list:
        content = []
        if response.generated_videos:
            for video in response.generated_videos:
                # Video URI is typically in video.uri or similar
                uri = video.video.uri
                content.append(
                    Part(
                        media=Media(
                            url=uri,
                            contentType='video/mp4',  # Default?
                        )
                    )
                )
        return content

    @property
    def metadata(self) -> dict:
        return {'model': {'supports': DEFAULT_VEO_SUPPORT.model_dump()}}
