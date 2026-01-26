#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Genkit extra API methods."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from genkit.ai import Genkit
from genkit.core.action import Action, ActionRunContext
from genkit.core.action.types import ActionKind
from genkit.core.typing import Operation, SpanMetadata
from genkit.types import DocumentData, TextPart, Part, RetrieverRequest, RetrieverResponse

@pytest.mark.asyncio
async def test_genkit_run():
    ai = Genkit()
    
    def sync_fn():
        return "hello"
    
    async def async_fn():
        return "world"
    
    res1 = await ai.run("test1", sync_fn)
    assert res1 == "hello"
    
    res2 = await ai.run("test2", async_fn)
    assert res2 == "world"
    
    # Test with metadata
    res3 = await ai.run("test3", sync_fn, metadata={"foo": "bar"})
    assert res3 == "hello"

@pytest.mark.asyncio
async def test_genkit_dynamic_tool():
    ai = Genkit()
    
    def my_tool(x: int) -> int:
        return x + 1
        
    tool = ai.dynamic_tool("my_tool", my_tool, description="increment x")
    
    assert isinstance(tool, Action)
    assert tool.kind == ActionKind.TOOL
    assert tool.name == "my_tool"
    assert tool.description == "increment x"
    
    # Execution
    resp = await tool.arun(5)
    assert resp.response == 6

@pytest.mark.asyncio
async def test_genkit_check_operation():
    ai = Genkit()
    
    op = Operation(id="123", done=False, action="test_action")
    
    mock_action = AsyncMock()
    mock_action.arun.return_value = MagicMock(response=Operation(id="123", done=True, output="result"))
    
    # Mock registry.resolve_action_by_key
    ai.registry.resolve_action_by_key = AsyncMock(return_value=mock_action)
    
    updated_op = await ai.check_operation(op)
    
    assert updated_op.done is True
    assert updated_op.output == "result"
    ai.registry.resolve_action_by_key.assert_called_with("test_action")

@pytest.mark.asyncio
async def test_genkit_check_operation_no_action():
    ai = Genkit()
    op = Operation(id="123", done=False) # action is None
    
    with pytest.raises(ValueError, match="Operation must have an action specified"):
        await ai.check_operation(op)

@pytest.mark.asyncio
async def test_genkit_check_operation_not_found():
    ai = Genkit()
    op = Operation(id="123", done=False, action="missing")
    ai.registry.resolve_action_by_key = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match='Action "missing" not found'):
        await ai.check_operation(op)

@pytest.mark.asyncio
async def test_define_simple_retriever():
    ai = Genkit()
    
    def simple_retriever(req: RetrieverRequest):
        # Returns list[DocumentData] directly
        # DocumentData.content takes list[DocumentPart], which includes TextPart
        return [DocumentData(content=[TextPart(text="doc1")])]
        
    retriever_action = ai.define_simple_retriever("simple", simple_retriever)
    
    assert retriever_action.kind == ActionKind.RETRIEVER
    
    # Test execution
    req = RetrieverRequest(query=DocumentData(content=[]))
    resp_wrapper = await retriever_action.arun(req)
    response = resp_wrapper.response
    
    assert isinstance(response, RetrieverResponse)
    assert len(response.documents) == 1
    assert response.documents[0].content[0].root.text == "doc1"

@pytest.mark.asyncio
async def test_current_context():
    from genkit.core.action._action import _action_context
    
    # current_context is a static method
    assert Genkit.current_context() is None
    
    context = {"auth": {"uid": "123"}}
    
    # Simulate being inside an action run using ActionRunContext internal mechanism
    token = _action_context.set(context)
    try:
        assert Genkit.current_context() == context
    finally:
        _action_context.reset(token)
    
    assert Genkit.current_context() is None

@pytest.mark.asyncio
async def test_flush_tracing():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry import trace as trace_api
    
    ai = Genkit()
    
    mock_provider = MagicMock(spec=TracerProvider)
    mock_provider.force_flush = MagicMock()
    
    # We can't easily mock the global provider if it's already set, 
    # but we can check if it calls force_flush if it is a TracerProvider.
    
    original_provider = trace_api.get_tracer_provider()
    trace_api.set_tracer_provider(mock_provider)
    try:
        await ai.flush_tracing()
        mock_provider.force_flush.assert_called_once()
    finally:
        # Note: set_tracer_provider can only be called once in real OTel, 
        # but in tests we might be using a mock.
        pass
