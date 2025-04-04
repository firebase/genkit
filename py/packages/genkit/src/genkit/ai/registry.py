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

"""Genkit maintains a registry of all actions.

An **action** is a remote callable function that uses typed-JSON RPC over HTTP
to allow the framework and users to define custom AI functionality.  There are
several kinds of action defined by [ActionKind][genkit.core.action.ActionKind]:

| Kind          | Description |
|---------------|-------------|
| `'chat-llm'`  | Chat LLM    |
| `'custom'`    | Custom      |
| `'embedder'`  | Embedder    |
| `'evaluator'` | Evaluator   |
| `'flow'`      | Flow        |
| `'indexer'`   | Indexer     |
| `'model'`     | Model       |
| `'prompt'`    | Prompt      |
| `'retriever'` | Retriever   |
| `'text-llm'`  | Text LLM    |
| `'tool'`      | Tool        |
| `'util'`      | Utility     |
"""

import asyncio
import inspect
import traceback
import uuid
from collections.abc import AsyncIterator, Callable
from functools import wraps
from typing import Any

import structlog
from pydantic import BaseModel

from genkit.blocks.embedding import EmbedderFn
from genkit.blocks.evaluator import BatchEvaluatorFn, EvaluatorFn
from genkit.blocks.formats.types import FormatDef
from genkit.blocks.model import ModelFn, ModelMiddleware
from genkit.blocks.prompt import define_prompt
from genkit.blocks.retriever import RetrieverFn
from genkit.blocks.tools import ToolRunContext
from genkit.codec import dump_dict
from genkit.core.action import Action
from genkit.core.action.types import ActionKind
from genkit.core.registry import Registry
from genkit.core.schema import to_json_schema
from genkit.core.tracing import run_in_new_span
from genkit.core.typing import (
    EvalFnResponse,
    EvalRequest,
    EvalResponse,
    GenerationCommonConfig,
    Message,
    ModelInfo,
    Part,
    Score,
    SpanMetadata,
    ToolChoice,
)

EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'evaluatorDisplayName'
EVALUATOR_METADATA_KEY_DEFINITION = 'evaluatorDefinition'
EVALUATOR_METADATA_KEY_IS_BILLED = 'evaluatorIsBilled'

logger = structlog.get_logger(__name__)


def get_func_description(func: Callable, description: str | None = None) -> str:
    """Get the description of a function.

    Args:
        func: The function to get the description of.
        description: The description to use if the function docstring is
            empty.
    """
    if description is not None:
        return description
    if func.__doc__ is not None:
        return func.__doc__
    return ''


