#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from genkit.core.action import ActionKind, parse_action_key


def test_action_enum_behaves_like_str() -> None:
    """Ensure the ActionType behaves like a string and to ensure we're using the
    correct variants."""
    assert ActionKind.CHATLLM == 'chat-llm'
    assert ActionKind.CUSTOM == 'custom'
    assert ActionKind.EMBEDDER == 'embedder'
    assert ActionKind.EVALUATOR == 'evaluator'
    assert ActionKind.FLOW == 'flow'
    assert ActionKind.INDEXER == 'indexer'
    assert ActionKind.MODEL == 'model'
    assert ActionKind.PROMPT == 'prompt'
    assert ActionKind.RETRIEVER == 'retriever'
    assert ActionKind.TEXTLLM == 'text-llm'
    assert ActionKind.TOOL == 'tool'
    assert ActionKind.UTIL == 'util'


def test_parse_action_key_valid() -> None:
    """Test valid inputs."""
    test_cases = [
        ('prompt/my-prompt', (ActionKind.PROMPT, 'my-prompt')),
        ('model/gpt-4', (ActionKind.MODEL, 'gpt-4')),
        ('custom/test-action', (ActionKind.CUSTOM, 'test-action')),
        ('flow/my-flow', (ActionKind.FLOW, 'my-flow')),
    ]

    for key, expected in test_cases:
        kind, name = parse_action_key(key)
        assert kind == expected[0]
        assert name == expected[1]


def test_parse_action_key_invalid_format() -> None:
    """Test invalid formats."""
    invalid_keys = [
        'invalid_key',  # Missing separator
        'too/many/parts',  # Too many parts
        '/missing-kind',  # Missing kind
        'missing-name/',  # Missing name
        '',  # Empty string
        '/',  # Just separator
    ]

    for key in invalid_keys:
        with pytest.raises(ValueError, match='Invalid action key format'):
            parse_action_key(key)


def test_parse_action_key_invalid_kind() -> None:
    """Test invalid action kinds."""
    with pytest.raises(ValueError, match='Invalid action kind'):
        parse_action_key('invalid-kind/my-action')
