# Copyright 2022 Google Inc.
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
"""
VertexAI for Python.
"""

from ..genkit import Genkit
from ..types import GenerateRequest, GenerateResponse, Message, TextPart
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part
from typing import Optional


def vertexAI(project_id: Optional[str] = None):

    def plugin(ai: Genkit):
        vertexai.init(location="us-central1")

        def gemini(request: GenerateRequest) -> GenerateResponse:
            geminiMsgs: list[Content] = []
            for m in request.messages:
                geminiParts: list[Part] = []
                for p in m.content:
                    if p.text != None:
                        geminiParts.append(Part.from_text(p.text))
                    else:
                        raise Exception('unsupported part type')
                geminiMsgs.append(
                    Content(role=m.role.value, parts=geminiParts))
            model = GenerativeModel("gemini-1.5-flash-002")
            response = model.generate_content(
                contents=geminiMsgs
            )
            return GenerateResponse(message=Message(role="model", content=[TextPart(text=response.text)]))

        ai.define_model(name='vertexai/gemini-1.5-flash', fn=gemini, metadata={
            "model": {
                "label": "banana",
                "supports": {
                    "multiturn": True
                },
            }
        })
    return plugin


def gemini(name: str):
    return f"vertexai/{name}"


__all__ = ["vertexAI", gemini]