class GenkitRegistry:
    """User-facing API for interacting with Genkit registry."""

    def __init__(self):
        """Initialize the Genkit registry."""
        self.registry: Registry = Registry()

    def flow(self, name: str | None = None, description: str | None = None) -> Callable[[Callable], Callable]:
        """Decorator to register a function as a flow.

        Args:
            name: Optional name for the flow. If not provided, uses the
                function name.
            description: Optional description for the flow. If not provided,
                uses the function docstring.

        Returns:
            A decorator function that registers the flow.
        """

        def wrapper(func: Callable) -> Callable:
            """Register the decorated function as a flow.

            Args:
                func: The function to register as a flow.

            Returns:
                The wrapped function that executes the flow.
            """
            flow_name = name if name is not None else func.__name__
            flow_description = get_func_description(func, description)
            action = self.registry.register_action(
                name=flow_name,
                kind=ActionKind.FLOW,
                fn=func,
                description=flow_description,
                span_metadata={'genkit:metadata:flow:name': flow_name},
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Asynchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """Synchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                return action.run(*args, **kwargs).response

            return FlowWrapper(
                fn=async_wrapper if action.is_async else sync_wrapper,
                action=action,
            )

        return wrapper

    def tool(self, name: str | None = None, description: str | None = None) -> Callable[[Callable], Callable]:
        """Decorator to register a function as a tool.

        Args:
            name: Optional name for the flow. If not provided, uses the function
                name.
            description: Description for the tool to be passed to the model;
                if not provided, uses the function docstring.

        Returns:
            A decorator function that registers the tool.
        """

        def wrapper(func: Callable) -> Callable:
            """Register the decorated function as a tool.

            Args:
                func: The function to register as a tool.

            Returns:
                The wrapped function that executes the tool.
            """
            tool_name = name if name is not None else func.__name__
            tool_description = get_func_description(func, description)

            input_spec = inspect.getfullargspec(func)

            def tool_fn_wrapper(*args):
                match len(input_spec.args):
                    case 0:
                        return func()
                    case 1:
                        return func(args[0])
                    case 2:
                        return func(args[0], ToolRunContext(args[1]))
                    case _:
                        raise ValueError('tool must have 0-2 args...')

            action = self.registry.register_action(
                name=tool_name,
                kind=ActionKind.TOOL,
                description=tool_description,
                fn=tool_fn_wrapper,
                metadata_fn=func,
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Asynchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """Synchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return action.run(*args, **kwargs).response

            return async_wrapper if action.is_async else sync_wrapper

        return wrapper

    def define_retriever(
        self,
        name: str,
        fn: RetrieverFn,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> Callable[[Callable], Callable]:
        """Define a retriever action.

        Args:
            name: Name of the retriever.
            fn: Function implementing the retriever behavior.
            config_schema: Optional schema for retriever configuration.
            metadata: Optional metadata for the retriever.
            description: Optional description for the retriever.
        """
        retriever_meta = metadata if metadata else {}
        if 'retriever' not in retriever_meta:
            retriever_meta['retriever'] = {}
        if 'label' not in retriever_meta['retriever'] or not retriever_meta['retriever']['label']:
            retriever_meta['retriever']['label'] = name
        if config_schema:
            retriever_meta['retriever']['customOptions'] = to_json_schema(config_schema)

        retriever_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=ActionKind.RETRIEVER,
            fn=fn,
            metadata=retriever_meta,
            description=retriever_description,
        )

    def define_evaluator(
        self,
        name: str,
        display_name: str,
        definition: str,
        fn: EvaluatorFn,
        is_billed: bool = False,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> Callable[[Callable], Callable]:
        """Define a evaluator action.

        This action runs the callback function on the every sample of
        the input dataset.

        Args:
            name: Name of the evaluator.
            fn: Function implementing the evaluator behavior.
            display_name: User-visible display name
            definition: User-visible evaluator definition
            is_billed: Whether the evaluator performs any billed actions
                        (paid  APIs, LLMs etc.)
            config_schema: Optional schema for evaluator configuration.
            metadata: Optional metadata for the evaluator.
            description: Optional description for the evaluator.
        """
        evaluator_meta = metadata if metadata else {}
        if 'evaluator' not in evaluator_meta:
            evaluator_meta['evaluator'] = {}
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DEFINITION] = definition
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DISPLAY_NAME] = display_name
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_IS_BILLED] = is_billed
        if 'label' not in evaluator_meta['evaluator'] or not evaluator_meta['evaluator']['label']:
            evaluator_meta['evaluator']['label'] = name
        if config_schema:
            evaluator_meta['evaluator']['customOptions'] = to_json_schema(config_schema)

        evaluator_description = get_func_description(fn, description)

        def eval_stepper_fn(req: EvalRequest) -> EvalResponse:
            eval_responses: list[EvalFnResponse] = []
            for index in range(len(req.dataset)):
                datapoint = req.dataset[index]
                if datapoint.test_case_id is None:
                    datapoint.test_case_id = uuid.uuid4()
                span_metadata = SpanMetadata(
                    name=f'Test Case {datapoint.test_case_id}',
                    metadata={'evaluator:evalRunId': req.eval_run_id},
                )
                try:
                    with run_in_new_span(span_metadata, labels={'genkit:type': 'evaluator'}) as span:
                        span_id = span.span_id()
                        trace_id = span.trace_id()
                        try:
                            span.set_input(datapoint)
                            test_case_output = fn(datapoint, req.options)
                            test_case_output.span_id = span_id
                            test_case_output.trace_id = trace_id
                            span.set_output(test_case_output)
                            eval_responses.append(test_case_output)
                        except Exception as e:
                            logger.debug(f'eval_stepper_fn error: {str(e)}')
                            logger.debug(traceback.format_exc())
                            evaluation = Score(
                                error=f'Evaluation of test case {datapoint.test_case_id} failed: \n{str(e)}'
                            )
                            eval_responses.append(
                                EvalFnResponse(
                                    span_id=span_id,
                                    trace_id=trace_id,
                                    test_case_id=datapoint.test_case_id,
                                    evaluation=evaluation,
                                )
                            )
                            # Raise to mark span as failed
                            raise e
                except Exception:
                    # Continue to process other points
                    continue
            return EvalResponse(eval_responses)

        return self.registry.register_action(
            name=name,
            kind=ActionKind.EVALUATOR,
            fn=eval_stepper_fn,
            metadata=evaluator_meta,
            description=evaluator_description,
        )

    def define_batch_evaluator(
        self,
        name: str,
        display_name: str,
        definition: str,
        fn: BatchEvaluatorFn,
        is_billed: bool = False,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> Callable[[Callable], Callable]:
        """Define a batch evaluator action.

        This action runs the callback function on the entire dataset.

        Args:
            name: Name of the evaluator.
            fn: Function implementing the evaluator behavior.
            display_name: User-visible display name
            definition: User-visible evaluator definition
            is_billed: Whether the evaluator performs any billed actions
                        (paid  APIs, LLMs etc.)
            config_schema: Optional schema for evaluator configuration.
            metadata: Optional metadata for the evaluator.
            description: Optional description for the evaluator.
        """
        evaluator_meta = metadata if metadata else {}
        if 'evaluator' not in evaluator_meta:
            evaluator_meta['evaluator'] = {}
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DEFINITION] = definition
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DISPLAY_NAME] = display_name
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_IS_BILLED] = is_billed
        if 'label' not in evaluator_meta['evaluator'] or not evaluator_meta['evaluator']['label']:
            evaluator_meta['evaluator']['label'] = name
        if config_schema:
            evaluator_meta['evaluator']['customOptions'] = to_json_schema(config_schema)

        evaluator_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=ActionKind.EVALUATOR,
            fn=fn,
            metadata=evaluator_meta,
            description=evaluator_description,
        )

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        info: ModelInfo | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a custom model action.

        Args:
            name: Name of the model.
            fn: Function implementing the model behavior.
            config_schema: Optional schema for model configuration.
            metadata: Optional metadata for the model.
            info: Optional ModelInfo for the model.
            description: Optional description for the model.
        """
        model_meta: dict[str, Any] = metadata if metadata else {}
        if info:
            model_meta['model'] = dump_dict(info)
        if 'model' not in model_meta:
            model_meta['model'] = {}
        if 'label' not in model_meta['model'] or not model_meta['model']['label']:
            model_meta['model']['label'] = name

        if config_schema:
            model_meta['model']['customOptions'] = to_json_schema(config_schema)

        model_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=ActionKind.MODEL,
            fn=fn,
            metadata=model_meta,
            description=model_description,
        )

    def define_embedder(
        self,
        name: str,
        fn: EmbedderFn,
        metadata: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a custom embedder action.

        Args:
            name: Name of the model.
            fn: Function implementing the embedder behavior.
            metadata: Optional metadata for the model.
            description: Optional description for the embedder.
        """
        embedder_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=ActionKind.EMBEDDER,
            fn=fn,
            metadata=metadata,
            description=embedder_description,
        )

    def define_format(self, format: FormatDef) -> None:
        """Registers a custom format in the registry.

        Args:
            format: The format to register.
        """
        self.registry.register_value('format', format.name, format)

    def define_prompt(
        self,
        variant: str | None = None,
        model: str | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        description: str | None = None,
        input_schema: type | dict[str, Any] | None = None,
        system: str | Part | list[Part] | None = None,
        prompt: str | Part | list[Part] | None = None,
        messages: str | list[Message] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, Any] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        # TODO:
        #  docs: list[Document]
    ):
        """Define a prompt.

        Args:
            variant: Optional variant name for the prompt.
            model: Optional model name to use for the prompt.
            config: Optional configuration for the model.
            description: Optional description for the prompt.
            input_schema: Optional schema for the input to the prompt.
            system: Optional system message for the prompt.
            prompt: Optional prompt for the model.
            messages: Optional messages for the model.
            output_format: Optional output format for the prompt.
            output_content_type: Optional output content type for the prompt.
            output_instructions: Optional output instructions for the prompt.
            output_schema: Optional schema for the output from the prompt.
            output_constrained: Optional flag indicating whether the output
                should be constrained.
            max_turns: Optional maximum number of turns for the prompt.
            return_tool_requests: Optional flag indicating whether tool requests
                should be returned.
            metadata: Optional metadata for the prompt.
            tools: Optional list of tools to use for the prompt.
            tool_choice: Optional tool choice for the prompt.
            use: Optional list of model middlewares to use for the prompt.
        """
        return define_prompt(
            self.registry,
            variant=variant,
            model=model,
            config=config,
            description=description,
            input_schema=input_schema,
            system=system,
            prompt=prompt,
            messages=messages,
            output_format=output_format,
            output_content_type=output_content_type,
            output_instructions=output_instructions,
            output_schema=output_schema,
            output_constrained=output_constrained,
            max_turns=max_turns,
            return_tool_requests=return_tool_requests,
            metadata=metadata,
            tools=tools,
            tool_choice=tool_choice,
            use=use,
        )


class FlowWrapper:
    """A wapper for flow functions to add `stream` method."""

    def __init__(self, fn: Callable, action: Action):
        """Initialize the FlowWrapper.

        Args:
            fn: The function to wrap.
            action: The action to wrap.
        """
        self._fn = fn
        self._action = action

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        """Call the wrapped function.

        Args:
            *args: Positional arguments to pass to the function.
            **kwds: Keyword arguments to pass to the function.

        Returns:
            The result of the function call.
        """
        return self._fn(*args, **kwds)

    def stream(
        self,
        input: Any = None,
        context: dict[str, Any] | None = None,
        telemetry_labels: dict[str, Any] | None = None,
    ) -> tuple[
        AsyncIterator,
        asyncio.Future,
    ]:
        """Run the flow and return an async iterator of the results.

        Args:
            input: The input to the action.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.

        Returns:
            A tuple containing:
            - An AsyncIterator of the chunks from the action.
            - An asyncio.Future that resolves to the final result of the action.
        """
        return self._action.stream(input=input, context=context, telemetry_labels=telemetry_labels)
