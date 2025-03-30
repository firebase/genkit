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
    GoogleGenai,
    google_genai_name,
)

ai = Genkit(
    plugins=[GoogleGenai()],
    model=google_genai_name('gemini-2.0-flash'),
)

app = Flask(__name__)


@app.post('/chat')
@genkit_flask_handler(ai)
@ai.flow()
async def say_hi(name: str, ctx):
    return await ai.generate(
        on_chunk=ctx.send_chunk,
        prompt=f'tell a medium sized joke about {name}',
    )
