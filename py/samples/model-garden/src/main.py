# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pdb
import asyncio
from genkit.veneer.veneer import Genkit
from genkit.plugins.vertex_ai.model_garden import (
    OpenAIFormatModelVersion,
    VertexAIModelGarden,
    vertexai_name
)
from genkit.core.typing import (
    Role,
    TextPart,
    Message
)

from openai import OpenAI
from google.auth import default, transport
# import google.auth.transport.requests

# credentials, project_id = default()
# credentials.refresh(transport.requests.Request())
# print(credentials)
# print(project_id)


# location = 'us-central1'
# base_url = f'https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/endpoints/openapi'

# client = OpenAI(
#     api_key=credentials.token,
#     base_url=base_url
# )

# response = client.chat.completions.create(
#     model="google/gemini-2.0-flash-001",
#     messages=[{"role": "user", "content": "Why is the sky blue?"}],
# )

# print(response)


# pdb.set_trace()

ai = Genkit(
    plugins=[
        VertexAIModelGarden(
            location='us-central1',
            models=['llama-3.1']
        )
    ]
)
@ai.flow()
async def say_hi(name: str):
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    return await ai.generate(
        model=vertexai_name(OpenAIFormatModelVersion.LLAMA_3_1),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'Say hi to {name}')],
            ),
        ],
    )

async def main() -> None:
    print(await say_hi('John Doe'))

if __name__ == '__main__':
    asyncio.run(main())