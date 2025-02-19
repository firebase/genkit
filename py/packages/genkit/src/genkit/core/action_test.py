#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from genkit.core.action import ActionKind


def test_action_enum_behaves_like_str() -> None:
    """Ensure the ActionType behaves like a string and to ensure we're using the
    correct variants."""
    assert isinstance(ActionKind.CHATLLM, str)
    """Mypy treats enums as distinct types even when they inherit str.
    Suppressed strict equality check for enums."""
    assert ActionKind.CHATLLM == 'chat-llm' # type: ignore[comparison-overlap]
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
