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

"""Scenario-style tests for tool interrupts (human-in-the-loop, respond / restart).

These tests read like app flows: register tools, run a model, pause on interrupt,
then resume. Low-level helpers are only covered where they encode a public contract.
"""

import pytest
from pydantic import BaseModel, Field

from genkit import (
    FinishReason,
    Genkit,
    Message,
    ModelResponse,
    Part,
    Resume,
    Role,
    TextPart,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
    ToolRunContext,
)
from genkit._ai._testing import define_programmable_model
from genkit._ai._tools import Interrupt, ToolInterruptError, define_interrupt
from genkit._core._typing import ToolRequest as TR

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def ai() -> Genkit:
    """Minimal Genkit app (no programmable model)."""
    return Genkit()


@pytest.fixture
def ai_programmable() -> tuple[Genkit, object]:
    """App with a programmable model so we can script multi-turn turns."""
    ai = Genkit(model='echoModel')
    pm, _ = define_programmable_model(ai)
    return ai, pm


# -----------------------------------------------------------------------------
# 1) Direct tool calls — how a developer exercises a tool outside generate()
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_returns_normally_when_no_interrupt(ai: Genkit) -> None:
    """Calling a tool like a plain function returns data when nothing pauses."""

    @ai.tool()
    async def add_one(input: dict) -> dict:
        return {'n': input['n'] + 1}

    out = await add_one({'n': 1})
    assert out == {'n': 2}


@pytest.mark.asyncio
async def test_direct_tool_call_surfaces_interrupt_as_genkit_error(ai: Genkit) -> None:
    """If the tool raises Interrupt, the action wraps it for the caller."""

    @ai.tool()
    async def maybe_stop(input: dict, ctx: ToolRunContext) -> dict:
        if input.get('pause'):
            raise Interrupt({'reason': 'confirm'})
        return {'ok': True}

    from genkit._core._error import GenkitError

    with pytest.raises(GenkitError) as exc:
        await maybe_stop({'pause': True})
    assert isinstance(exc.value.cause, ToolInterruptError)


# -----------------------------------------------------------------------------
# 2) Full generate() flow — user-visible pause, then reply via tool.respond()
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conversation_pauses_on_interrupt_then_continues_after_user_responds(
    ai_programmable: tuple[Genkit, object],
) -> None:
    """Model requests tools; interrupt fires; user sends a response part; model finishes."""

    ai, pm = ai_programmable

    class ToolInput(BaseModel):
        value: int | None = Field(None, description='value field')

    @ai.tool(name='do_math')
    async def do_math(input: ToolInput) -> int:
        """Regular tool."""
        return (input.value or 0) + 7

    @ai.tool(name='ask_user')
    async def ask_user(input: ToolInput, ctx: ToolRunContext) -> None:
        """Human-in-the-loop checkpoint."""
        ctx.interrupt({'needs': 'approval'})

    # Turn 1: model asks for both tools; runtime executes and stops at interrupt.
    tool_request_msg = Message(
        role=Role.MODEL,
        content=[
            Part(root=TextPart(text='call these tools')),
            Part(
                root=ToolRequestPart(
                    tool_request=ToolRequest(input={'value': 5}, name='ask_user', ref='r-ask'),
                )
            ),
            Part(
                root=ToolRequestPart(
                    tool_request=ToolRequest(input={'value': 5}, name='do_math', ref='r-math'),
                )
            ),
        ],
    )
    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=tool_request_msg,
        )
    )
    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='done'))]),
        )
    )

    interrupted = await ai.generate(
        model='programmableModel',
        prompt='hi',
        tools=['do_math', 'ask_user'],
    )

    assert interrupted.finish_reason == 'interrupted'
    assert len(interrupted.interrupts) >= 1
    assert interrupted.interrupts[0].tool_request.name == 'ask_user'

    # Turn 2: user supplies the answer for the interrupt; model completes.
    final = await ai.generate(
        model='programmableModel',
        messages=interrupted.messages,
        tool_responses=[ask_user.respond(interrupted.interrupts[0], {'approved': True})],
        tools=['do_math', 'ask_user'],
    )

    assert final.text == 'done'


