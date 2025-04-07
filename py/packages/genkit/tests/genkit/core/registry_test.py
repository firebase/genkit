#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the registry module.

This module contains unit tests for the Registry class and its associated
functionality, ensuring proper registration and management of Genkit resources.
"""

import pytest

from genkit.ai import Genkit, GenkitRegistry, Plugin
from genkit.core.action.types import ActionKind, ActionMetadataKey
from genkit.core.registry import Registry


def test_register_action_with_name_and_kind() -> None:
    """Ensure we can register an action with a name and kind."""
    registry = Registry()
    action = registry.register_action(name='test_action', kind=ActionKind.CUSTOM, fn=lambda x: x)
    got = registry.lookup_action(ActionKind.CUSTOM, 'test_action')

    assert got == action
    assert got.name == 'test_action'
    assert got.kind == ActionKind.CUSTOM


def test_lookup_action_by_key() -> None:
    """Ensure we can lookup an action by its key."""
    registry = Registry()
    action = registry.register_action(name='test_action', kind=ActionKind.CUSTOM, fn=lambda x: x)
    got = registry.lookup_action_by_key('/custom/test_action')

    assert got == action
    assert got.name == 'test_action'
    assert got.kind == ActionKind.CUSTOM


def test_lookup_action_by_key_invalid_format() -> None:
    """Ensure lookup_action_by_key handles invalid key format."""
    registry = Registry()
    with pytest.raises(ValueError, match='Invalid action key format'):
        registry.lookup_action_by_key('invalid_key')


def test_list_serializable_actions() -> None:
    """Ensure we can list serializable actions."""
    registry = Registry()
    registry.register_action(name='test_action', kind=ActionKind.CUSTOM, fn=lambda x: x)

    got = registry.list_serializable_actions()
    assert got == {
        '/custom/test_action': {
            'key': '/custom/test_action',
            'name': 'test_action',
            'inputSchema': {},
            'outputSchema': {},
            'metadata': {
                ActionMetadataKey.INPUT_KEY: {},
                ActionMetadataKey.OUTPUT_KEY: {},
            },
        },
    }


def test_resolve_action_from_plugin():
    resolver_calls = []

    class MyPlugin(Plugin):
        name = 'myplugin'

        def resolve_action(self, ai: GenkitRegistry, kind: ActionKind, name: str):
            nonlocal resolver_calls
            resolver_calls.append([kind, name])

            def model_fn():
                pass

            ai.define_model(name=name, fn=model_fn)

        def initialize(self, ai: GenkitRegistry) -> None:
            pass

    ai = Genkit(plugins=[MyPlugin()])

    action = ai.registry.lookup_action(ActionKind.MODEL, 'myplugin/foo')

    assert action is not None
    assert len(resolver_calls) == 1

    assert resolver_calls == [[ActionKind.MODEL, 'myplugin/foo']]

    # should be idempotent
    ai.registry.lookup_action(ActionKind.MODEL, 'myplugin/foo')
    assert len(resolver_calls) == 1


def test_register_value():
    registry = Registry()

    registry.register_value('format', 'json', [1, 2, 3])

    assert registry.lookup_value('format', 'json') == [1, 2, 3]
