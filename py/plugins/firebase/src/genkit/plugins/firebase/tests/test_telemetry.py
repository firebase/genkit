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

"""Tests for Firebase telemetry functionality."""

import json
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import Status, StatusCode

from genkit.plugins.firebase import add_firebase_telemetry


def test_add_firebase_telemetry():
    """Test that add_firebase_telemetry calls add_gcp_telemetry with force_export=False."""
    with patch('genkit.plugins.firebase.add_gcp_telemetry') as mock_gcp_telemetry:
        add_firebase_telemetry()
        mock_gcp_telemetry.assert_called_once_with(force_export=False)


class TestMetrics:
    """Tests for metrics recording functionality."""

    def test_record_generate_metrics_with_valid_span(self):
        """Test metrics recording for a valid model span."""
        from genkit.plugins.google_cloud.telemetry.metrics import record_generate_metrics

        # Create mock span with model execution data
        span = Mock(spec=ReadableSpan)
        span.attributes = {
            'genkit:type': 'action',
            'genkit:metadata:subtype': 'model',
            'genkit:name': 'gemini-2.0-flash',
            'genkit:path': '/{myFlow,t:flow}',
            'genkit:output': json.dumps({
                'usage': {
                    'inputTokens': 100,
                    'outputTokens': 50,
                    'inputCharacters': 500,
                    'outputCharacters': 250,
                }
            }),
        }
        span.status = Status(StatusCode.OK)
        span.start_time = 1000000000
        span.end_time = 1100000000  # 100ms later

        # Should not raise exception
        record_generate_metrics(span)

    def test_record_generate_metrics_with_error(self):
        """Test metrics recording for failed model execution."""
        from genkit.plugins.google_cloud.telemetry.metrics import record_generate_metrics

        span = Mock(spec=ReadableSpan)
        span.attributes = {
            'genkit:type': 'action',
            'genkit:metadata:subtype': 'model',
            'genkit:name': 'gemini-2.0-flash',
            'genkit:path': '/{myFlow,t:flow}',
        }
        span.status = Status(StatusCode.ERROR)
        span.start_time = 1000000000
        span.end_time = 1100000000

        # Should not raise exception
        record_generate_metrics(span)

    def test_record_generate_metrics_skips_non_model_spans(self):
        """Test that non-model spans are skipped."""
        from genkit.plugins.google_cloud.telemetry.metrics import record_generate_metrics

        span = Mock(spec=ReadableSpan)
        span.attributes = {
            'genkit:type': 'action',
            'genkit:metadata:subtype': 'flow',  # Not a model
        }

        # Should not raise exception
        record_generate_metrics(span)

    def test_record_generate_metrics_with_no_attributes(self):
        """Test that spans without attributes are handled gracefully."""
        from genkit.plugins.google_cloud.telemetry.metrics import record_generate_metrics

        span = Mock(spec=ReadableSpan)
        span.attributes = None

        # Should not raise exception
        record_generate_metrics(span)

    def test_record_generate_metrics_with_all_usage_types(self):
        """Test metrics recording with all usage types."""
        from genkit.plugins.google_cloud.telemetry.metrics import record_generate_metrics

        span = Mock(spec=ReadableSpan)
        span.attributes = {
            'genkit:type': 'action',
            'genkit:metadata:subtype': 'model',
            'genkit:name': 'gemini-2.0-flash',
            'genkit:path': '/{testFlow,t:flow}',
            'genkit:output': json.dumps({
                'usage': {
                    'inputTokens': 100,
                    'outputTokens': 50,
                    'inputCharacters': 500,
                    'outputCharacters': 250,
                    'inputImages': 2,
                    'outputImages': 1,
                    'inputVideos': 1,
                    'outputVideos': 0,
                    'inputAudio': 1,
                    'outputAudio': 1,
                }
            }),
        }
        span.status = Status(StatusCode.OK)
        span.start_time = 1000000000
        span.end_time = 1200000000

        # Should not raise exception
        record_generate_metrics(span)

    def test_record_generate_metrics_with_invalid_usage(self):
        """Test metrics recording handles invalid usage data gracefully."""
        from genkit.plugins.google_cloud.telemetry.metrics import record_generate_metrics

        span = Mock(spec=ReadableSpan)
        span.attributes = {
            'genkit:type': 'action',
            'genkit:metadata:subtype': 'model',
            'genkit:name': 'test-model',
            'genkit:path': '/{flow,t:flow}',
            'genkit:output': json.dumps({
                'usage': {
                    'inputTokens': 'invalid',  # Invalid type
                    'outputTokens': None,
                }
            }),
        }
        span.status = Status(StatusCode.OK)
        span.start_time = 1000000000
        span.end_time = 1100000000

        # Should not raise exception
        record_generate_metrics(span)

    def test_extract_feature_name(self):
        """Test feature name extraction from paths."""
        from genkit.plugins.google_cloud.telemetry.metrics import _extract_feature_name

        assert _extract_feature_name('/{myFlow,t:flow}') == 'myFlow'
        assert _extract_feature_name('/{outer,t:flow}/{inner,t:flow}') == 'outer'
        assert _extract_feature_name('') == '<unknown>'
        assert _extract_feature_name('/invalid') == '<unknown>'
        assert _extract_feature_name('/{test123,t:flow}') == 'test123'


