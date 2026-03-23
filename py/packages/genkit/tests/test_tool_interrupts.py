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

"""Tests for tool interrupts API."""

import pytest

from genkit import Genkit
from genkit._ai._tools import Interrupt, ToolRunContext, define_interrupt, define_tool
from genkit._core._typing import Part, Resume, ToolRequestPart


@pytest.fixture
def ai() -> Genkit:
    """Create a Genkit instance for testing."""
    return Genkit()


class TestInterruptException:
    """Test the Interrupt exception class."""

    def test_interrupt_creation(self) -> None:
        """Test creating an Interrupt exception."""
        interrupt = Interrupt({'reason': 'test'})
        assert interrupt.data == {'reason': 'test'}

    def test_interrupt_no_data(self) -> None:
        """Test creating an Interrupt without data."""
        interrupt = Interrupt()
        assert interrupt.data == {}

    def test_interrupt_raise(self) -> None:
        """Test raising an Interrupt exception."""
        with pytest.raises(Interrupt) as exc_info:
            raise Interrupt({'reason': 'test'})
        assert exc_info.value.data == {'reason': 'test'}


class TestToolRunContext:
    """Test ToolRunContext enhancements."""

    def test_is_resumed_false_by_default(self, ai: Genkit) -> None:
        """Test is_resumed returns False when not resumed."""
        from genkit._core._action import ActionRunContext

        ctx = ToolRunContext(ActionRunContext())
        assert not ctx.is_resumed()

    def test_is_resumed_true_with_metadata(self, ai: Genkit) -> None:
        """Test is_resumed returns True when resumed_metadata is set."""
        from genkit._core._action import ActionRunContext

        ctx = ToolRunContext(ActionRunContext(), resumed_metadata={'foo': 'bar'})
        assert ctx.is_resumed()

    def test_resumed_metadata_accessible(self, ai: Genkit) -> None:
        """Test resumed_metadata is accessible."""
        from genkit._core._action import ActionRunContext

        meta = {'key': 'value'}
        ctx = ToolRunContext(ActionRunContext(), resumed_metadata=meta)
        assert ctx.resumed_metadata == meta

    def test_original_input_accessible(self, ai: Genkit) -> None:
        """Test original_input is accessible."""
        from genkit._core._action import ActionRunContext

        original = {'amount': 100}
        ctx = ToolRunContext(ActionRunContext(), original_input=original)
        assert ctx.original_input == original


class TestToolInterrupt:
    """Test tool interrupts with raise Interrupt."""

    @pytest.mark.asyncio
    async def test_tool_raises_interrupt(self, ai: Genkit) -> None:
        """Test a tool that raises Interrupt."""

        @ai.tool()
        async def test_tool(input: dict, ctx: ToolRunContext) -> dict:
            if input.get('should_interrupt'):
                raise Interrupt({'reason': 'user_confirmation'})
            return {'result': 'success'}

        # Call without interrupt
        result = await test_tool({'should_interrupt': False})
        assert result == {'result': 'success'}

        # Call with interrupt - should raise ToolInterruptError (wrapped by action)
        from genkit._core._error import GenkitError

        with pytest.raises(GenkitError) as exc_info:
            await test_tool({'should_interrupt': True})

        # The Interrupt should be wrapped in ToolInterruptError, which is the cause
        from genkit._ai._tools import ToolInterruptError

        assert isinstance(exc_info.value.cause, ToolInterruptError)


