#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the message utils."""

from genkit.blocks.messages import inject_instructions
from genkit.core.typing import (
    Message,
    Metadata,
    Role,
    TextPart,
)


def test_inject_instructions_user_message() -> None:
    result = inject_instructions(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text='hello'), TextPart(text='world')],
            )
        ],
        instructions='injected',
    )

    assert result == [
        Message(
            role=Role.USER,
            content=[
                TextPart(text='hello'),
                TextPart(text='world'),
                TextPart(
                    text='injected',
                    metadata=Metadata(root={'purpose': 'output'}),
                ),
            ],
            metadata=None,
        )
    ]


def test_inject_instructions_system_message() -> None:
    """Tests that it injects into the system message."""
    result = inject_instructions(
        messages=[
            Message(
                role=Role.SYSTEM,
                content=[TextPart(text='system'), TextPart(text='message')],
            ),
            Message(
                role=Role.USER,
                content=[TextPart(text='hello'), TextPart(text='world')],
            ),
        ],
        instructions='injected',
    )

    assert result == [
        Message(
            role=Role.SYSTEM,
            content=[
                TextPart(text='system'),
                TextPart(text='message'),
                TextPart(
                    text='injected',
                    metadata=Metadata(root={'purpose': 'output'}),
                ),
            ],
            metadata=None,
        ),
        Message(
            role=Role.USER,
            content=[
                TextPart(text='hello'),
                TextPart(text='world'),
            ],
            metadata=None,
        ),
    ]


def test_inject_instructions_purpose() -> None:
    """Tests that it injects into message with purpose metadata."""
    result = inject_instructions(
        messages=[
            Message(
                role=Role.SYSTEM,
                content=[TextPart(text='system'), TextPart(text='message')],
            ),
            Message(
                role=Role.USER,
                content=[
                    TextPart(
                        text='will be overridden',
                        metadata=Metadata(root={'purpose': 'output', 'pending': True}),
                    ),
                    TextPart(text='world'),
                ],
            ),
        ],
        instructions='injected',
    )

    assert result == [
        Message(
            role=Role.SYSTEM,
            content=[
                TextPart(text='system'),
                TextPart(text='message'),
            ],
            metadata=None,
        ),
        Message(
            role=Role.USER,
            content=[
                TextPart(
                    text='injected',
                    metadata=Metadata(root={'purpose': 'output'}),
                ),
                TextPart(text='world'),
            ],
            metadata=None,
        ),
    ]


def test_inject_instructions_short_circuit() -> None:
    """Tests that it slips injection when injected data already present."""
    result = inject_instructions(
        messages=[
            Message(
                role=Role.SYSTEM,
                content=[TextPart(text='system'), TextPart(text='message')],
            ),
            Message(
                role=Role.USER,
                content=[
                    TextPart(
                        text='previously injected',
                        metadata=Metadata(root={'purpose': 'output'}),
                    ),
                    TextPart(text='world'),
                ],
            ),
        ],
        instructions='injected',
    )

    assert result == [
        Message(
            role=Role.SYSTEM,
            content=[
                TextPart(text='system'),
                TextPart(text='message'),
            ],
            metadata=None,
        ),
        Message(
            role=Role.USER,
            content=[
                TextPart(
                    text='previously injected',
                    metadata=Metadata(root={'purpose': 'output'}),
                ),
                TextPart(text='world'),
            ],
            metadata=None,
        ),
    ]