class TestGCPTelemetry:
    """Tests for GCP telemetry configuration."""

    def test_add_gcp_telemetry_in_dev_environment(self):
        """Test that telemetry is not added in dev environment by default."""
        from genkit.plugins.google_cloud.telemetry.tracing import add_gcp_telemetry

        with patch(
            "genkit.plugins.google_cloud.telemetry.tracing.is_dev_environment",
            return_value=True,
        ):
            with patch(
                "genkit.plugins.google_cloud.telemetry.tracing.add_custom_exporter"
            ) as mock_add:
                add_gcp_telemetry(force_export=False)
                mock_add.assert_not_called()

    def test_add_gcp_telemetry_force_export_in_dev(self):
        """Test that force_export=True works in dev environment."""
        from genkit.plugins.google_cloud.telemetry.tracing import add_gcp_telemetry

        with patch(
            "genkit.plugins.google_cloud.telemetry.tracing.is_dev_environment",
            return_value=True,
        ):
            with patch(
                "genkit.plugins.google_cloud.telemetry.tracing.add_custom_exporter"
            ) as mock_add:
                with patch("genkit.plugins.google_cloud.telemetry.tracing.metrics"):
                    with patch(
                        "genkit.plugins.google_cloud.telemetry.tracing.CloudMonitoringMetricsExporter"
                    ):
                        with patch(
                            "genkit.plugins.google_cloud.telemetry.tracing.GoogleCloudResourceDetector"
                        ):
                            add_gcp_telemetry(force_export=True)
                            mock_add.assert_called_once()

    def test_add_gcp_telemetry_in_prod_environment(self):
        """Test that telemetry is added in production environment."""
        from genkit.plugins.google_cloud.telemetry.tracing import add_gcp_telemetry

        with patch(
            "genkit.plugins.google_cloud.telemetry.tracing.is_dev_environment",
            return_value=False,
        ):
            with patch(
                "genkit.plugins.google_cloud.telemetry.tracing.add_custom_exporter"
            ) as mock_add:
                with patch("genkit.plugins.google_cloud.telemetry.tracing.metrics"):
                    with patch(
                        "genkit.plugins.google_cloud.telemetry.tracing.CloudMonitoringMetricsExporter"
                    ):
                        with patch(
                            "genkit.plugins.google_cloud.telemetry.tracing.GoogleCloudResourceDetector"
                        ):
                            add_gcp_telemetry()
                            mock_add.assert_called_once()

    def test_genkitgcp_exporter_export_success(self):
        """Test GenkitGCPExporter exports spans successfully."""
        from genkit.plugins.google_cloud.telemetry.tracing import GenkitGCPExporter
        from opentelemetry.sdk.trace.export import SpanExportResult

        with patch('genkit.plugins.google_cloud.telemetry.tracing.record_generate_metrics'):
            exporter = GenkitGCPExporter(project_id='test-project')

            # Mock the client
            exporter.client = MagicMock()
            exporter._translate_to_cloud_trace = MagicMock(return_value=[])

            span = Mock(spec=ReadableSpan)
            span.attributes = {}

            result = exporter.export([span])
            assert result == SpanExportResult.SUCCESS

    def test_genkitgcp_exporter_export_failure(self):
        """Test GenkitGCPExporter handles export failures."""
        from genkit.plugins.google_cloud.telemetry.tracing import GenkitGCPExporter
        from opentelemetry.sdk.trace.export import SpanExportResult

        with patch('genkit.plugins.google_cloud.telemetry.tracing.record_generate_metrics'):
            exporter = GenkitGCPExporter(project_id='test-project')

            # Mock the client to raise exception
            exporter.client = MagicMock()
            exporter.client.batch_write_spans.side_effect = Exception('Export failed')
            exporter._translate_to_cloud_trace = MagicMock(return_value=[])

            span = Mock(spec=ReadableSpan)
            span.attributes = {}

            result = exporter.export([span])
            assert result == SpanExportResult.FAILURE
