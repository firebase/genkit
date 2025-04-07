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

"""Test tool calling."""

from unittest.mock import MagicMock

from genkit.ai import ActionKind
from genkit.plugins.compat_oai.models import OpenAIModel
from genkit.plugins.compat_oai.models.model_info import GPT_4
from genkit.types import GenerateRequest, GenerateResponseChunk


def test_get_evaluated_tool_message_param_returns_expected_message() -> None:
    """Test get evaluated tool message param returns expected message."""
    tool_call = MagicMock()
    tool_call.id = 'abc123'
    tool_call.function.name = 'tool_fn'
    tool_call.function.arguments = '{"key": "val"}'

    model = OpenAIModel(model=GPT_4, client=MagicMock(), registry=MagicMock())
    model._evaluate_tool = MagicMock(return_value='tool_result')

    result = model._get_evaluated_tool_message_param(tool_call)
    assert result['role'] == 'tool'
    assert result['tool_call_id'] == 'abc123'
    assert result['content'] == 'tool_result'


def test_evaluate_tool_executes_registered_action() -> None:
    """Test evaluate tool executes registered action."""
    mock_action = MagicMock()
    mock_action.input_type.validate_python.return_value = {'a': 1}
    mock_action.run.return_value = 'result'

    mock_registry = MagicMock()
    mock_registry.registry.lookup_action.return_value = mock_action

    model = OpenAIModel(model=GPT_4, client=MagicMock(), registry=mock_registry)

    result = model._evaluate_tool('my_tool', '{"a": 1}')
    mock_registry.registry.lookup_action.assert_called_once_with(ActionKind.TOOL, 'my_tool')
    mock_action.input_type.validate_python.assert_called_once_with({'a': 1})
    mock_action.run.assert_called_once_with({'a': 1})
    assert result == 'result'


def test_generate_with_tool_calls_executes_tools(sample_request: GenerateRequest) -> None:
    """Test generate with tool calls executes tools."""
    mock_tool_call = MagicMock()
    mock_tool_call.id = 'tool123'
    mock_tool_call.function.name = 'tool_fn'
    mock_tool_call.function.arguments = '{"a": 1}'

    # First call triggers tool execution
    first_response = MagicMock()
    first_response.choices = [
        MagicMock(
            finish_reason='tool_calls',
            message=MagicMock(tool_calls=[mock_tool_call]),
        )
    ]
    # Second call is the model response
    second_response = MagicMock()
    second_response.choices = [MagicMock(finish_reason='stop', message=MagicMock(content='final response'))]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        first_response,
        second_response,
    ]

    mock_action = MagicMock()
    mock_action.input_type.validate_python.return_value = {'a': 1}
    mock_action.run.return_value = 'tool result'

    mock_registry = MagicMock()
    mock_registry.registry.lookup_action.return_value = mock_action

    model = OpenAIModel(model=GPT_4, client=mock_client, registry=mock_registry)

    response = model.generate(sample_request)

    assert response.message.content[0].root.text == 'final response'
    assert mock_client.chat.completions.create.call_count == 2


def test_generate_stream_with_tool_calls(sample_request):
    mock_tool_call = MagicMock()
    mock_tool_call.id = 'tool123'
    mock_tool_call.index = 0
    mock_tool_call.function.name = 'tool_fn'
    mock_tool_call.function.arguments = ''

    # First chunk: tool call starts
    chunk1 = MagicMock()
    chunk1.choices = [
        MagicMock(
            index=0,
            delta=MagicMock(
                content=None,
                tool_calls=[mock_tool_call],
            ),
        )
    ]

    # Second chunk: continuation of tool call arguments
    chunk2 = MagicMock()
    chunk2.choices = [
        MagicMock(
            index=0,
            delta=MagicMock(
                content=None,
                tool_calls=[
                    MagicMock(
                        index=0,
                        function=MagicMock(arguments='{"a": "123"}'),
                        id='tool123',
                    )
                ],
            ),
        )
    ]

    # Third stream after tool execution: final model response
    final_chunk = MagicMock()
    final_chunk.choices = [
        MagicMock(
            index=0,
            delta=MagicMock(content='final stream content', tool_calls=None),
        )
    ]

    # Simulate the streaming lifecycle
    class MockStream:
        def __init__(self, chunks):
            self._chunks = chunks
            self._current = 0
            self.response = MagicMock()
            self.response.is_closed = False

        def __iter__(self):
            return self

        def __next__(self):
            if self._current >= len(self._chunks):
                self.response.is_closed = True
                raise StopIteration
            chunk = self._chunks[self._current]
            self._current += 1
            return chunk

    # First stream: tool call chunks
    first_stream = MockStream([chunk1, chunk2])
    # Second stream: model output after tool is processed
    second_stream = MockStream([final_chunk])

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        first_stream,
        second_stream,
    ]

    # Set up mock tool evaluation
    mock_action = MagicMock()
    mock_action.input_type.validate_python.return_value = {'a': '123'}
    mock_action.run.return_value = 'tool response'

    mock_registry = MagicMock()
    mock_registry.registry.lookup_action.return_value = mock_action

    model = OpenAIModel(model=GPT_4, client=mock_client, registry=mock_registry)

    chunks = []

    def callback(chunk: GenerateResponseChunk):
        chunks.append(chunk.content[0].root.text)

    model.generate_stream(sample_request, callback)

    assert chunks == ['final stream content']
    assert mock_action.run.call_count == 1
    assert mock_client.chat.completions.create.call_count == 2
