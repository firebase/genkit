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

"""Tests for the Checks AI Safety plugin."""

from unittest.mock import MagicMock, patch

import pytest

from genkit.core.action import ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.plugins.checks import Checks, ChecksEvaluationConfig, ChecksMetricType


def test_plugin_name() -> None:
    """Test plugin has correct name."""
    plugin = Checks(project_id='test-project')
    assert plugin.name == 'checks'


def test_init_with_project_id() -> None:
    """Test plugin initialization with project ID."""
    plugin = Checks(project_id='my-project')
    assert plugin._project_id == 'my-project'


def test_init_with_evaluation_config() -> None:
    """Test plugin initialization with evaluation config."""
    config = ChecksEvaluationConfig(
        metrics=[
            ChecksMetricType.DANGEROUS_CONTENT,
            ChecksMetricType.HARASSMENT,
        ]
    )
    plugin = Checks(project_id='my-project', evaluation=config)
    assert plugin._evaluation == config


def test_init_with_evaluation_dict() -> None:
    """Test plugin initialization with evaluation as dict."""
    eval_dict = {
        'metrics': [
            ChecksMetricType.DANGEROUS_CONTENT,
            ChecksMetricType.HATE_SPEECH,
        ]
    }
    plugin = Checks(project_id='my-project', evaluation=eval_dict)
    assert plugin._evaluation == eval_dict


def test_init_with_google_auth_options() -> None:
    """Test plugin initialization with Google auth options."""
    auth_opts = {'credentials_file': '/path/to/creds.json'}
    plugin = Checks(project_id='my-project', google_auth_options=auth_opts)
    assert plugin._google_auth_options == auth_opts


@pytest.mark.asyncio
async def test_init_returns_empty_list() -> None:
    """Test that init() returns empty list (uses lazy loading)."""
    plugin = Checks(project_id='test-project')

    # Mock authentication
    with patch.object(plugin, '_initialize_auth') as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = mock_creds

        result = await plugin.init(registry=None)
        assert result == []
        assert plugin._credentials == mock_creds


@pytest.mark.asyncio
async def test_init_raises_without_project_id() -> None:
    """Test that init() raises ValueError without project_id."""
    plugin = Checks()  # No project_id

    # Mock authentication to not set project from credentials
    with patch.object(plugin, '_initialize_auth') as mock_auth:
        mock_creds = MagicMock()
        mock_auth.return_value = mock_creds

        with pytest.raises(ValueError, match="missing the 'project_id'"):
            await plugin.init(registry=None)


@pytest.mark.asyncio
async def test_resolve_returns_none_for_non_evaluator() -> None:
    """Test that resolve returns None for non-evaluator action types."""
    plugin = Checks(project_id='test-project')
    plugin._credentials = MagicMock()  # Set up credentials

    result = await plugin.resolve(ActionKind.MODEL, 'checks/dangerous_content')
    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_none_for_other_namespace() -> None:
    """Test that resolve returns None for actions not in checks namespace."""
    plugin = Checks(project_id='test-project')
    plugin._credentials = MagicMock()

    result = await plugin.resolve(ActionKind.EVALUATOR, 'other/evaluator')
    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_evaluator_action() -> None:
    """Test that resolve returns the guardrails evaluator action."""
    plugin = Checks(
        project_id='test-project',
        evaluation=ChecksEvaluationConfig(
            metrics=[
                ChecksMetricType.DANGEROUS_CONTENT,
                ChecksMetricType.HARASSMENT,
            ]
        ),
    )

    # Create a mock registry
    mock_registry = MagicMock()

    # Initialize plugin
    with patch.object(plugin, '_initialize_auth') as mock_auth:
        mock_auth.return_value = MagicMock()
        await plugin.init(registry=mock_registry)

    # Resolve the guardrails evaluator
    action = await plugin.resolve(ActionKind.EVALUATOR, 'checks/guardrails')

    assert action is not None
    assert action.name == 'checks/guardrails'
    assert action.kind == ActionKind.EVALUATOR
    assert action.metadata is not None
    assert 'evaluator' in action.metadata


@pytest.mark.asyncio
async def test_resolve_returns_none_for_non_guardrails_evaluator() -> None:
    """Test that resolve returns None for individual metric evaluators."""
    plugin = Checks(
        project_id='test-project',
        evaluation=ChecksEvaluationConfig(metrics=[ChecksMetricType.DANGEROUS_CONTENT]),
    )

    # Initialize plugin
    with patch.object(plugin, '_initialize_auth') as mock_auth:
        mock_auth.return_value = MagicMock()
        await plugin.init(registry=None)

    # Should return None for individual metric names (not supported)
    result = await plugin.resolve(ActionKind.EVALUATOR, 'checks/dangerous_content')
    assert result is None


@pytest.mark.asyncio
async def test_list_actions_returns_evaluator_metadata() -> None:
    """Test that list_actions returns metadata for the guardrails evaluator.

    The Checks plugin returns a single evaluator (checks/guardrails) that
    evaluates all configured metrics, matching the JS implementation.
    """
    plugin = Checks(
        project_id='test-project',
        evaluation=ChecksEvaluationConfig(
            metrics=[
                ChecksMetricType.DANGEROUS_CONTENT,
                ChecksMetricType.HARASSMENT,
            ]
        ),
    )

    # Initialize plugin to load metrics
    with patch.object(plugin, '_initialize_auth') as mock_auth:
        mock_auth.return_value = MagicMock()
        await plugin.init(registry=None)

    actions = await plugin.list_actions()

    # Should return a single guardrails evaluator
    assert len(actions) == 1
    assert all(isinstance(a, ActionMetadata) for a in actions)
    assert all(a.kind == ActionKind.EVALUATOR for a in actions)
    assert actions[0].name == 'checks/guardrails'


@pytest.mark.asyncio
async def test_list_actions_empty_without_metrics() -> None:
    """Test that list_actions returns empty list when no metrics configured."""
    plugin = Checks(project_id='test-project')

    # Initialize plugin
    with patch.object(plugin, '_initialize_auth') as mock_auth:
        mock_auth.return_value = MagicMock()
        await plugin.init(registry=None)

    actions = await plugin.list_actions()
    assert actions == []


def test_checks_metric_type_values() -> None:
    """Test that ChecksMetricType has expected values."""
    assert ChecksMetricType.DANGEROUS_CONTENT.value == 'DANGEROUS_CONTENT'
    assert ChecksMetricType.HARASSMENT.value == 'HARASSMENT'
    assert ChecksMetricType.HATE_SPEECH.value == 'HATE_SPEECH'
    assert ChecksMetricType.SEXUALLY_EXPLICIT.value == 'SEXUALLY_EXPLICIT'
    assert ChecksMetricType.VIOLENCE_AND_GORE.value == 'VIOLENCE_AND_GORE'


def test_checks_evaluation_config_defaults() -> None:
    """Test ChecksEvaluationConfig default values."""
    config = ChecksEvaluationConfig()
    assert config.metrics == []


def test_checks_evaluation_config_with_metrics() -> None:
    """Test ChecksEvaluationConfig with metrics."""
    config = ChecksEvaluationConfig(
        metrics=[
            ChecksMetricType.DANGEROUS_CONTENT,
            ChecksMetricType.HARASSMENT,
            ChecksMetricType.HATE_SPEECH,
        ]
    )
    assert len(config.metrics) == 3
    assert ChecksMetricType.DANGEROUS_CONTENT in config.metrics
