# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
Google Cloud Vertex AI Plugin for Genkit.
"""

from collections.abc import Callable

import vertexai
from genkit.core.schemas import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)
from genkit.veneer.veneer import Genkit
from vertexai.generative_models import Content, GenerativeModel, Part


def package_name() -> str:
    return 'genkit.plugins.vertex_ai'


def vertex_ai(project_id: str | None = None) -> Callable[[Genkit], None]:
    def plugin(ai: Genkit) -> None:
        vertexai.init(location='us-central1', project=project_id)

        def handle_gemini_request(request: GenerateRequest) -> GenerateResponse:
            gemini_msgs: list[Content] = []
            for m in request.messages:
                gemini_parts: list[Part] = []
                for p in m.content:
                    if p.root.text is not None:
                        gemini_parts.append(Part.from_text(p.root.text))
                    else:
                        raise Exception('unsupported part type')
                gemini_msgs.append(
                    Content(role=m.role.value, parts=gemini_parts)
                )
            model = GenerativeModel('gemini-1.5-flash-002')
            response = model.generate_content(contents=gemini_msgs)
            return GenerateResponse(
                message=Message(
                    role=Role.model, content=[TextPart(text=response.text)]
                )
            )

        ai.define_model(
            name='vertexai/gemini-1.5-flash',
            fn=handle_gemini_request,
            metadata={
                'model': {
                    'label': 'banana',
                    'supports': {'multiturn': True},
                }
            },
        )

    return plugin


def gemini(name: str) -> str:
    return f'vertexai/{name}'


__all__ = ['package_name', 'vertex_ai', 'gemini']
