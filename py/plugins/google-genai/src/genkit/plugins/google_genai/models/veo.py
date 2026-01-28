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

"""Veo video generation model for Google GenAI plugin.

Veo is Google's video generation model that creates videos from text prompts.
It uses the background model pattern because video generation is a long-running
operation that can take 30 seconds to several minutes.

Architecture:
    ```
    ┌──────────────────────────────────────────────────────────────────────┐
    │                      Veo Video Generation Flow                        │
    ├──────────────────────────────────────────────────────────────────────┤
    │                                                                       │
    │   1. START                 2. POLL                  3. COMPLETE       │
    │   ┌─────────┐             ┌─────────┐             ┌─────────┐        │
    │   │ Prompt  │ ─predict──► │Operation│ ─getOp()──► │  Video  │        │
    │   │  +cfg   │  LongRun    │  (name) │    ...      │  (URI)  │        │
    │   └─────────┘             └────┬────┘             └─────────┘        │
    │                                                                       │
    └──────────────────────────────────────────────────────────────────────┘
    ```

Supported Models:
    +-------------------------------+------------------------------------------+
    | Model                         | Description                              |
    +-------------------------------+------------------------------------------+
    | veo-2.0-generate-001          | Veo 2.0 standard                         |
    | veo-3.0-generate-001          | Veo 3.0 standard                         |
    | veo-3.0-fast-generate-001     | Veo 3.0 fast (lower latency)            |
    | veo-3.1-generate-preview      | Veo 3.1 preview                          |
    | veo-3.1-fast-generate-preview | Veo 3.1 fast preview                     |
    +-------------------------------+------------------------------------------+

Example:
    >>> from genkit import Genkit
    >>> from genkit.plugins.google_genai import GoogleAI
    >>>
    >>> ai = Genkit(plugins=[GoogleAI()])
    >>>
    >>> # Start video generation
    >>> response = await ai.generate(
    ...     model='googleai/veo-2.0-generate-001',
    ...     prompt='A cat playing piano in a jazz club',
    ... )
    >>>
    >>> # Poll until complete
    >>> operation = response.operation
    >>> while not operation.done:
    ...     await asyncio.sleep(5)
    ...     operation = await ai.check_operation(operation)
    >>>
    >>> # Get the video URL
    >>> print(operation.output)

See Also:
    - https://ai.google.dev/gemini-api/docs/video
    - JS implementation: js/plugins/google-genai/src/googleai/veo.ts
"""

import sys

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

from typing import Any

from google import genai
from pydantic import BaseModel, Field

from genkit.blocks.background_model import BackgroundAction, define_background_model
from genkit.core.action import ActionRunContext
from genkit.core.registry import Registry
from genkit.core.typing import (
    Error,
    GenerateRequest,
    ModelInfo,
    Operation,
    Supports,
)


class VeoVersion(StrEnum):
    """Supported Veo video generation models.

    See: https://cloud.google.com/vertex-ai/generative-ai/docs/video/model-versions
    """

    # Veo 2 (stable production models)
    VEO_2_0 = 'veo-2.0-generate-001'
    VEO_2_0_EXP = 'veo-2.0-generate-exp'
    # Veo 3.1 (latest with native audio, improved narrative control)
    VEO_3_1 = 'veo-3.1-generate-001'
    VEO_3_1_FAST = 'veo-3.1-fast-generate-001'


# Known Veo models with their capabilities
KNOWN_VEO_MODELS = {
    VeoVersion.VEO_2_0,
    VeoVersion.VEO_2_0_EXP,
    VeoVersion.VEO_3_1,
    VeoVersion.VEO_3_1_FAST,
}


def is_veo_model(name: str) -> bool:
    """Check if a model name is a Veo model.

    Args:
        name: The model name to check.

    Returns:
        True if this is a Veo model name.
    """
    return name.startswith('veo-')


class VeoConfig(BaseModel):
    """Configuration options for Veo video generation.

    See: https://ai.google.dev/gemini-api/docs/video

    Attributes:
        negative_prompt: Text describing what to avoid in the video.
        aspect_ratio: Desired aspect ratio ('9:16' or '16:9').
        person_generation: Control generation of people in videos.
        duration_seconds: Length of output video in seconds (5-8).
        enhance_prompt: Enable prompt enhancement (default: True).
    """

    negative_prompt: str | None = Field(default=None, alias='negativePrompt')
    aspect_ratio: str | None = Field(default=None, alias='aspectRatio')
    person_generation: str | None = Field(default=None, alias='personGeneration')
    duration_seconds: int | None = Field(default=None, ge=5, le=8, alias='durationSeconds')
    enhance_prompt: bool | None = Field(default=None, alias='enhancePrompt')

    model_config = {'populate_by_name': True}


