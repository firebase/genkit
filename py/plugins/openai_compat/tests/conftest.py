# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from genkit.core.typing import (
    GenerateRequest,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.openai_compat.models.model_info import GPT_4


@pytest.fixture
def sample_request():
    """Fixture to create a sample GenerateRequest object."""
    return GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[TextPart(text='Hello, world!')])
        ],
        config=GenerationCommonConfig(
            version=GPT_4,
            top_p=0.9,
            temperature=0.7,
            stop_sequences=['stop'],
            max_output_tokens=100,
        ),
    )
