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

import os

import structlog

from genkit.ai import Genkit
from genkit.plugins.vertex_ai.model_garden import ModelGardenPlugin, model_garden_name

logger = structlog.get_logger(__name__)


def get_project_id() -> str:
    """Get Google Cloud project ID from environment or prompt user."""
    project_id = os.getenv('GCLOUD_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        project_id = input('Enter your Google Cloud Project ID: ').strip()
        if not project_id:
            raise ValueError('Google Cloud Project ID is required for Model Garden.')
        os.environ['GCLOUD_PROJECT'] = project_id
    return project_id


def get_location() -> str:
    """Get Google Cloud location from environment or prompt user."""
    location = os.getenv('GOOGLE_CLOUD_LOCATION') or os.getenv('GOOGLE_CLOUD_REGION')
    if not location:
        location = input('Enter your Google Cloud Location (default: us-central1): ').strip()
        if not location:
            location = 'us-central1'
        os.environ['GOOGLE_CLOUD_LOCATION'] = location
    return location


project_id = get_project_id()
location = get_location()

ai = Genkit(
    plugins=[
        ModelGardenPlugin(project_id=project_id, location=location),
    ],
)


# @ai.flow()
# async def say_hi(name: str) -> str:
#     """Generate a greeting for the given name.
#
#     Args:
#         name: The name of the person to greet.
#
#     Returns:
#         The generated greeting response.
#     """
#     response = await ai.generate(
#         model=model_garden_name('meta/llama-3.2-90b-vision-instruct-maas'),
#         config={'temperature': 1},
#         prompt=f'hi {name}',
#     )
#
#     return response.message.content[0].root.text


# @ai.flow()
# async def say_hi_stream(name: str) -> str:
#     """Say hi to a name and stream the response.
#
#     Args:
#         name: The name to say hi to.
#
#     Returns:
#         The response from the OpenAI API.
#     """
#     stream, _ = ai.generate_stream(
#         model=model_garden_name('meta/llama-3.2-90b-vision-instruct-maas'),
#         config={'temperature': 1},
#         prompt=f'hi {name}',
#     )
#     result = ''
#     async for data in stream:
#         for part in data.content:
#             result += part.root.text
#     return result


@ai.flow()
async def jokes_flow(subject: str) -> str:
    """Generate a joke about the given subject.

    Args:
        subject: The subject of the joke.

    Returns:
        The generated joke.
    """
    response = await ai.generate(
        # Note: The model name usually includes the publisher prefix for Model Garden
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        config={'temperature': 1, 'max_output_tokens': 1024},
        prompt=f'Tell a short joke about {subject}',
    )

    return response.text


async def main() -> None:
    # await logger.ainfo(await say_hi('John Doe'))
    # await logger.ainfo(await say_hi_stream('John Doe'))
    await logger.ainfo(await jokes_flow('banana'))


if __name__ == '__main__':
    ai.run_main(main())
