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

"""Background model demo using Google Veo for video generation.

This demo shows how to use **Veo**, Google's video generation model, which is
implemented as a **background model** because video generation can take 30 seconds
to several minutes.

What is Veo?
============
Veo is Google's state-of-the-art video generation model that creates videos
from text prompts. It supports:

    +----------------------------+---------------------------------------------+
    | Feature                    | Description                                 |
    +----------------------------+---------------------------------------------+
    | Text-to-video              | Generate videos from text descriptions      |
    | Image-to-video             | Animate images into videos                  |
    | Aspect ratios              | 9:16 (vertical) or 16:9 (horizontal)        |
    | Duration                   | 5-8 seconds per generation                  |
    | Prompt enhancement         | AI-enhanced prompts for better results      |
    +----------------------------+---------------------------------------------+

Why Background Models?
======================
Regular AI models (like text generation) return results in milliseconds.
But video generation takes much longer:

    ```
    ┌──────────────────────────────────────────────────────────────────────┐
    │                    Video Generation Timeline                          │
    ├──────────────────────────────────────────────────────────────────────┤
    │                                                                       │
    │   Text Generation:   |████| ~1 second                                │
    │                                                                       │
    │   Image Generation:  |████████████| ~10-30 seconds                   │
    │                                                                       │
    │   Video Generation:  |████████████████████████████████| 30s - 5min   │
    │                                                                       │
    └──────────────────────────────────────────────────────────────────────┘
    ```

Background models solve this by:
1. Returning immediately with a job ID (Operation)
2. Allowing you to poll for completion
3. Delivering the result when ready

How to Use Veo
==============
```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI, VeoVersion

ai = Genkit(plugins=[GoogleAI()])

# Start video generation (returns immediately)
response = await ai.generate(
    model=f'googleai/{VeoVersion.VEO_2_0}',
    prompt='A cat playing piano in a jazz club',
)

# Poll until complete
operation = response.operation
while not operation.done:
    await asyncio.sleep(5)
    operation = await ai.check_operation(operation)

# Get the video URL
video_url = operation.output['message']['content'][0]['media']['url']
```

Running This Demo
=================
1. Set your API key:
   export GEMINI_API_KEY=your_api_key

2. Run the demo:
   cd py/samples/background-model-demo
   ./run.sh

3. Open the DevUI and try the `veo_video_generator` flow.

Note: If no API key is set, the demo falls back to a simulated model.

See Also:
========
- Veo documentation: https://ai.google.dev/gemini-api/docs/video
- Background models: genkit.blocks.background_model
"""

import asyncio
import os
import time
import uuid
from typing import Annotated, Any

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit
from genkit.blocks.background_model import lookup_background_action
from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    Error,
    GenerateRequest,
    Message,
    ModelInfo,
    Operation,
    Part,
    Role,
    Supports,
    TextPart,
)

# Install rich traceback handler for beautiful, Rust-like error messages
install_rich_traceback(show_locals=True, width=120, extra_lines=3)

# Check if we have an API key for real Veo
HAS_API_KEY = bool(os.getenv('GEMINI_API_KEY'))

# Initialize Genkit with or without the Google plugin
if HAS_API_KEY:
    from genkit.plugins.google_genai import GoogleAI, VeoVersion

    ai = Genkit(plugins=[GoogleAI()])
    VEO_MODEL = f'googleai/{VeoVersion.VEO_2_0}'
    print(f'[Veo Demo] Using real Veo model: {VEO_MODEL}')
else:
    ai = Genkit()
    VEO_MODEL = 'simulated-veo'
    print('[Veo Demo] No GEMINI_API_KEY found, using simulated model')
    print('[Veo Demo] Set GEMINI_API_KEY to use real Veo video generation')


# ============================================================================
# Simulated Veo Model (used when no API key is available)
# ============================================================================

# In-memory store for simulated operations
_operations: dict[str, dict[str, Any]] = {}


class SimulatedVeoConfig(BaseModel):
    """Configuration for the simulated Veo model."""

    duration_seconds: int = Field(default=5, description='Duration of generated video in seconds')
    aspect_ratio: str = Field(default='16:9', description='Video aspect ratio')
    enhance_prompt: bool = Field(default=True, description='Enable prompt enhancement')


async def simulated_veo_start(
    request: GenerateRequest,
    ctx: ActionRunContext,
) -> Operation:
    """Start a simulated video generation operation."""
    prompt = ''
    if request.messages:
        for msg in request.messages:
            for part in msg.content:
                if hasattr(part.root, 'text') and part.root.text:
                    prompt = str(part.root.text)
                    break
            if prompt:
                break

    op_id = f'operations/veo-{uuid.uuid4().hex[:12]}'

    _operations[op_id] = {
        'prompt': prompt,
        'start_time': time.time(),
        'status': 'processing',
        'progress': 0,
    }

    print(f'[Simulated Veo] Started: {op_id}')
    print(f'[Simulated Veo] Prompt: "{prompt[:60]}..."')

    return Operation(
        id=op_id,
        done=False,
        metadata={'status': 'processing', 'progress': 0},
    )