@pytest.mark.asyncio
async def test_define_interrupt_is_a_checkpoint_tool(ai_programmable: tuple[Genkit, object]) -> None:
    """ai.define_interrupt registers a tool that always pauses until the user responds."""

    ai, pm = ai_programmable

    class ToolInput(BaseModel):
        value: int | None = Field(None, description='value')

    checkpoint = ai.define_interrupt(
        name='approval_gate',
        input_schema=ToolInput,
        description='Requires approval before continuing',
    )

    tool_request_msg = Message(
        role=Role.MODEL,
        content=[
            Part(root=TextPart(text='need approval')),
            Part(
                root=ToolRequestPart(
                    tool_request=ToolRequest(input={'value': 1}, name='approval_gate', ref='r-g'),
                )
            ),
        ],
    )
    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=tool_request_msg,
        )
    )
    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='approved'))]),
        )
    )

    interrupted = await ai.generate(
        model='programmableModel',
        prompt='run',
        tools=['approval_gate'],
    )

    assert interrupted.finish_reason == 'interrupted'
    assert interrupted.interrupts[0].tool_request.name == 'approval_gate'

    final = await ai.generate(
        model='programmableModel',
        messages=interrupted.messages,
        tool_responses=[checkpoint.respond(interrupted.interrupts[0], {'ok': True})],
        tools=['approval_gate'],
    )

    assert final.text == 'approved'


# -----------------------------------------------------------------------------
# 3) Guardrails — wrong tool, restart shape (still user-visible)
# -----------------------------------------------------------------------------


def test_respond_rejects_interrupt_for_other_tool(ai: Genkit) -> None:
    """tool.respond() must match the tool that produced the interrupt."""

    @ai.tool(name='alpha')
    async def alpha(input: dict) -> dict:
        return {}

    wrong = Part(
        root=ToolRequestPart(
            tool_request=TR(name='beta', ref='x', input={}),
            metadata={'interrupt': True},
        )
    )

    with pytest.raises(ValueError, match="Interrupt is for tool 'beta'"):
        alpha.respond(wrong, {})


def test_restart_carries_revised_input_for_next_execution(ai: Genkit) -> None:
    """After restart, the new request carries the edited input and original in metadata."""

    @ai.tool(name='edit_me')
    async def edit_me(input: dict) -> dict:
        return {}

    interrupt = Part(
        root=ToolRequestPart(
            tool_request=TR(name='edit_me', ref='r1', input={'x': 1}),
            metadata={'interrupt': True},
        )
    )

    restarted = edit_me.restart(interrupt, replace_input={'x': 99})
    assert restarted.root.tool_request.input == {'x': 99}
    assert restarted.root.metadata.get('replacedInput') == {'x': 1}


# -----------------------------------------------------------------------------
# 4) Low-level registry helper (define_interrupt with metadata)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_define_interrupt_helper_with_request_metadata(ai: Genkit) -> None:
    """define_interrupt(registry, ...) still works for custom interrupt metadata."""

    def meta_fn(input: dict) -> dict:
        return {'item': input.get('item')}

    tool = define_interrupt(
        ai.registry,
        None,
        name='confirm',
        description='Confirm',
        request_metadata=meta_fn,
    )

    from genkit._core._error import GenkitError

    with pytest.raises(GenkitError) as exc:
        await tool({'item': 'delete'})

    assert isinstance(exc.value.cause, ToolInterruptError)
    assert exc.value.cause.metadata == {'item': 'delete'}


# -----------------------------------------------------------------------------
# 5) Public Resume type (re-exported for apps)
# -----------------------------------------------------------------------------


def test_resume_type_supports_respond_and_restart_lists() -> None:
    """Resume bundles tool replies or restarts for a follow-up generate call."""
    r = Resume(
        respond=[
            ToolResponsePart(
                tool_response=ToolResponse(name='t', ref='1', output={'a': 1}),
            )
        ],
        restart=[
            ToolRequestPart(
                tool_request=ToolRequest(name='t', ref='1', input={'b': 2}),
            )
        ],
    )
    assert r.respond is not None and r.respond[0].tool_response.name == 't'
    assert r.restart is not None and r.restart[0].tool_request.name == 't'
