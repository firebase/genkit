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

"""Evaluator type definitions for the Genkit framework."""

import inspect
import traceback
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, ClassVar, cast, get_origin

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing_extensions import Never

from genkit._core._action import (
    Action,
    ActionKind,
    ActionRunContext,
    known_annotation_names,
    resolve_type_hints,
    signature_of,
    with_request_annotation,
)
from genkit._core._logger import get_logger
from genkit._core._model import BatchEvaluatorRequest, EvaluatorRequest, declared_config_type
from genkit._core._registry import Registry
from genkit._core._schema import to_json_schema
from genkit._core._telemetry._attrs import metadata_key
from genkit._core._telemetry._instrumentation import SpanContext, run_in_new_span
from genkit._core._typing import (
    BaseDataPoint,
    EvalResponse,
    EvaluatorResponse,
    Score,
    ScoreStatus,
)

logger = get_logger(__name__)

EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'evaluatorDisplayName'
EVALUATOR_METADATA_KEY_DEFINITION = 'evaluatorDefinition'
EVALUATOR_METADATA_KEY_IS_BILLED = 'evaluatorIsBilled'

# Per-row evaluator: one EvaluatorRequest (row + options) per dataset row. Must be async.
EvaluatorFn = Callable[[EvaluatorRequest[Any]], Coroutine[Any, Any, EvaluatorResponse]]

# Batch evaluator: one BatchEvaluatorRequest (dataset + options). Returns list[EvaluatorResponse].
BatchEvaluatorFn = Callable[[BatchEvaluatorRequest[Any]], Coroutine[Any, Any, list[EvaluatorResponse]]]


class EvaluatorRef(BaseModel):
    """Reference to an evaluator."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', populate_by_name=True, alias_generator=to_camel)

    name: str
    config: dict[str, object] | None = None


def _is_subclass(annotation: object, cls: type) -> bool:
    """``issubclass`` that is False for non-classes. ``EvaluatorRequest[Cfg]`` counts as ``EvaluatorRequest``."""
    return isinstance(annotation, type) and get_origin(annotation) is None and issubclass(annotation, cls)


def _row_request_class(fn: Callable[..., Any], name: str) -> type[EvaluatorRequest[Any]]:
    """The request class a per-row fn takes: ``EvaluatorRequest`` or ``EvaluatorRequest[Cfg]``.

    The fn takes exactly one parameter. The pre-1.0 ``(row, options)`` form
    raises a TypeError that shows the new one.
    """
    params = [
        p
        for p in signature_of(fn).parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    hints = resolve_type_hints(fn, known_annotation_names(ActionKind.EVALUATOR))
    annotation = hints.get(params[0].name) if params else None
    fn_name = getattr(fn, '__name__', name)
    if len(params) != 1 or annotation is BaseDataPoint:
        got = ', '.join(p.name for p in params)
        raise TypeError(
            f"evaluator '{name}' takes one EvaluatorRequest, but '{fn_name}' takes ({got}). "
            f'Write `async def {fn_name}(req: EvaluatorRequest[YourConfig]) -> EvaluatorResponse` '
            '(or bare EvaluatorRequest for a dict) and read req.row and req.options.'
        )
    if _is_subclass(annotation, BatchEvaluatorRequest):
        raise TypeError(
            f"evaluator '{name}': BatchEvaluatorRequest is the whole dataset; register '{fn_name}' with "
            'define_batch_evaluator, or take EvaluatorRequest to score one row.'
        )
    if _is_subclass(annotation, EvaluatorRequest):
        return cast(type[EvaluatorRequest[Any]], annotation)
    return EvaluatorRequest


def _check_batch_annotation(fn: Callable[..., Any], name: str) -> None:
    """A batch fn typed with the per-row ``EvaluatorRequest`` raises instead of failing every run."""
    hints = resolve_type_hints(fn, known_annotation_names(ActionKind.EVALUATOR))
    if any(_is_subclass(a, EvaluatorRequest) for a in hints.values()):
        fn_name = getattr(fn, '__name__', name)
        raise TypeError(
            f"batch evaluator '{name}': EvaluatorRequest is one row; '{fn_name}' should take "
            'BatchEvaluatorRequest (req.dataset, req.options), or register it with define_evaluator.'
        )


def _set_custom_options(evaluator_meta: dict[str, object], action: Action[Any, Any, Any]) -> None:
    """Annotation only: the Dev UI form comes from the options class."""
    info = evaluator_meta.get('evaluator')
    if isinstance(info, dict) and 'customOptions' not in info and action.config_schema is not None:
        cast(dict[str, object], info)['customOptions'] = to_json_schema(action.config_schema)


def _evaluator_metadata(
    name: str,
    display_name: str,
    definition: str,
    is_billed: bool,
    config_schema: type[BaseModel] | dict[str, object] | None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the action metadata that the Dev UI and `genkit eval:run` read."""
    evaluator_meta: dict[str, object] = dict(metadata) if metadata else {}
    existing = evaluator_meta.get('evaluator')
    info: dict[str, object] = {str(k): v for k, v in existing.items()} if isinstance(existing, dict) else {}
    evaluator_meta['evaluator'] = info
    info[EVALUATOR_METADATA_KEY_DEFINITION] = definition
    info[EVALUATOR_METADATA_KEY_DISPLAY_NAME] = display_name
    info[EVALUATOR_METADATA_KEY_IS_BILLED] = is_billed
    label = info.get('label')
    if not isinstance(label, str) or not label:
        info['label'] = name
    if config_schema:
        info['customOptions'] = to_json_schema(config_schema)
    return evaluator_meta


