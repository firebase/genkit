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

from flask import Flask

from genkit.ai import Genkit
from genkit.plugins.flask import genkit_flask_handler
from genkit.plugins.google_genai import (
    GoogleAI,
    googleai_name,
)
from genkit.plugins.google_genai.models.gemini import GoogleAIGeminiVersion

ai = Genkit(
    plugins=[GoogleAI()],
    model=googleai_name(GoogleAIGeminiVersion.GEMINI_2_0_FLASH),
)

app = Flask(__name__)


async def my_context_provider(request):
    """Provide a context for the flow."""
    return {'username': request.headers.get('authorization')}


@app.post('/chat')
@genkit_flask_handler(ai, context_provider=my_context_provider)
@ai.flow()
async def say_hi(name: str, ctx):
    """Say hi to the user."""
    return await ai.generate(
        on_chunk=ctx.send_chunk,
        prompt=f'tell a medium sized joke about {name} for user {ctx.context.get("username")}',
    )
