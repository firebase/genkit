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

"""Genkit Evaluators plugin: regex, deep_equal, jsonata."""

import json
import re
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, TypedDict

from genkit._core._action import Action, ActionKind
from genkit._core._plugin import Plugin
from genkit._core._typing import (
    BaseDataPoint,
    EvalFnResponse,
    EvalRequest,
    EvalResponse,
    EvalStatusEnum,
    Score,
)
from genkit.plugin_api import to_json_schema

try:
    from jsonata import Jsonata
except ImportError:
    Jsonata = None  # type: ignore[misc, assignment]

PROVIDER = 'genkitEval'


def genkit_eval_name(local: str) -> str:
    """Return namespaced evaluator name."""
    return f'{PROVIDER}/{local}'


# EvaluatorFn: (datapoint, options) -> EvalFnResponse
EvaluatorFn = Callable[[BaseDataPoint, object | None], Coroutine[Any, Any, EvalFnResponse]]


def _make_eval_stepper(metric_fn: EvaluatorFn) -> Callable[[EvalRequest], Coroutine[Any, Any, EvalResponse]]:
    """Wrap a per-datapoint metric fn into an EvalRequest -> EvalResponse stepper."""

    async def _stepper(req: EvalRequest) -> EvalResponse:
        responses: list[EvalFnResponse] = []
        for datapoint in req.dataset:
            if datapoint.test_case_id is None:
                datapoint.test_case_id = str(uuid.uuid4())
            try:
                out = await metric_fn(datapoint, req.options)
                responses.append(out)
            except Exception as e:
                responses.append(
                    EvalFnResponse(
                        test_case_id=datapoint.test_case_id or '',
                        evaluation=Score(
                            error=f'Evaluation failed: {e!s}',
                            status=EvalStatusEnum.FAIL,
                        ),
                    )
                )
        return EvalResponse(responses)

    return _stepper


async def _regex_impl(datapoint: BaseDataPoint, _options: object | None = None) -> EvalFnResponse:
    """Regex evaluator: reference must be a regex string; output tested against it."""
    if datapoint.output is None:
        raise ValueError('output was not provided')
    if datapoint.reference is None:
        raise ValueError('reference was not provided')
    if not isinstance(datapoint.reference, str):
        raise ValueError('reference must be a string (regex)')
    output_str = datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
    match = bool(re.search(datapoint.reference, output_str))
    status = EvalStatusEnum.PASS_ if match else EvalStatusEnum.FAIL
    return EvalFnResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=Score(score=match, status=status),
    )


async def _deep_equal_impl(datapoint: BaseDataPoint, _options: object | None = None) -> EvalFnResponse:
    """Deep equal evaluator: output must equal reference."""
    if datapoint.output is None:
        raise ValueError('output was not provided')
    if datapoint.reference is None:
        raise ValueError('reference was not provided')
    equal = datapoint.output == datapoint.reference
    status = EvalStatusEnum.PASS_ if equal else EvalStatusEnum.FAIL
    return EvalFnResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=Score(score=equal, status=status),
    )


async def _jsonata_impl(datapoint: BaseDataPoint, _options: object | None = None) -> EvalFnResponse:
    """JSONata evaluator: reference is a JSONata expression; evaluated against output."""
    if datapoint.output is None:
        raise ValueError('output was not provided')
    if datapoint.reference is None:
        raise ValueError('reference was not provided')
    if not isinstance(datapoint.reference, str):
        raise ValueError('reference must be a string (jsonata)')
    if Jsonata is None:
        raise RuntimeError('jsonata-python is required for jsonata evaluator')
    expr = Jsonata(datapoint.reference)
    result = expr.evaluate(datapoint.output)
    # Go: false, "", nil -> FAIL; else PASS
    passed = result not in (False, '', None)
    status = EvalStatusEnum.PASS_ if passed else EvalStatusEnum.FAIL
    return EvalFnResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=Score(score=result, status=status),
    )


class _EvaluatorMeta(TypedDict):
    """Evaluator config: all keys required."""

    display_name: str
    definition: str
    is_billed: bool
    fn: EvaluatorFn


def _to_evaluator_metadata(meta: _EvaluatorMeta) -> dict[str, object]:
    """Convert evaluator config dict to action metadata."""
    return {
        'evaluator': {
            'evaluatorDisplayName': meta['display_name'],
            'evaluatorDefinition': meta['definition'],
            'evaluatorIsBilled': meta['is_billed'],
            'label': '',
        }
    }


# Each evaluator: name -> {display_name, definition, is_billed, fn}
EVALUATOR_CONFIG: dict[str, _EvaluatorMeta] = {
    'regex': {
        'display_name': 'RegExp',
        'definition': 'Tests output against the regexp provided as reference',
        'is_billed': False,
        'fn': _regex_impl,
    },
    'deep_equal': {
        'display_name': 'Deep Equals',
        'definition': 'Tests equality of output against the provided reference',
        'is_billed': False,
        'fn': _deep_equal_impl,
    },
    'jsonata': {
        'display_name': 'JSONata',
        'definition': 'Tests JSONata expression (provided in reference) against output',
        'is_billed': False,
        'fn': _jsonata_impl,
    },
}


class GenkitEval(Plugin):
    """Plugin providing regex, deep_equal, and jsonata evaluators (matching Go/JS)."""

    name = PROVIDER

    def __init__(self) -> None:
        """Initialize the plugin (actions are created lazily)."""
        self._actions: list[Action] | None = None

    def _get_actions(self) -> list[Action]:
        """Create and cache evaluator actions."""
        if self._actions is not None:
            return self._actions
        self._actions = [
            Action(
                kind=ActionKind.EVALUATOR,
                name=name,
                fn=_make_eval_stepper(cfg['fn']),
                metadata=_to_evaluator_metadata(cfg),
            )
            for name, cfg in EVALUATOR_CONFIG.items()
        ]
        return self._actions

    async def init(self) -> list[Action]:
        """Return evaluator actions."""
        return self._get_actions()

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve evaluator by name."""
        if action_type != ActionKind.EVALUATOR:
            return None
        if not name.startswith(f'{PROVIDER}/'):
            return None
        local = name.split('/', 1)[1]
        actions = self._get_actions()
        for a in actions:
            if a.name == local or a.name == name:
                return a
        return None

    async def list_actions(self) -> list:
        """List evaluator actions (metadata)."""
        from genkit._core._action import ActionMetadata

        actions = self._get_actions()
        return [
            ActionMetadata(
                kind=ActionKind.EVALUATOR,
                name=f'{PROVIDER}/{a.name}',
                input_json_schema=to_json_schema(EvalRequest),
                output_json_schema=to_json_schema(list[EvalFnResponse]),
                metadata=a.metadata,
            )
            for a in actions
        ]
