# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import threading

import pytest
from genkit.core.schema_types import (
    GenerateRequest,
    Message,
    Part,
    Role,
    TextPart,
    ToolRequestPart,
)

action_callback_event = threading.Event()


@pytest.fixture
def mock_generate_request() -> ToolRequestPart:
    return GenerateRequest(
        messages=[
            Message(
                role=Role.user,
                content=[
                    Part(
                        root=TextPart(text='Hello world!'),
                    )
                ],
            )
        ]
    )