def _get_func_description(func: Callable[..., Any], description: str | None = None) -> str:
    """Return description if provided, otherwise use the function's docstring."""
    if description is not None:
        return description
    if func.__doc__ is not None:
        return func.__doc__
    return ''


class Evaluator(Action[BatchEvaluatorRequest, EvalResponse, Never]):
    """Evaluator action that runs ``fn`` on each dataset row, without registering it.

    The action takes a ``BatchEvaluatorRequest`` and calls ``fn`` once per row
    with ``EvaluatorRequest(row=row, options=req.options)``. Annotate ``fn``'s
    parameter as ``EvaluatorRequest[Cfg]`` to get ``options`` validated into
    ``Cfg``, with defaults; bare ``EvaluatorRequest`` gives a dict. Given both
    that annotation and ``config_schema``, they must be the same class.

    Plugin ``init`` / ``resolve`` / ``list_actions`` return this.
    ``define_evaluator`` registers it.
    """

    def __init__(
        self,
        name: str,
        fn: EvaluatorFn,
        *,
        display_name: str,
        definition: str,
        is_billed: bool = False,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> None:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError(f"Action handlers must be async functions. Got sync function for '{name}'.")
        row_request = _row_request_class(fn, name)

        evaluator_meta = _evaluator_metadata(name, display_name, definition, is_billed, config_schema, metadata)
        evaluator_description = _get_func_description(fn, description)

        async def eval_stepper_fn(req: BatchEvaluatorRequest) -> EvalResponse:
            eval_responses: list[EvaluatorResponse] = []
            for index in range(len(req.dataset)):
                datapoint = req.dataset[index]
                case_id = datapoint.test_case_id or str(uuid.uuid4())
                datapoint.test_case_id = case_id
                try:

                    async def body(
                        span: SpanContext, point: BaseDataPoint = datapoint, test_case_id: str = case_id
                    ) -> EvaluatorResponse:
                        try:
                            test_case_output = await fn(row_request(row=point, options=req.options))
                            test_case_output.span_id = span.span_id
                            test_case_output.trace_id = span.trace_id
                            return test_case_output
                        except Exception as e:
                            logger.debug(f'eval_stepper_fn error: {e!s}')
                            logger.debug(traceback.format_exc())
                            evaluation = Score(
                                error=f'Evaluation of test case {test_case_id} failed: \n{e!s}',
                                status=ScoreStatus.FAIL,
                            )
                            eval_responses.append(
                                EvaluatorResponse(
                                    span_id=span.span_id,
                                    trace_id=span.trace_id,
                                    test_case_id=test_case_id,
                                    evaluation=[evaluation],
                                )
                            )
                            raise e

                    eval_responses.append(
                        await run_in_new_span(
                            f'Test Case {datapoint.test_case_id}',
                            body,
                            action_type='evaluator',
                            input=datapoint,
                            attributes={metadata_key('evaluator:evalRunId'): str(req.eval_run_id)},
                        )
                    )
                except Exception:  # noqa: S112 - intentionally continue processing other datapoints
                    continue
            return EvalResponse(eval_responses)

        # The stepper is the action, so it carries the per-row fn's options class:
        # EvaluatorRequest[Cfg] on fn makes the action input BatchEvaluatorRequest[Cfg].
        options_cls = declared_config_type(row_request)
        if options_cls is not None:
            eval_stepper_fn.__annotations__['req'] = cast(Any, BatchEvaluatorRequest)[options_cls]

        super().__init__(
            kind=ActionKind.EVALUATOR,
            name=name,
            fn=eval_stepper_fn,
            metadata=evaluator_meta,
            description=evaluator_description,
            config_schema=config_schema,
        )
        _set_custom_options(evaluator_meta, self)


def define_evaluator(
    registry: Registry,
    name: str,
    display_name: str,
    definition: str,
    fn: EvaluatorFn,
    is_billed: bool = False,
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    description: str | None = None,
) -> Evaluator:
    """Register an evaluator that calls ``fn`` with one ``EvaluatorRequest`` per dataset row."""
    action = Evaluator(
        name,
        fn,
        display_name=display_name,
        definition=definition,
        is_billed=is_billed,
        config_schema=config_schema,
        metadata=metadata,
        description=description,
    )
    registry.register_action_from_instance(action)
    return action


class BatchEvaluator(Action[BatchEvaluatorRequest, EvalResponse, Never]):
    """Batch evaluator action that runs ``fn`` once on the whole ``BatchEvaluatorRequest``, without registering it.

    Annotate ``fn``'s parameter as ``BatchEvaluatorRequest[Cfg]`` to get
    ``options`` validated into ``Cfg``. ``fn`` returns ``list[EvaluatorResponse]``. The action wraps the list so
    ``action.run(...).response`` is an ``EvalResponse``.
    Plugin ``init`` / ``resolve`` / ``list_actions`` return this.
    ``define_batch_evaluator`` registers it.
    """

    def __init__(
        self,
        name: str,
        fn: BatchEvaluatorFn,
        *,
        display_name: str,
        definition: str,
        is_billed: bool = False,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> None:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError(f"Action handlers must be async functions. Got sync function for '{name}'.")
        _check_batch_annotation(fn, name)

        evaluator_meta = _evaluator_metadata(name, display_name, definition, is_billed, config_schema, metadata)
        evaluator_description = _get_func_description(fn, description)

        # the action hands back the rows as one model so the Dev UI and
        # `genkit eval:run` get a JSON array, the same as a per-row evaluator.
        # fn stays the metadata_fn, so its signature is still checked when built.
        async def batch_fn(req: BatchEvaluatorRequest, ctx: ActionRunContext) -> EvalResponse:
            return EvalResponse(await self.params.call(fn, req, ctx))

        super().__init__(
            kind=ActionKind.EVALUATOR,
            name=name,
            fn=batch_fn,
            # An unannotated fn still gets a BatchEvaluatorRequest, not the raw JSON dict.
            metadata_fn=with_request_annotation(fn, BatchEvaluatorRequest, kind=ActionKind.EVALUATOR),
            metadata=evaluator_meta,
            description=evaluator_description,
            config_schema=config_schema,
        )
        _set_custom_options(evaluator_meta, self)


def define_batch_evaluator(
    registry: Registry,
    name: str,
    display_name: str,
    definition: str,
    fn: BatchEvaluatorFn,
    is_billed: bool = False,
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    description: str | None = None,
) -> BatchEvaluator:
    """Register a batch evaluator that runs ``fn`` once on the whole ``BatchEvaluatorRequest``."""
    action = BatchEvaluator(
        name,
        fn,
        display_name=display_name,
        definition=definition,
        is_billed=is_billed,
        config_schema=config_schema,
        metadata=metadata,
        description=description,
    )
    registry.register_action_from_instance(action)
    return action
