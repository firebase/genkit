# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for v2 plugin support.

Focused on key product requirements, not code coverage.
Tests verify that v2 plugins work standalone and with framework,
and that v1 plugins continue working (backward compatibility).
"""

import pytest

from genkit.ai import Genkit
from genkit.ai._plugin import PluginV2, is_plugin_v2
from genkit.core.action import Action, ActionMetadata
from genkit.core.registry import ActionKind
from genkit.types import (
    Candidate,
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)


# Helper: Simple v2 test plugin
class SimpleV2Plugin(PluginV2):
    """Minimal v2 plugin for testing."""

    name = "test-v2"

    def __init__(self, models: list[str] | None = None):
        self._models = models or ["model-1"]

    def init(self):
        from genkit.blocks.model import model

        return [
            model(
                name=m,
                fn=self._generate,
            )
            for m in self._models
        ]

    def resolve(self, action_type, name):
        from genkit.blocks.model import model

        # Framework passes unprefixed name
        if action_type == ActionKind.MODEL and name in ["model-1", "model-2", "lazy-model"]:
            return model(name=name, fn=self._generate)
        return None

    def list_actions(self):
        return [
            ActionMetadata(name=m, kind=ActionKind.MODEL, info={})
            for m in ["model-1", "model-2"]
        ]

    # model() method inherited from PluginV2 base class

    def _generate(self, request: GenerateRequest, ctx):
        """Simple test model that echoes input."""
        input_text = request.messages[0].content[0].text if request.messages else "empty"
        return GenerateResponse(
            candidates=[
                Candidate(
                    message=Message(
                        role=Role.MODEL, content=[TextPart(text=f"TEST: {input_text}")]
                    )
                )
            ]
        )


# Test 1: V2 plugins return actions
def test_v2_plugin_init_returns_actions():
    """V2 plugin init() should return list of Action objects."""
    plugin = SimpleV2Plugin(models=["model-1", "model-2"])

    actions = plugin.init()

    assert isinstance(actions, list)
    assert len(actions) == 2
    assert all(isinstance(a, Action) for a in actions)
    assert actions[0].name == "model-1"
    assert actions[0].kind == ActionKind.MODEL


# Test 2: V2 plugins work standalone
@pytest.mark.asyncio
async def test_v2_plugin_works_standalone():
    """V2 plugin should work WITHOUT Genkit framework."""
    # Create plugin - NO Genkit instance
    plugin = SimpleV2Plugin()

    # Get an action
    action = plugin.resolve(ActionKind.MODEL, "model-1")

    # Call it directly
    response = await action.arun({"messages": [{"role": "user", "content": [{"text": "hello"}]}]})

    assert response is not None
    assert response.response.candidates[0].message.content[0].text == "TEST: hello"


# Test 3: V2 plugins work with framework
@pytest.mark.asyncio
async def test_v2_plugin_works_with_framework():
    """V2 plugin should work WITH Genkit framework."""
    plugin = SimpleV2Plugin()

    ai = Genkit(plugins=[plugin])

    response = await ai.generate("test-v2/model-1", prompt="framework test")

    assert response.text is not None
    assert "TEST:" in response.text


# Test 4: Framework supports both v1 and v2
@pytest.mark.asyncio
async def test_framework_accepts_v2_plugin():
    """Framework should accept v2 plugins."""
    plugin = SimpleV2Plugin()

    ai = Genkit(plugins=[plugin])

    response = await ai.generate("test-v2/model-1", prompt="test")

    assert response.text is not None


# Test 5: Lazy loading
@pytest.mark.asyncio
async def test_v2_lazy_loading():
    """V2 plugin should support lazy loading via resolve()."""
    # Plugin with NO eager models
    plugin = SimpleV2Plugin(models=[])

    ai = Genkit(plugins=[plugin])

    # init() returned empty, but resolve() should work
    response = await ai.generate("test-v2/lazy-model", prompt="test")

    assert response.text is not None
    assert "TEST:" in response.text


# Test 6: Automatic namespacing
@pytest.mark.asyncio
async def test_v2_automatic_namespacing():
    """Framework should add namespace automatically."""
    plugin = SimpleV2Plugin()

    # Plugin returns action WITHOUT namespace
    actions = plugin.init()
    assert actions[0].name == "model-1"  # No prefix

    # Framework adds namespace
    ai = Genkit(plugins=[plugin])

    # Must use namespaced name
    response = await ai.generate("test-v2/model-1", prompt="test")
    assert response.text is not None


# Test 7: List actions
def test_v2_list_actions():
    """V2 plugin list_actions() should return metadata."""
    plugin = SimpleV2Plugin()

    metadata = plugin.list_actions()

    assert isinstance(metadata, list)
    assert len(metadata) == 2
    assert all(isinstance(m, ActionMetadata) for m in metadata)


# Test 8: Detection function
def test_is_plugin_v2_detection():
    """is_plugin_v2() should correctly detect v2 plugins."""
    from genkit.ai._plugin import Plugin

    v2_plugin = SimpleV2Plugin()

    # Create a simple v1 plugin for testing
    class SimpleV1Plugin(Plugin):
        name = "test-v1"

        def initialize(self, ai):
            pass

    v1_plugin = SimpleV1Plugin()

    assert is_plugin_v2(v2_plugin) is True
    assert is_plugin_v2(v1_plugin) is False
    assert is_plugin_v2("not a plugin") is False


# Test 9: model() factory
def test_model_factory_creates_action():
    """model() factory should create Action without registry."""
    from genkit.blocks.model import model

    def dummy_fn(request, ctx):
        return GenerateResponse(
            candidates=[
                Candidate(
                    message=Message(role=Role.MODEL, content=[TextPart(text="test")])
                )
            ]
        )

    action = model(name="test-model", fn=dummy_fn)

    assert isinstance(action, Action)
    assert action.name == "test-model"
    assert action.kind == ActionKind.MODEL


# Test 10: Convenience method
@pytest.mark.asyncio
async def test_v2_plugin_model_convenience_method():
    """V2 plugin.model() should provide convenient access."""
    plugin = SimpleV2Plugin()

    # Get model via convenience method
    action = await plugin.model("model-1")

    assert isinstance(action, Action)
    assert action.name == "model-1"

    # Should raise for non-existent model
    with pytest.raises(ValueError, match="not found"):
        await plugin.model("nonexistent-model")


