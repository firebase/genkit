# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""An Imagen model on VertexAI sample."""

import asyncio
import base64

from genkit.ai import Genkit
from genkit.core.typing import Message, Role, TextPart
from genkit.plugins.vertex_ai import (
    ImagenOptions,
    ImagenVersion,
    VertexAI,
    vertexai_name,
)

ai = Genkit(
    plugins=[VertexAI()], model=vertexai_name(ImagenVersion.IMAGEN3_FAST)
)


@ai.flow()
async def draw_image(prompt: str):
    # config is optional
    config = ImagenOptions(number_of_images=3)
    return await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=prompt)],
            )
        ],
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
