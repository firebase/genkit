# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from genkit.core.typing import (
    GenerateRequest,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.compat_oai.models.model_info import GPT_4
from genkit.plugins.compat_oai.typing import OpenAIConfig


@pytest.fixture
def sample_request():
    """Fixture to create a sample GenerateRequest object."""
    return GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[TextPart(text='Hello, world!')])
        ],
        config=OpenAIConfig(
            model=GPT_4,
            top_p=0.9,
            temperature=0.7,
            stop=['stop'],
            max_tokens=100,
        ),
    )