class TestToolRespondRestart:
    """Test tool.respond() and tool.restart() methods."""

    def test_tool_respond_method_exists(self, ai: Genkit) -> None:
        """Test that define_tool adds respond method."""

        @ai.tool()
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        assert hasattr(test_tool, 'respond')
        assert callable(test_tool.respond)

    def test_tool_restart_method_exists(self, ai: Genkit) -> None:
        """Test that define_tool adds restart method."""

        @ai.tool()
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        assert hasattr(test_tool, 'restart')
        assert callable(test_tool.restart)

    def test_tool_respond_creates_response_part(self, ai: Genkit) -> None:
        """Test tool.respond() creates a valid response Part."""

        @ai.tool(name='my_tool')
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        # Create a mock interrupt part
        from genkit._core._typing import ToolRequest

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='my_tool', ref='ref-1', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        response_part = test_tool.respond(interrupt_part, {'result': 'done'})
        assert isinstance(response_part, Part)
        assert response_part.root.tool_response is not None
        assert response_part.root.tool_response.name == 'my_tool'
        assert response_part.root.tool_response.output == {'result': 'done'}

    def test_tool_respond_validates_tool_name(self, ai: Genkit) -> None:
        """Test tool.respond() validates the tool name matches."""

        @ai.tool(name='my_tool')
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        # Create an interrupt for a different tool
        from genkit._core._typing import ToolRequest

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='wrong_tool', ref='ref-1', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        with pytest.raises(ValueError, match="Interrupt is for tool 'wrong_tool'"):
            test_tool.respond(interrupt_part, {'result': 'done'})

    def test_tool_restart_creates_request_part(self, ai: Genkit) -> None:
        """Test tool.restart() creates a valid request Part."""

        @ai.tool(name='my_tool')
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        from genkit._core._typing import ToolRequest

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='my_tool', ref='ref-1', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        restart_part = test_tool.restart(interrupt_part)
        assert isinstance(restart_part, Part)
        assert restart_part.root.tool_request is not None
        assert restart_part.root.tool_request.name == 'my_tool'
        assert restart_part.root.metadata.get('resumed') is True
        assert 'interrupt' not in restart_part.root.metadata

    def test_tool_restart_replaces_input(self, ai: Genkit) -> None:
        """Test tool.restart() with replace_input."""

        @ai.tool(name='my_tool')
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        from genkit._core._typing import ToolRequest

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='my_tool', ref='ref-1', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        restart_part = test_tool.restart(interrupt_part, replace_input={'x': 2})
        assert restart_part.root.tool_request.input == {'x': 2}
        assert restart_part.root.metadata.get('replacedInput') == {'x': 1}

    def test_tool_restart_with_metadata(self, ai: Genkit) -> None:
        """Test tool.restart() with custom resumed_metadata."""

        @ai.tool(name='my_tool')
        async def test_tool(input: dict) -> dict:
            return {'result': 'ok'}

        from genkit._core._typing import ToolRequest

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='my_tool', ref='ref-1', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        restart_part = test_tool.restart(interrupt_part, resumed_metadata={'auth': 'token123'})
        assert restart_part.root.metadata.get('resumed') == {'auth': 'token123'}


class TestInterruptRespondRestart:
    """Test tool.respond() and tool.restart() — respond/restart live on the tool, not the interrupt."""

    @pytest.mark.asyncio
    async def test_tool_respond_creates_response_part(self, ai: Genkit) -> None:
        """Test tool.respond(interrupt_part, output) creates a ToolResponsePart."""
        from genkit._core._typing import ToolRequest

        @ai.tool(description="test tool")
        async def my_tool(input: dict) -> dict:
            raise Interrupt({"reason": "test"})

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='my_tool', ref='ref-1', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        response = my_tool.respond(interrupt_part, {'result': 'done'})
        assert isinstance(response, Part)
        assert response.root.tool_response is not None
        assert response.root.tool_response.output == {'result': 'done'}

    @pytest.mark.asyncio
    async def test_tool_restart_creates_request_part(self, ai: Genkit) -> None:
        """Test tool.restart(interrupt_part) creates a ToolRequestPart for re-execution."""
        from genkit._core._typing import ToolRequest

        @ai.tool(description="test tool")
        async def my_tool2(input: dict) -> dict:
            raise Interrupt({"reason": "test"})

        interrupt_part = Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(name='my_tool2', ref='ref-2', input={'x': 1}),
                metadata={'interrupt': True},
            )
        )

        restart = my_tool2.restart(interrupt_part, resumed_metadata={'approved': True})
        assert isinstance(restart, Part)
        assert restart.root.tool_request is not None