def veo_model_info(version: str) -> ModelInfo:
    """Get model info for a Veo model.

    Args:
        version: The Veo model version.

    Returns:
        ModelInfo describing the model's capabilities.
    """
    return ModelInfo(
        label=f'Google AI - {version}',
        supports=Supports(
            media=True,
            multiturn=False,
            tools=False,
            system_role=False,
            output=['media'],
        ),
    )


def _extract_text(request: GenerateRequest) -> str:
    """Extract text prompt from a GenerateRequest.

    Args:
        request: The generation request.

    Returns:
        The text prompt string.
    """
    if not request.messages:
        return ''
    for message in request.messages:
        for part in message.content:
            if hasattr(part.root, 'text') and part.root.text:
                return str(part.root.text)
    return ''


def _to_veo_parameters(config: Any) -> dict[str, Any]:  # noqa: ANN401
    """Convert config to Veo API parameters.

    Args:
        config: The model configuration (VeoConfig or dict).

    Returns:
        Dictionary of Veo API parameters.
    """
    if config is None:
        return {}

    if isinstance(config, VeoConfig):
        params = config.model_dump(by_alias=True, exclude_none=True)
    elif isinstance(config, dict):
        params = {k: v for k, v in config.items() if v is not None}
    else:
        return {}

    return params


def _from_veo_operation(api_op: dict[str, Any]) -> Operation:
    """Convert Veo API operation to Genkit Operation.

    Args:
        api_op: The raw API operation response.

    Returns:
        A Genkit Operation object.
    """
    op = Operation(
        id=api_op.get('name', ''),
        done=api_op.get('done', False),
    )

    # Handle error
    if 'error' in api_op and api_op['error']:
        op.error = Error(message=api_op['error'].get('message', 'Unknown error'))
        return op

    # Handle response with generated videos
    response = api_op.get('response', {})
    video_response = response.get('generateVideoResponse', {})
    samples = video_response.get('generatedSamples', [])

    if samples:
        # Build content from generated videos
        content = []
        for sample in samples:
            video = sample.get('video', {})
            uri = video.get('uri')
            if uri:
                content.append({'media': {'url': uri}})

        if content:
            op.output = {
                'finishReason': 'stop',
                'message': {
                    'role': 'model',
                    'content': content,
                },
            }

    return op


class VeoModel:
    """Veo video generation model.

    This class implements the background model pattern for Veo video generation.
    """

    def __init__(self, version: str, client: genai.Client) -> None:
        """Initialize Veo model.

        Args:
            version: The Veo model version.
            client: The Google GenAI client.
        """
        self._version = version
        self._client = client

    async def start(self, request: GenerateRequest, ctx: ActionRunContext) -> Operation:
        """Start a video generation operation.

        Args:
            request: The generation request.
            ctx: The action run context.

        Returns:
            An Operation with the job ID.
        """
        prompt = _extract_text(request)
        if not prompt:
            raise ValueError('Veo requires a text prompt')

        # Build the Veo predict request
        {
            'instances': [{'prompt': prompt}],
            'parameters': _to_veo_parameters(request.config),
        }

        # Call the predictLongRunning API
        # Note: The google-genai client may not expose this directly,
        # so we use the underlying REST API pattern
        response = await self._client.aio.models.generate_videos(
            model=self._version,
            prompt=prompt,
            config=request.config if isinstance(request.config, dict) else None,
        )

        # Convert to Operation
        return _from_veo_operation({
            'name': response.name if hasattr(response, 'name') else str(response),
            'done': getattr(response, 'done', False),
        })

    async def check(self, operation: Operation) -> Operation:
        """Check the status of a video generation operation.

        Args:
            operation: The operation to check.

        Returns:
            Updated Operation with current status.
        """
        # Get the operation status using the video-specific method
        response = await self._client.aio.operations._get_videos_operation(operation_name=operation.id)

        # Convert response to dict for processing
        op_dict = {
            'name': getattr(response, 'name', operation.id),
            'done': getattr(response, 'done', False),
        }

        if hasattr(response, 'error') and response.error:
            op_dict['error'] = {'message': str(response.error)}

        if hasattr(response, 'response') and response.response:
            op_dict['response'] = response.response

        return _from_veo_operation(op_dict)


def define_veo_model(
    registry: Registry,
    name: str,
    version: str,
    client: genai.Client,
) -> BackgroundAction:
    """Define and register a Veo background model.

    Args:
        registry: The registry to register with.
        name: The full model name (e.g., 'googleai/veo-2.0-generate-001').
        version: The Veo version (e.g., 'veo-2.0-generate-001').
        client: The Google GenAI client.

    Returns:
        A BackgroundAction for the Veo model.
    """
    veo = VeoModel(version, client)

    return define_background_model(
        registry=registry,
        name=name,
        start=veo.start,
        check=veo.check,
        label=f'Google AI - {version}',
        info=veo_model_info(version),
        config_schema=VeoConfig,
        description=f'Veo video generation model ({version})',
    )
