#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Testing utilities for Genkit applications.

This module provides mock models, test utilities, and a model test suite for
testing Genkit applications without making actual API calls to AI providers.

Key Components
==============

┌───────────────────────────────────────────────────────────────────────────┐
│                         Testing Components                                 │
├───────────────────────┬───────────────────────────────────────────────────┤
│ Component             │ Purpose                                           │
├───────────────────────┼───────────────────────────────────────────────────┤
│ EchoModel             │ Echoes input back - verify request formatting     │
│ ProgrammableModel     │ Returns configurable responses - test scenarios   │
│ StaticResponseModel   │ Always returns same response - simple tests       │
│ test_models()         │ Run standard test suite against models            │
└───────────────────────┴───────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.ai import Genkit
    from genkit.testing import (
        define_echo_model,
        define_programmable_model,
        test_models,
    )

    ai = Genkit()

    # Echo model - useful for verifying request formatting
    echo, echo_action = define_echo_model(ai)
    response = await ai.generate(model='echoModel', prompt='Hello')
    # response contains: "[ECHO] user: "Hello""

    # Programmable model - useful for testing specific scenarios
    pm, pm_action = define_programmable_model(ai)
    pm.responses = [GenerateResponse(message=Message(...))]
    response = await ai.generate(model='programmableModel', prompt='test')
    assert pm.last_request is not None

    # Test suite - validate model implementations
    report = await test_models(ai, ['googleai/gemini-2.0-flash'])
    for test in report:
        print(f'{test["description"]}: {test["models"]}')
    ```

Cross-Language Parity:
    - JavaScript: js/ai/src/testing/model-tester.ts
    - Go: go/ai/testutil_test.go

See Also:
    - https://genkit.dev for Genkit documentation
"""

from copy import deepcopy
from typing import Any, TypedDict

from pydantic import BaseModel, Field

from genkit.ai import Genkit, Output
from genkit.codec import dump_json
from genkit.core.action import Action, ActionRunContext
from genkit.core.action.types import ActionKind
from genkit.core.tracing import run_in_new_span
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Media,
    MediaPart,
    Message,
    ModelInfo,
    Part,
    Role,
    SpanMetadata,
    TextPart,
)


class ProgrammableModel:
    """A configurable model implementation for testing.

    This class allows test cases to define custom responses that the model
    should return, making it useful for testing expected behavior in various
    scenarios.

    Attributes:
        request_count: Total number of requests received.
        responses: List of predefined responses to return.
        chunks: Optional list of chunks to stream for each request.
        last_request: The most recent request received (deep copy).

    Example:
        ```python
        ai = Genkit()
        pm, action = define_programmable_model(ai)

        # Set up responses
        pm.responses = [
            GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='Response 1'))])),
            GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='Response 2'))])),
        ]

        # First call returns "Response 1"
        result1 = await ai.generate(model='programmableModel', prompt='test')

        # Second call returns "Response 2"
        result2 = await ai.generate(model='programmableModel', prompt='test')

        # Inspect last request
        assert pm.last_request.messages[0].content[0].root.text == 'test'
        ```
    """

    def __init__(self) -> None:
        """Initialize a new ProgrammableModel instance."""
        self._request_idx: int = 0
        self.request_count: int = 0
        self.responses: list[GenerateResponse] = []
        self.chunks: list[list[GenerateResponseChunk]] | None = None
        self.last_request: GenerateRequest | None = None

    def reset(self) -> None:
        """Reset the model state for reuse in tests."""
        self._request_idx = 0
        self.request_count = 0
        self.responses = []
        self.chunks = None
        self.last_request = None

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Process a generation request and return a programmed response.

        This function returns pre-configured responses and streams
        pre-configured chunks based on the current request index.

        Args:
            request: The generation request to process.
            ctx: The action run context for streaming chunks.

        Returns:
            The pre-configured response for the current request.

        Raises:
            IndexError: If more requests are made than responses configured.
        """
        # Store deep copy of request for inspection (matches JS behavior)
        self.last_request = deepcopy(request)
        self.request_count += 1

        response = self.responses[self._request_idx]
        if self.chunks and self._request_idx < len(self.chunks):
            for chunk in self.chunks[self._request_idx]:
                ctx.send_chunk(chunk)
        self._request_idx += 1
        return response


def define_programmable_model(
    ai: Genkit,
    name: str = 'programmableModel',
) -> tuple[ProgrammableModel, Action]:
    """Define a configurable programmable model for testing.

    Creates a model that returns pre-configured responses, useful for
    testing specific scenarios like multi-turn conversations, tool calls,
    or error conditions.

    Args:
        ai: The Genkit instance to register the model with.
        name: The name for the model. Defaults to 'programmableModel'.

    Returns:
        A tuple of (ProgrammableModel instance, registered Action).

    Example:
        ```python
        ai = Genkit()
        pm, action = define_programmable_model(ai)

        # Configure response with tool call
        pm.responses = [
            GenerateResponse(
                message=Message(
                    role=Role.MODEL,
                    content=[
                        Part(
                            root=ToolRequestPart(
                                tool_request=ToolRequest(
                                    name='myTool',
                                    input={'arg': 'value'},
                                ),
                            )
                        )
                    ],
                )
            )
        ]
        ```
    """
    pm = ProgrammableModel()

    def model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        return pm.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (pm, action)


class EchoModel:
    """A model implementation that echoes back the input with metadata.

    This model is useful for testing as it returns a readable representation
    of the input it received, including config, tools, and output schema.

    The echo format is:
        [ECHO] role: "content", role: "content" config tool_choice output

    Attributes:
        last_request: The most recent request received.
        stream_countdown: If True, streams "3", "2", "1" chunks before response.

    Example:
        ```python
        ai = Genkit()
        echo, action = define_echo_model(ai, stream_countdown=True)

        response = await ai.generate(model='echoModel', prompt='Hello world', config={'temperature': 0.5})
        # Response text: '[ECHO] user: "Hello world" {"temperature":0.5}'
        # With streaming: sends chunks "3", "2", "1" before final response
        ```
    """

    def __init__(self, stream_countdown: bool = False) -> None:
        """Initialize a new EchoModel instance.

        Args:
            stream_countdown: If True, stream "3", "2", "1" chunks before response.
        """
        self.last_request: GenerateRequest | None = None
        self.stream_countdown: bool = stream_countdown

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Process a generation request and echo it back in the response.

        Args:
            request: The generation request to process.
            ctx: The action run context for streaming.

        Returns:
            A response containing an echo of the input request details.
        """
        self.last_request = request

        # Build echo string from messages
        merged_txt = ''
        for m in request.messages:
            merged_txt += f' {m.role}: ' + ','.join(
                dump_json(p.root.text) if p.root.text is not None else '""' for p in m.content
            )
        echo_resp = f'[ECHO]{merged_txt}'

        # Add config, tools, and output info
        if request.config:
            echo_resp += f' {dump_json(request.config)}'
        if request.tools:
            echo_resp += f' tools={",".join(t.name for t in request.tools)}'
        if request.tool_choice is not None:
            echo_resp += f' tool_choice={request.tool_choice}'
        if request.output and dump_json(request.output) != '{}':
            echo_resp += f' output={dump_json(request.output)}'

        # Stream countdown chunks if enabled (matches JS behavior)
        if self.stream_countdown:
            for i, countdown in enumerate(['3', '2', '1']):
                ctx.send_chunk(
                    chunk=GenerateResponseChunk(role=Role.MODEL, index=i, content=[Part(root=TextPart(text=countdown))])
                )

        # NOTE: Part is a RootModel requiring root=TextPart(...) syntax.
        return GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text=echo_resp))]))


def define_echo_model(
    ai: Genkit,
    name: str = 'echoModel',
    stream_countdown: bool = False,
) -> tuple[EchoModel, Action]:
    """Define an echo model that returns input back as output.

    Creates a model that echoes the request back in a readable format,
    useful for testing request formatting and middleware behavior.

    Args:
        ai: The Genkit instance to register the model with.
        name: The name for the model. Defaults to 'echoModel'.
        stream_countdown: If True, stream "3", "2", "1" before final response.

    Returns:
        A tuple of (EchoModel instance, registered Action).

    Example:
        ```python
        ai = Genkit()
        echo, action = define_echo_model(ai, stream_countdown=True)

        # Test that middleware properly formats requests
        response = await ai.generate(model='echoModel', prompt='test')
        assert '[ECHO]' in response.text
        ```
    """
    echo = EchoModel(stream_countdown=stream_countdown)

    def model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        return echo.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (echo, action)


class StaticResponseModel:
    """A model that always returns the same static response.

    Useful for simple test cases where a fixed response is needed.

    Attributes:
        response_message: The message to always return.
        last_request: The most recent request received.
        request_count: Total number of requests received.
    """

    def __init__(self, message: dict[str, Any]) -> None:
        """Initialize with a static message to return.

        Args:
            message: The message data to always return.
        """
        self.response_message: Message = Message.model_validate(message)
        self.last_request: GenerateRequest | None = None
        self.request_count: int = 0

    def model_fn(self, request: GenerateRequest, _ctx: ActionRunContext) -> GenerateResponse:
        """Return the static response.

        Args:
            request: The generation request (stored but not used).
            _ctx: The action run context (unused).

        Returns:
            GenerateResponse with the static message.
        """
        self.last_request = request
        self.request_count += 1
        return GenerateResponse(message=self.response_message)


def define_static_response_model(
    ai: Genkit,
    message: dict[str, Any],
    name: str = 'staticModel',
) -> tuple[StaticResponseModel, Action]:
    """Define a model that always returns the same response.

    Args:
        ai: The Genkit instance to register the model with.
        message: The message data to always return.
        name: The name for the model. Defaults to 'staticModel'.

    Returns:
        A tuple of (StaticResponseModel instance, registered Action).

    Example:
        ```python
        ai = Genkit()
        static, action = define_static_response_model(
            ai,
            message={'role': 'model', 'content': [{'text': 'Hello!'}]},
        )

        # Always returns "Hello!"
        response = await ai.generate(model='staticModel', prompt='anything')
        assert response.text == 'Hello!'
        ```
    """
    static = StaticResponseModel(message)

    def model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        return static.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (static, action)


class SkipTestError(Exception):
    """Exception raised to skip a test case.

    This is used internally by the test suite to indicate that a test
    should be skipped (e.g., because the model doesn't support the
    feature being tested).
    """


def skip() -> None:
    """Skip the current test case.

    Raises:
        SkipTestError: Always raised to skip the test.
    """
    raise SkipTestError()


class ModelTestError(TypedDict, total=False):
    """Error information from a failed test."""

    message: str
    stack: str | None


class ModelTestResult(TypedDict, total=False):
    """Result of testing a single model on a single test case."""

    name: str
    passed: bool
    skipped: bool
    error: ModelTestError


class TestCaseReport(TypedDict):
    """Report for a single test case across all models."""

    description: str
    models: list[ModelTestResult]


TestReport = list[TestCaseReport]
"""Complete test report for all test cases and models."""


class GablorkenInput(BaseModel):
    """Input for the gablorken tool used in tool calling tests."""

    value: float = Field(..., description='The value to calculate gablorken for')


async def test_models(ai: Genkit, models: list[str]) -> TestReport:
    r"""Run a standard test suite against one or more models.

    This function runs a series of tests to validate model implementations,
    checking for basic functionality, multimodal support, conversation history,
    system prompts, structured output, and tool calling.

    Test Suite Overview
    ===================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          Model Test Suite                                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                          │
    │  Test Case              │ Description                    │ Auto-Skip    │
    │  ───────────────────────┼────────────────────────────────┼─────────────│
    │  basic hi               │ Simple text generation         │ Never        │
    │  multimodal             │ Image input processing         │ No media     │
    │  history                │ Multi-turn conversation        │ No multiturn │
    │  system prompt          │ System message handling        │ Never        │
    │  structured output      │ JSON schema output             │ Never        │
    │  tool calling           │ Function calling               │ No tools     │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘

    Args:
        ai: The Genkit instance with models to test.
        models: List of model names to test (e.g., ['googleai/gemini-2.0-flash']).

    Returns:
        A TestReport containing results for each test case and model.

    Example:
        ```python
        from genkit.ai import Genkit
        from genkit.plugins.google_genai import GoogleAI
        from genkit.testing import test_models

        ai = Genkit(plugins=[GoogleAI()])

        # Test multiple models
        report = await test_models(
            ai,
            [
                'googleai/gemini-2.0-flash',
                'googleai/gemini-1.5-pro',
            ],
        )

        # Print results
        for test in report:
            print(f'\\n{test["description"]}:')
            for model in test['models']:
                status = '✓' if model['passed'] else ('⊘' if model.get('skipped') else '✗')
                print(f'  {status} {model["name"]}')
                if 'error' in model:
                    print(f'      Error: {model["error"]["message"]}')
        ```

    Note:
        - Tests are automatically skipped if the model doesn't support
          the required capability (e.g., tools, media, multiturn).
        - A 'gablorkenTool' is automatically registered for tool calling tests.
        - The test uses a small base64-encoded test image for multimodal tests.

    See Also:
        - JS implementation: js/ai/src/testing/model-tester.ts
    """

    # Register the gablorken tool for tool calling tests
    # NOTE: Tool name is camelCase to match JS implementation for parity
    @ai.tool(name='gablorkenTool')
    def gablorken_tool(input: GablorkenInput) -> float:
        """Calculate the gablorken of a value. Use when need to calculate a gablorken."""
        return (input.value**3) + 1.407

    async def get_model_info(model_name: str) -> ModelInfo | None:
        """Get ModelInfo for a model, or None if not available.

        Args:
            model_name: The name of the model to look up.

        Returns:
            ModelInfo if available, None otherwise.
        """
        model_action = await ai.registry.resolve_action(ActionKind.MODEL, model_name)
        if model_action and model_action.metadata:
            info_obj = model_action.metadata.get('model')
            if isinstance(info_obj, ModelInfo):
                return info_obj
        return None

    # Define test cases
    async def test_basic_hi(model: str) -> None:
        """Test basic text generation."""
        response = await ai.generate(model=model, prompt='just say "Hi", literally')
        got = response.text.strip()
        assert 'hi' in got.lower(), f'Expected "Hi" in response, got: {got}'

    async def test_multimodal(model: str) -> None:
        """Test multimodal (image) input."""
        info = await get_model_info(model)
        if not (info and info.supports and info.supports.media):
            skip()

        # Small test image (plus sign)
        test_image = (
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2'
            'AAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV9TpSoVETOIOGSoulgQFXHU'
            'KhShQqgVWnUwufRDaNKQtLg4Cq4FBz8Wqw4uzro6uAqC4AeIs4OToouU+L+k0CLG'
            'g+N+vLv3uHsHCLUi0+22MUA3ylYyHpPSmRUp9IpOhCCiFyMKs81ZWU7Ad3zdI8DX'
            'uyjP8j/35+jWsjYDAhLxDDOtMvE68dRm2eS8TyyygqIRnxOPWnRB4keuqx6/cc67'
            'LPBM0Uol54hFYinfwmoLs4KlE08SRzTdoHwh7bHGeYuzXqywxj35C8NZY3mJ6zQH'
            'EccCFiFDgooKNlBEGVFaDVJsJGk/5uMfcP0yuVRybYCRYx4l6FBcP/gf/O7Wzk2M'
            'e0nhGND+4jgfQ0BoF6hXHef72HHqJ0DwGbgymv5SDZj+JL3a1CJHQM82cHHd1NQ9'
            '4HIH6H8yFUtxpSBNIZcD3s/omzJA3y3Qter11tjH6QOQoq4SN8DBITCcp+w1n3d3'
            'tPb275lGfz9aC3Kd0jYiSQAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+gJ'
            'BxQRO1/5qB8AAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAAA'
            'sUlEQVQoz61SMQqEMBDcO5SYToUE/IBPyRMCftAH+INUviApUwYjNkKCVcTiQK7I'
            'HSw45czODrMswCOQUkopEQZjzDiOWemdZfu+b5oGYYgx1nWNMPwB2vACAK01Y4wQ'
            '8qGqqirL8jzPlNI9t64r55wQUgBA27be+xDCfaJhGJxzSqnv3UKIn7ne+2VZEB2s'
            'tZRSRLN93+d5RiRs28Y5RySEEI7jyEpFlp2mqeu6Zx75ApQwPdsIcq0ZAAAAAElF'
            'TkSuQmCC'
        )

        response = await ai.generate(
            model=model,
            prompt=[
                Part(root=MediaPart(media=Media(url=test_image))),
                Part(root=TextPart(text='what math operation is this? plus, minus, multiply or divide?')),
            ],
        )
        got = response.text.strip().lower()
        assert 'plus' in got, f'Expected "plus" in response, got: {got}'

    async def test_history(model: str) -> None:
        """Test conversation history (multi-turn)."""
        info = await get_model_info(model)
        if not (info and info.supports and info.supports.multiturn):
            skip()

        response1 = await ai.generate(model=model, prompt='My name is Glorb')
        response2 = await ai.generate(
            model=model,
            prompt="What's my name?",
            messages=response1.messages,
        )
        got = response2.text.strip()
        assert 'Glorb' in got, f'Expected "Glorb" in response, got: {got}'

    async def test_system_prompt(model: str) -> None:
        """Test system prompt handling."""
        response = await ai.generate(
            model=model,
            prompt='Hi',
            messages=[
                Message.model_validate({
                    'role': 'system',
                    'content': [{'text': 'If the user says "Hi", just say "Bye"'}],
                }),
            ],
        )
        got = response.text.strip()
        assert 'Bye' in got, f'Expected "Bye" in response, got: {got}'

    async def test_structured_output(model: str) -> None:
        """Test structured JSON output."""

        class PersonInfo(BaseModel):
            name: str
            occupation: str

        response = await ai.generate(
            model=model,
            prompt='extract data as json from: Jack was a Lumberjack',
            output=Output(schema=PersonInfo),
        )
        got = response.output
        assert got is not None, 'Expected structured output'
        # Output can be dict or model instance depending on parsing
        if isinstance(got, BaseModel):
            got = got.model_dump()

        assert isinstance(got, dict), f'Expected output to be a dict or BaseModel, got {type(got)}'
        assert got.get('name') == 'Jack', f"Expected name='Jack', got: {got.get('name')}"
        assert got.get('occupation') == 'Lumberjack', f"Expected occupation='Lumberjack', got: {got.get('occupation')}"

    async def test_tool_calling(model: str) -> None:
        """Test tool/function calling."""
        info = await get_model_info(model)
        if not (info and info.supports and info.supports.tools):
            skip()

        response = await ai.generate(
            model=model,
            prompt='what is a gablorken of 2? use provided tool',
            tools=['gablorkenTool'],
        )
        got = response.text.strip()
        # 2^3 + 1.407 = 9.407
        assert '9.407' in got, f'Expected "9.407" in response, got: {got}'

    # Map of test cases
    tests: dict[str, Any] = {
        'basic hi': test_basic_hi,
        'multimodal': test_multimodal,
        'history': test_history,
        'system prompt': test_system_prompt,
        'structured output': test_structured_output,
        'tool calling': test_tool_calling,
    }

    # Run tests with tracing
    report: TestReport = []

    with run_in_new_span(SpanMetadata(name='testModels'), labels={'genkit:type': 'testSuite'}):
        for test_name, test_fn in tests.items():
            with run_in_new_span(SpanMetadata(name=test_name), labels={'genkit:type': 'testCase'}):
                case_report: TestCaseReport = {
                    'description': test_name,
                    'models': [],
                }

                for model in models:
                    model_result: ModelTestResult = {
                        'name': model,
                        'passed': True,  # Optimistic
                    }

                    try:
                        await test_fn(model)
                    except SkipTestError:
                        model_result['passed'] = False
                        model_result['skipped'] = True
                    except AssertionError as e:
                        model_result['passed'] = False
                        model_result['error'] = {
                            'message': str(e),
                            'stack': None,
                        }
                    except Exception as e:
                        model_result['passed'] = False
                        model_result['error'] = {
                            'message': str(e),
                            'stack': None,
                        }

                    case_report['models'].append(model_result)

                report.append(case_report)

    return report


# Export all public symbols
__all__ = [
    'EchoModel',
    'GablorkenInput',
    'ModelTestError',
    'ModelTestResult',
    'ProgrammableModel',
    'SkipTestError',
    'StaticResponseModel',
    'TestCaseReport',
    'TestReport',
    'define_echo_model',
    'define_programmable_model',
    'define_static_response_model',
    'skip',
    'test_models',
]
