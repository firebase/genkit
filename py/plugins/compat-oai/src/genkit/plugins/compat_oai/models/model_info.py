# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI Compatible Models for Genkit.
"""

from genkit.core.typing import (
    ModelInfo,
    Supports,
)

GPT_3_5_TURBO = 'gpt-3.5-turbo'
GPT_4 = 'gpt-4'
GPT_4_TURBO = 'gpt-4-turbo'
GPT_4O = 'gpt-4o'
GPT_4O_MINI = 'gpt-4o-mini'
O1_MINI = 'o1-mini'

SUPPORTED_OPENAI_MODELS: dict[str, ModelInfo] = {
    GPT_3_5_TURBO: ModelInfo(
        label='OpenAI - gpt-3.5-turbo',
        versions=[
            'gpt-3.5-turbo-1106',
            'gpt-3.5-turbo-0125',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
        ),
    ),
    GPT_4O: ModelInfo(
        label='OpenAI - gpt-4o',
        versions=[
            'gpt-4o-2024-11-20',
            'gpt-4o-2024-08-06',
            'gpt-4o-2024-05-13',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
        ),
    ),
    GPT_4O_MINI: ModelInfo(
        label='OpenAI - gpt-4o-mini',
        versions=[
            'gpt-4o-mini-2024-07-18',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
        ),
    ),
    O1_MINI: ModelInfo(
        label='OpenAI - o1-mini',
        versions=[
            'o1-mini-2024-09-12',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
        ),
    ),
    GPT_4: ModelInfo(
        label='OpenAI - GPT-4',
        versions=[
            'gpt-4-0613',
            'gpt-4-1106-preview',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
        ),
    ),
    GPT_4_TURBO: ModelInfo(
        label='OpenAI - GPT-4 Turbo',
        versions=[
            'gpt-4-turbo-2024-04-09',
            'gpt-4-turbo-preview',
        ],
        supports=Supports(
            multiturn=True,
            media=False,
            tools=True,
            systemRole=True,
        ),
    ),
}
