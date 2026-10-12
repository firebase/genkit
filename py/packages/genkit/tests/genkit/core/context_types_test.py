# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""FlowContext and ToolContext: one class hierarchy, generic over the chunk type, found by name in strings."""

from typing import Any, get_origin

import pytest
from typing_extensions import assert_type

from genkit import FlowContext, ToolContext
from genkit._core._action import ActionKind, find_input_and_context
from genkit.plugin_api import ActionRunContext


def test_flow_context_is_action_run_context() -> None:
    """`FlowContext` is the same class plugins import as `ActionRunContext`."""
    assert FlowContext is ActionRunContext


def test_contexts_subscript_at_runtime() -> None:
    """`FlowContext[str]` and `ToolContext[int]` are real generic aliases."""
    assert get_origin(FlowContext[str]) is ActionRunContext
    assert get_origin(ToolContext[int]) is ToolContext
    assert issubclass(ToolContext, FlowContext)


def test_tool_context_is_a_flow_context_for_type_checkers() -> None:
    """A `ToolContext[int]` goes wherever a `FlowContext[int]` is expected; checked by pyright, pyrefly and ty."""

    def plate(ctx: FlowContext[int]) -> FlowContext[int]:
        ctx.send_chunk(3)
        return ctx

    tool_ctx: ToolContext[int] = ToolContext(FlowContext[int]())
    flow_ctx: FlowContext[str] = FlowContext[str]()

    assert_type(plate(tool_ctx), FlowContext[int])
    assert_type(flow_ctx.context, dict[str, Any])
    assert_type(tool_ctx.is_resumed(), bool)


@pytest.mark.parametrize(
    'annotation',
    [
        'FlowContext',
        'ToolContext',
        'ActionRunContext',
        'FlowContext[str]',
        'ToolContext[int]',
        'FlowContext | None',
        'Optional[ToolContext]',
        'genkit.FlowContext',
        'genkit.ToolContext[int] | None',
    ],
)
def test_string_annotation_naming_a_context_marks_the_context(annotation: str) -> None:
    """A string naming FlowContext or ToolContext (as `from __future__` or TYPE_CHECKING leaves it) is the ctx."""

    async def check_allergens(dish: str, ctx: object) -> str:
        return dish

    check_allergens.__annotations__['ctx'] = annotation
    params = find_input_and_context(check_allergens, {'dish': str}, kind=ActionKind.FLOW, name='check_allergens')

    assert params.input is not None and params.input.name == 'dish'
    assert params.context is not None and params.context.name == 'ctx'


@pytest.mark.parametrize('annotation', ['FlowContexts', 'Context', 'ToolContextual', 'str'])
def test_string_annotation_not_naming_a_context_is_a_second_input(annotation: str) -> None:
    """Near-miss names are not the ctx, so a second parameter still raises."""

    async def check_allergens(dish: str, ctx: object) -> str:
        return dish

    check_allergens.__annotations__['ctx'] = annotation

    with pytest.raises(TypeError, match="'ctx' is a second parameter"):
        find_input_and_context(check_allergens, {'dish': str}, kind=ActionKind.FLOW, name='check_allergens')