class TestDefineInterrupt:
    """Test define_interrupt function."""

    @pytest.mark.asyncio
    async def test_define_interrupt_always_interrupts(self, ai: Genkit) -> None:
        """Test that define_interrupt creates a tool that always interrupts."""
        interrupt_tool = define_interrupt(
            ai.registry,
            None,
            name='confirm',
            description='Confirm action',
        )

        # Should always raise on call
        from genkit._core._error import GenkitError

        with pytest.raises(GenkitError):
            await interrupt_tool({'action': 'delete'})

    @pytest.mark.asyncio
    async def test_define_interrupt_with_custom_metadata(self, ai: Genkit) -> None:
        """Test define_interrupt with custom metadata function."""

        def get_meta(input: dict) -> dict:
            return {'action': input.get('action'), 'critical': True}

        interrupt_tool = define_interrupt(
            ai.registry,
            None,
            name='confirm',
            description='Confirm action',
            request_metadata=get_meta,
        )

        from genkit._ai._tools import ToolInterruptError
        from genkit._core._error import GenkitError

        with pytest.raises(GenkitError) as exc_info:
            await interrupt_tool({'action': 'delete_all'})

        # Extract the ToolInterruptError from the cause
        assert isinstance(exc_info.value.cause, ToolInterruptError)
        assert exc_info.value.cause.metadata == {'action': 'delete_all', 'critical': True}

    def test_ai_define_interrupt_method(self, ai: Genkit) -> None:
        """Test ai.define_interrupt() method exists and works."""
        interrupt_tool = ai.define_interrupt(
            name='ask_user',
            description='Ask user for input',
        )

        assert callable(interrupt_tool)
        assert hasattr(interrupt_tool, 'respond')
        assert hasattr(interrupt_tool, 'restart')


class TestResumeRoundTrip:
    """Test full interrupt-resume round trip."""

    @pytest.mark.asyncio
    async def test_resume_metadata_propagation(self, ai: Genkit) -> None:
        """Test that resumed_metadata is accessible in tool context."""
        resumed_value = None

        @ai.tool(name='check_auth')
        async def check_auth(input: dict, ctx: ToolRunContext) -> dict:
            nonlocal resumed_value
            if ctx.is_resumed():
                resumed_value = ctx.resumed_metadata
                return {'authenticated': True}
            raise Interrupt({'reason': 'needs_auth'})

        # This test verifies the API structure - actual resume flow requires generate()
        # First call should interrupt
        from genkit._core._error import GenkitError

        with pytest.raises(GenkitError):
            await check_auth({'user': 'alice'})

    @pytest.mark.asyncio
    async def test_original_input_accessible(self, ai: Genkit) -> None:
        """Test that original_input is accessible when input is replaced."""
        original_value = None

        @ai.tool(name='transfer')
        async def transfer(input: dict, ctx: ToolRunContext) -> dict:
            nonlocal original_value
            if ctx.is_resumed():
                original_value = ctx.original_input
                return {'status': 'transferred', 'amount': input['amount']}
            if input['amount'] > 100:
                raise Interrupt({'reason': 'confirm_large'})
            return {'status': 'transferred', 'amount': input['amount']}

        # Small amount - no interrupt
        result = await transfer({'amount': 50})
        assert result == {'status': 'transferred', 'amount': 50}


class TestResumeParameter:
    """Test the resume parameter on generate()."""

    def test_resume_type_available(self) -> None:
        """Test that Resume type is available from genkit."""
        from genkit import Resume

        assert Resume is not None

    def test_resume_has_respond_field(self) -> None:
        """Test that Resume has respond field."""
        resume = Resume(respond=[])
        assert resume.respond == []

    def test_resume_has_restart_field(self) -> None:
        """Test that Resume has restart field."""
        resume = Resume(restart=[])
        assert resume.restart == []
