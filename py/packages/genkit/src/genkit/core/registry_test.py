#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the registry module.

This module contains unit tests for the Registry class and its associated
functionality, ensuring proper registration and management of Genkit resources.
"""

import pytest
from genkit.core.action import ActionKind
from genkit.core.registry import Registry


def test_register_action_with_name_and_kind() -> None:
    """Ensure we can register an action with a name and kind."""
    registry = Registry()
    action = registry.register_action(
        name='test_action', kind=ActionKind.CUSTOM, fn=lambda x: x
    )
    got = registry.lookup_action(ActionKind.CUSTOM, 'test_action')

    assert got == action
    assert got.name == 'test_action'
    assert got.kind == ActionKind.CUSTOM


def test_lookup_action_by_key() -> None:
    """Ensure we can lookup an action by its key."""
    registry = Registry()
    action = registry.register_action(
        name='test_action', kind=ActionKind.CUSTOM, fn=lambda x: x
    )
    got = registry.lookup_action_by_key('custom/test_action')

    assert got == action
    assert got.name == 'test_action'
    assert got.kind == ActionKind.CUSTOM


def test_lookup_action_by_key_invalid_format() -> None:
    """Ensure lookup_action_by_key handles invalid key format."""
    registry = Registry()
    with pytest.raises(ValueError, match='Invalid action key format'):
        registry.lookup_action_by_key('invalid_key')
    with pytest.raises(ValueError, match='Invalid action key format'):
        registry.lookup_action_by_key('too/many/parts')
