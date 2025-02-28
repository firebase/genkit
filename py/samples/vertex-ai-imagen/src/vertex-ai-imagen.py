# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""An Imagen model on VertexAI sample."""

import asyncio
import base64

from genkit.core.typing import Message, Role, TextPart
from genkit.plugins.vertex_ai import ImagenVersion, VertexAI, vertexai_name
from genkit.veneer.veneer import Genkit

ai = Genkit(
    plugins=[VertexAI()], model=vertexai_name(ImagenVersion.IMAGEN3_FAST)
)


@ai.flow()
async def draw_image(prompt: str):
    return await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=prompt)],
            )
        ]
    )


async def main() -> None:
    """Main entry point for the Imagen sample."""
    response = await draw_image('Draw a flower.')
    base64string = response.message.content[0].root.media.url
    image = base64.b64decode(base64string, validate=True)
    with open('flower.jpg', 'wb') as f:
        f.write(image)


if __name__ == '__main__':
    asyncio.run(main())
