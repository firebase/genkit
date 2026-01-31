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

"""Tests for the Checks metrics module.

These tests verify parity with the JS implementation in:
js/plugins/checks/src/metrics.ts
"""

from genkit.plugins.checks.metrics import (
    ChecksMetric,
    ChecksMetricConfig,
    ChecksMetricType,
    is_metric_config,
)


class TestChecksMetricType:
    """Tests for ChecksMetricType enum matching JS ChecksEvaluationMetricType."""

    def test_dangerous_content_value(self) -> None:
        """Test DANGEROUS_CONTENT value matches JS."""
        assert ChecksMetricType.DANGEROUS_CONTENT.value == 'DANGEROUS_CONTENT'

    def test_pii_soliciting_reciting_value(self) -> None:
        """Test PII_SOLICITING_RECITING value matches JS."""
        assert ChecksMetricType.PII_SOLICITING_RECITING.value == 'PII_SOLICITING_RECITING'

    def test_harassment_value(self) -> None:
        """Test HARASSMENT value matches JS."""
        assert ChecksMetricType.HARASSMENT.value == 'HARASSMENT'

    def test_sexually_explicit_value(self) -> None:
        """Test SEXUALLY_EXPLICIT value matches JS."""
        assert ChecksMetricType.SEXUALLY_EXPLICIT.value == 'SEXUALLY_EXPLICIT'

    def test_hate_speech_value(self) -> None:
        """Test HATE_SPEECH value matches JS."""
        assert ChecksMetricType.HATE_SPEECH.value == 'HATE_SPEECH'

    def test_medical_info_value(self) -> None:
        """Test MEDICAL_INFO value matches JS."""
        assert ChecksMetricType.MEDICAL_INFO.value == 'MEDICAL_INFO'

    def test_violence_and_gore_value(self) -> None:
        """Test VIOLENCE_AND_GORE value matches JS."""
        assert ChecksMetricType.VIOLENCE_AND_GORE.value == 'VIOLENCE_AND_GORE'

    def test_obscenity_and_profanity_value(self) -> None:
        """Test OBSCENITY_AND_PROFANITY value matches JS."""
        assert ChecksMetricType.OBSCENITY_AND_PROFANITY.value == 'OBSCENITY_AND_PROFANITY'

    def test_all_metric_types_exist(self) -> None:
        """Test all JS ChecksEvaluationMetricType values exist in Python."""
        js_metric_types = [
            'DANGEROUS_CONTENT',
            'PII_SOLICITING_RECITING',
            'HARASSMENT',
            'SEXUALLY_EXPLICIT',
            'HATE_SPEECH',
            'MEDICAL_INFO',
            'VIOLENCE_AND_GORE',
            'OBSCENITY_AND_PROFANITY',
        ]
        python_metric_types = [m.value for m in ChecksMetricType]

        for js_type in js_metric_types:
            assert js_type in python_metric_types, f'Missing metric type: {js_type}'

    def test_metric_type_count_matches_js(self) -> None:
        """Test Python has same number of metric types as JS."""
        # JS has 8 metric types
        assert len(ChecksMetricType) == 8

    def test_metric_type_is_string_enum(self) -> None:
        """Test ChecksMetricType is a string enum for JSON serialization."""
        # ChecksMetricType is str + Enum, so value is the string
        assert ChecksMetricType.DANGEROUS_CONTENT.value == 'DANGEROUS_CONTENT'
        # Can be used where strings are expected
        assert str(ChecksMetricType.DANGEROUS_CONTENT.value) == 'DANGEROUS_CONTENT'


class TestChecksMetricConfig:
    """Tests for ChecksMetricConfig dataclass matching JS ChecksEvaluationMetricConfig."""

    def test_config_with_type_only(self) -> None:
        """Test config with just type (no threshold)."""
        config = ChecksMetricConfig(type=ChecksMetricType.HARASSMENT)
        assert config.type == ChecksMetricType.HARASSMENT
        assert config.threshold is None

    def test_config_with_threshold(self) -> None:
        """Test config with type and threshold (matching JS)."""
        config = ChecksMetricConfig(
            type=ChecksMetricType.DANGEROUS_CONTENT,
            threshold=0.8,
        )
        assert config.type == ChecksMetricType.DANGEROUS_CONTENT
        assert config.threshold == 0.8

    def test_config_threshold_float(self) -> None:
        """Test threshold accepts float values."""
        config = ChecksMetricConfig(
            type=ChecksMetricType.HATE_SPEECH,
            threshold=0.5,
        )
        assert config.threshold == 0.5


class TestIsMetricConfig:
    """Tests for is_metric_config function matching JS isConfig."""

    def test_returns_true_for_config(self) -> None:
        """Test is_metric_config returns True for ChecksMetricConfig."""
        config = ChecksMetricConfig(type=ChecksMetricType.HARASSMENT)
        assert is_metric_config(config) is True

    def test_returns_false_for_metric_type(self) -> None:
        """Test is_metric_config returns False for ChecksMetricType."""
        assert is_metric_config(ChecksMetricType.HARASSMENT) is False

    def test_returns_false_for_all_metric_types(self) -> None:
        """Test is_metric_config returns False for all metric types."""
        for metric_type in ChecksMetricType:
            assert is_metric_config(metric_type) is False

    def test_returns_true_for_config_with_threshold(self) -> None:
        """Test is_metric_config returns True for config with threshold."""
        config = ChecksMetricConfig(
            type=ChecksMetricType.DANGEROUS_CONTENT,
            threshold=0.9,
        )
        assert is_metric_config(config) is True


class TestChecksMetricUnion:
    """Tests for ChecksMetric type alias matching JS ChecksEvaluationMetric."""

    def test_metric_type_is_valid_metric(self) -> None:
        """Test ChecksMetricType is a valid ChecksMetric."""
        metric: ChecksMetric = ChecksMetricType.HARASSMENT
        assert isinstance(metric, ChecksMetricType)

    def test_metric_config_is_valid_metric(self) -> None:
        """Test ChecksMetricConfig is a valid ChecksMetric."""
        metric: ChecksMetric = ChecksMetricConfig(type=ChecksMetricType.HARASSMENT)
        assert isinstance(metric, ChecksMetricConfig)

    def test_list_of_mixed_metrics(self) -> None:
        """Test list can contain both types (matching JS usage)."""
        metrics: list[ChecksMetric] = [
            ChecksMetricType.DANGEROUS_CONTENT,
            ChecksMetricConfig(
                type=ChecksMetricType.HARASSMENT,
                threshold=0.8,
            ),
            ChecksMetricType.HATE_SPEECH,
        ]
        assert len(metrics) == 3
        assert is_metric_config(metrics[0]) is False
        assert is_metric_config(metrics[1]) is True
        assert is_metric_config(metrics[2]) is False
