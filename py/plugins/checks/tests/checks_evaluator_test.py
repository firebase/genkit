# Copyright 2026 Google LLC
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

"""Tests for the Checks evaluator functionality.

These tests verify parity with the JS implementation in:
js/plugins/checks/src/evaluation.ts
"""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.core.action.types import ActionKind
from genkit.core.typing import BaseDataPoint, EvalRequest
from genkit.plugins.checks import Checks, ChecksEvaluationConfig, ChecksMetricType
from genkit.plugins.checks.guardrails import ClassifyContentResponse, PolicyResult


class TestChecksEvaluator:
    """Tests for Checks evaluator matching JS checksEvaluators."""

    @pytest.mark.asyncio
    async def test_evaluator_name_matches_js(self) -> None:
        """Test evaluator is named 'checks/guardrails' matching JS."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')

        assert action is not None
        assert action.name == 'checks/guardrails'

    @pytest.mark.asyncio
    async def test_evaluator_metadata_matches_js(self) -> None:
        """Test evaluator metadata structure matches JS implementation."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[
                    ChecksMetricType.DANGEROUS_CONTENT,
                    ChecksMetricType.HARASSMENT,
                ],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')

        assert action is not None
        assert action.metadata is not None
        assert 'evaluator' in action.metadata

        evaluator_meta = cast(dict[str, Any], action.metadata['evaluator'])
        assert 'definition' in evaluator_meta
        assert 'displayName' in evaluator_meta
        assert evaluator_meta['displayName'] == 'checks/guardrails'

    @pytest.mark.asyncio
    async def test_evaluator_definition_includes_policy_types(self) -> None:
        """Test evaluator definition includes configured policy types (matching JS)."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[
                    ChecksMetricType.DANGEROUS_CONTENT,
                    ChecksMetricType.HARASSMENT,
                ],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')

        assert action is not None
        assert action.metadata is not None

        evaluator_meta = cast(dict[str, Any], action.metadata['evaluator'])
        definition = str(evaluator_meta['definition'])
        assert 'DANGEROUS_CONTENT' in definition
        assert 'HARASSMENT' in definition

    @pytest.mark.asyncio
    async def test_evaluator_returns_scores_per_policy(self) -> None:
        """Test evaluator returns a score for each policy (matching JS evaluationResults)."""
        mock_response = ClassifyContentResponse(
            policy_results=[
                PolicyResult(
                    policy_type='DANGEROUS_CONTENT',
                    score=0.1,
                    violation_result='NON_VIOLATIVE',
                ),
                PolicyResult(
                    policy_type='HARASSMENT',
                    score=0.8,
                    violation_result='VIOLATIVE',
                ),
            ]
        )

        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[
                    ChecksMetricType.DANGEROUS_CONTENT,
                    ChecksMetricType.HARASSMENT,
                ],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        # Get the evaluator action
        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')
        assert action is not None

        # Mock the guardrails client
        plugin._guardrails = MagicMock()
        plugin._guardrails.classify_content = AsyncMock(return_value=mock_response)

        # Create evaluation request
        request = EvalRequest(
            dataset=[
                BaseDataPoint(
                    test_case_id='test-1',
                    input='test input',
                    output='test output to evaluate',
                ),
            ],
            eval_run_id='run-1',
        )

        # Run the evaluator
        result = await action.arun(request)

        # Verify we get scores for each policy
        # result.response is ActionResponse[EvalResponse], EvalResponse is RootModel[list[EvalFnResponse]]
        eval_fn_responses = result.response.root
        assert len(eval_fn_responses) == 1
        eval_response = eval_fn_responses[0]

        # Should have evaluation as list of scores (matching JS evaluationResults array)
        assert eval_response.evaluation is not None
        if isinstance(eval_response.evaluation, list):
            assert len(eval_response.evaluation) == 2

            # Check score structure matches JS
            score_ids = [s.id for s in eval_response.evaluation]
            assert 'DANGEROUS_CONTENT' in score_ids
            assert 'HARASSMENT' in score_ids

    @pytest.mark.asyncio
    async def test_evaluator_score_structure_matches_js(self) -> None:
        """Test individual score structure matches JS implementation."""
        mock_response = ClassifyContentResponse(
            policy_results=[
                PolicyResult(
                    policy_type='DANGEROUS_CONTENT',
                    score=0.75,
                    violation_result='VIOLATIVE',
                ),
            ]
        )

        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')
        assert action is not None

        plugin._guardrails = MagicMock()
        plugin._guardrails.classify_content = AsyncMock(return_value=mock_response)

        request = EvalRequest(
            dataset=[
                BaseDataPoint(
                    test_case_id='test-1',
                    output='content to evaluate',
                ),
            ],
            eval_run_id='run-1',
        )

        result = await action.arun(request)

        # EvalResponse is RootModel[list[EvalFnResponse]]
        eval_fn_responses = result.response.root
        eval_response = eval_fn_responses[0]
        assert isinstance(eval_response.evaluation, list)

        score = eval_response.evaluation[0]

        # Verify JS-compatible structure:
        # { id: result.policyType, score: result.score, details: { reasoning: `Status ${result.violationResult}` } }
        assert score.id == 'DANGEROUS_CONTENT'
        assert score.score == 0.75
        assert score.details is not None
        assert 'Status VIOLATIVE' in (score.details.reasoning or '')

    @pytest.mark.asyncio
    async def test_evaluator_preserves_test_case_id(self) -> None:
        """Test evaluator preserves testCaseId (matching JS)."""
        mock_response = ClassifyContentResponse(
            policy_results=[
                PolicyResult(
                    policy_type='HARASSMENT',
                    score=0.5,
                    violation_result='NON_VIOLATIVE',
                ),
            ]
        )

        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.HARASSMENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')
        assert action is not None

        plugin._guardrails = MagicMock()
        plugin._guardrails.classify_content = AsyncMock(return_value=mock_response)

        request = EvalRequest(
            dataset=[
                BaseDataPoint(
                    test_case_id='my-custom-id-123',
                    output='test output',
                ),
            ],
            eval_run_id='run-1',
        )

        result = await action.arun(request)

        # EvalResponse is RootModel[list[EvalFnResponse]]
        assert result.response.root[0].test_case_id == 'my-custom-id-123'

    @pytest.mark.asyncio
    async def test_evaluator_generates_test_case_id_if_missing(self) -> None:
        """Test evaluator generates testCaseId if not provided."""
        mock_response = ClassifyContentResponse(
            policy_results=[
                PolicyResult(
                    policy_type='HARASSMENT',
                    score=0.5,
                    violation_result='NON_VIOLATIVE',
                ),
            ]
        )

        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.HARASSMENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')
        assert action is not None

        plugin._guardrails = MagicMock()
        plugin._guardrails.classify_content = AsyncMock(return_value=mock_response)

        request = EvalRequest(
            dataset=[
                BaseDataPoint(
                    test_case_id=None,  # No ID provided
                    output='test output',
                ),
            ],
            eval_run_id='run-1',
        )

        result = await action.arun(request)

        # Should have generated a test case ID
        # EvalResponse is RootModel[list[EvalFnResponse]]
        assert result.response.root[0].test_case_id is not None
        assert len(result.response.root[0].test_case_id) > 0

    @pytest.mark.asyncio
    async def test_evaluator_evaluates_output_content(self) -> None:
        """Test evaluator evaluates the output field (matching JS datapoint.output)."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')
        assert action is not None

        mock_classify = AsyncMock(
            return_value=ClassifyContentResponse(
                policy_results=[
                    PolicyResult(
                        policy_type='DANGEROUS_CONTENT',
                        score=0.5,
                        violation_result='NON_VIOLATIVE',
                    ),
                ]
            )
        )
        plugin._guardrails = MagicMock()
        plugin._guardrails.classify_content = mock_classify

        request = EvalRequest(
            dataset=[
                BaseDataPoint(
                    test_case_id='test-1',
                    input='this is the input',  # Should NOT be evaluated
                    output='this is the output to evaluate',  # This should be evaluated
                ),
            ],
            eval_run_id='run-1',
        )

        await action.arun(request)

        # Verify the output content was sent to classify_content
        mock_classify.assert_called_once()
        call_args = mock_classify.call_args
        content = call_args[1]['content']
        assert content == 'this is the output to evaluate'

    @pytest.mark.asyncio
    async def test_evaluator_handles_missing_output(self) -> None:
        """Test evaluator handles datapoint with no output."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')
        assert action is not None

        plugin._guardrails = MagicMock()

        request = EvalRequest(
            dataset=[
                BaseDataPoint(
                    test_case_id='test-1',
                    output=None,  # No output
                ),
            ],
            eval_run_id='run-1',
        )

        result = await action.arun(request)

        # Should return an error response
        # EvalResponse is RootModel[list[EvalFnResponse]]
        eval_response = result.response.root[0]
        assert eval_response.evaluation is not None
        # When there's no output, we should get an error score
        if not isinstance(eval_response.evaluation, list):
            assert eval_response.evaluation.error is not None


class TestChecksEvaluatorSingleEvaluator:
    """Tests verifying the plugin creates a single guardrails evaluator."""

    @pytest.mark.asyncio
    async def test_only_one_evaluator_action(self) -> None:
        """Test plugin returns only one evaluator (checks/guardrails)."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[
                    ChecksMetricType.DANGEROUS_CONTENT,
                    ChecksMetricType.HARASSMENT,
                    ChecksMetricType.HATE_SPEECH,
                ],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        actions = await plugin.list_actions()

        # Should only be one evaluator, not one per metric
        assert len(actions) == 1
        assert actions[0].name == 'checks/guardrails'
        assert actions[0].kind == ActionKind.EVALUATOR

    @pytest.mark.asyncio
    async def test_individual_metric_not_resolvable(self) -> None:
        """Test individual metrics are not resolvable as separate evaluators."""
        plugin = Checks(
            project_id='test-project',
            evaluation=ChecksEvaluationConfig(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
            ),
        )

        with patch.object(plugin, '_initialize_auth') as mock_auth:
            mock_auth.return_value = MagicMock()
            await plugin.init(registry=MagicMock())

        # Should NOT be able to resolve individual metrics
        result = await plugin.resolve(ActionKind.EVALUATOR, 'checks/dangerous_content')
        assert result is None

        result = await plugin.resolve(ActionKind.EVALUATOR, 'checks/DANGEROUS_CONTENT')
        assert result is None
