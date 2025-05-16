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

"""An Imagen model on VertexAI sample."""

import asyncio
import base64

from genkit.ai import Genkit
from genkit.plugins.vertex_ai import (
    ImagenOptions,
    ImagenVersion,
    VertexAI,
    vertexai_name,
)

ai = Genkit(plugins=[VertexAI()], model=vertexai_name(ImagenVersion.IMAGEN3_FAST))


@ai.flow()
async def draw_image(prompt: str):
    """Draw an image."""
    # config is optional
    config = ImagenOptions(number_of_images=3)
    return await ai.generate(
        prompt=prompt,
        config=config.model_dump(),
    )


async def main() -> None:
    """Main entry point for the Imagen sample."""
    response = await draw_image('Draw a flower.')
    for i, content in enumerate(response.message.content):
        base64string = content.root.media.url
        image = base64.b64decode(base64string, validate=True)
        with open(f'flower_{i}.jpg', 'wb') as f:
            f.write(image)


if __name__ == '__main__':
    asyncio.run(main())
