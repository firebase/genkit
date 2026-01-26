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

"""A simple flow served via a flask server."""

import os
from typing import Annotated

from flask import Flask
from pydantic import Field

from genkit.ai import Genkit
from genkit.blocks.model import GenerateResponseWrapper
from genkit.core.action import ActionRunContext
from genkit.core.context import RequestData
from genkit.plugins.flask import genkit_flask_handler
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.google_genai.models.gemini import GoogleAIGeminiVersion

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

ai = Genkit(
    plugins=[GoogleAI()],
    model=f'googleai/{GoogleAIGeminiVersion.GEMINI_3_FLASH_PREVIEW}',
)

app = Flask(__name__)


async def my_context_provider(request: RequestData) -> dict:
    """Provide a context for the flow."""
    return {'username': request.request.headers.get('authorization')}


@app.post('/chat')
@genkit_flask_handler(ai, context_provider=my_context_provider)
@ai.flow()
async def say_hi(
    name: Annotated[str, Field(default='Alice')] = 'Alice',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> GenerateResponseWrapper:
    """Say hi to the user."""
    return await ai.generate(
        on_chunk=ctx.send_chunk,
        prompt=f'tell a medium sized joke about {name} for user {ctx.context.get("username")}',
    )
