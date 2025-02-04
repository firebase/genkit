# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from genkit.core.types import Message, TextPart, Role
from genkit.plugins.ollama.models import (
    OllamaPluginParams,
    ModelDefinition,
    OllamaAPITypes,
)
from genkit.plugins.ollama import Ollama

from genkit.veneer import Genkit


# model can be pulled with `ollama pull *LLM_VERSION*`
LLM_VERSION = 'llama3.2:latest'

plugin_params = OllamaPluginParams(
    models=[
        ModelDefinition(
            name=LLM_VERSION,
            api_type=OllamaAPITypes.CHAT,
        )
    ],
)

ai = Genkit(
    plugins=[
        Ollama(
            plugin_params=plugin_params,
        )
    ],
    model=f'ollama/{LLM_VERSION}',
)


@ai.flow()
def say_hi(input: str):
    return ai.generate(
        messages=[
            Message(
                role=Role.user,
                content=[
                    TextPart(text='hi ' + input),
                ],
            )
        ]
    )


def main() -> None:
    print(say_hi('John Doe'))


if __name__ == '__main__':
    main()