async def simulated_veo_check(operation: Operation) -> Operation:
    """Check simulated video generation status."""
    op_data = _operations.get(operation.id)

    if op_data is None:
        return Operation(
            id=operation.id,
            done=True,
            error=Error(message=f'Operation {operation.id} not found'),
        )

    # Simulate 10-second generation
    elapsed = time.time() - op_data['start_time']
    progress = min(100, int(elapsed * 10))
    op_data['progress'] = progress

    print(f'[Simulated Veo] {operation.id}: {progress}% complete')

    if progress >= 100:
        video_url = f'https://storage.googleapis.com/veo-videos/{operation.id.split("/")[-1]}.mp4'

        return Operation(
            id=operation.id,
            done=True,
            metadata={'status': 'completed', 'progress': 100},
            output={
                'finishReason': 'stop',
                'message': {
                    'role': 'model',
                    'content': [{'media': {'url': video_url}}],
                },
            },
        )

    return Operation(
        id=operation.id,
        done=False,
        metadata={
            'status': 'processing',
            'progress': progress,
            'estimatedRemainingSeconds': max(0, 10 - elapsed),
        },
    )


# Register simulated model if no API key
if not HAS_API_KEY:
    simulated_veo = ai.define_background_model(
        name='simulated-veo',
        start=simulated_veo_start,
        check=simulated_veo_check,
        label='Simulated Veo (Demo)',
        info=ModelInfo(
            label='Simulated Veo',
            supports=Supports(
                media=True,
                multiturn=False,
                tools=False,
                system_role=False,
                output=['media'],
            ),
        ),
        config_schema=SimulatedVeoConfig,
        description='Simulated Veo for demo purposes (set GEMINI_API_KEY for real Veo)',
    )


# ============================================================================
# Demo Flows
# ============================================================================


@ai.flow(name='veo_video_generator', description='Generate a video using Veo')
async def veo_video_generator_flow(
    prompt: Annotated[
        str, Field(default='A majestic cat playing piano in a jazz club, cinematic lighting')
    ] = 'A majestic cat playing piano in a jazz club, cinematic lighting',
) -> dict[str, Any]:
    """Generate a video using Veo (or simulated model).

    This flow demonstrates the background model pattern:
    1. Start the video generation (returns immediately)
    2. Poll until complete
    3. Return the video URL

    Args:
        prompt: Text description of the video to generate.

    Returns:
        Dictionary with operation details and video URL.
    """
    print(f'\n{"=" * 60}')
    print('Veo Video Generation')
    print(f'{"=" * 60}')
    print(f'Model: {VEO_MODEL}')
    print(f'Prompt: {prompt}')
    print()

    # Get the model (either real Veo or simulated)
    if HAS_API_KEY:
        # Use real Veo via lookup
        action_key = f'/background-model/{VEO_MODEL}'
        video_model = await lookup_background_action(ai.registry, action_key)
        if video_model is None:
            return {'error': f'Model {VEO_MODEL} not found'}
    else:
        # Use simulated model
        video_model = simulated_veo

    # Start the operation
    operation = await video_model.start(
        GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text=prompt))],
                )
            ],
        )
    )

    print(f'Operation started: {operation.id}')
    print(f'Action key: {operation.action}')
    print('Polling for completion...\n')

    # Poll until complete (with timeout)
    max_wait = 300  # 5 minutes for real Veo
    start_time = time.time()

    while not operation.done:
        if time.time() - start_time > max_wait:
            print('Timeout waiting for video generation')
            break

        await asyncio.sleep(5)  # Poll every 5 seconds
        operation = await video_model.check(operation)

        if operation.metadata:
            progress = operation.metadata.get('progress', 0)
            status = operation.metadata.get('status', 'unknown')
            print(f'Status: {status}, Progress: {progress}%')

    print()

    if operation.done and operation.output:
        print(f'{"=" * 60}')
        print('Video generation complete!')
        print(f'{"=" * 60}')

        # Extract video URL from response
        video_url = None
        output = operation.output
        if isinstance(output, dict):
            message = output.get('message', {})
            content = message.get('content', [])
            if content and isinstance(content[0], dict):
                media = content[0].get('media', {})
                video_url = media.get('url')

        return {
            'operation_id': operation.id,
            'status': 'completed',
            'video_url': video_url,
            'output': operation.output,
            'using_real_veo': HAS_API_KEY,
        }
    elif operation.error:
        return {
            'operation_id': operation.id,
            'status': 'error',
            'error': operation.error,
            'using_real_veo': HAS_API_KEY,
        }
    else:
        return {
            'operation_id': operation.id,
            'status': 'timeout',
            'using_real_veo': HAS_API_KEY,
        }


@ai.flow(name='veo_check_status', description='Check the status of a Veo operation')
async def veo_check_status_flow(
    operation_id: Annotated[str, Field(default='operations/veo-example123')] = 'operations/veo-example123',
) -> dict[str, Any]:
    """Check the status of an existing Veo operation.

    Args:
        operation_id: The operation ID to check (from veo_video_generator output).

    Returns:
        Current operation status.

    Note:
        Run veo_video_generator first to get a real operation_id, then use it here.
    """
    if operation_id == 'operations/veo-example123':
        return {
            'info': 'This is a demo operation ID. Run veo_video_generator first!',
            'usage': 'Copy the operation_id from veo_video_generator output and paste it here.',
            'example_operation_id': 'operations/veo-abc123def456',
        }

    # Create an operation object to check
    operation = Operation(
        id=operation_id,
        action=f'/background-model/{VEO_MODEL}',
        done=False,
    )

    # Check the operation
    updated = await ai.check_operation(operation)

    return {
        'operation_id': updated.id,
        'done': updated.done,
        'output': updated.output,
        'error': updated.error,
        'metadata': updated.metadata,
    }


async def main() -> None:
    """Keep the server alive for the Dev UI."""
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
