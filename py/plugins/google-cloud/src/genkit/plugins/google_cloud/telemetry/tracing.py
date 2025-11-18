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


"""GCP telemetry export for traces and metrics."""

import logging
import uuid
from collections.abc import Sequence

import structlog
from google.api_core import exceptions as core_exceptions, retry as retries
from google.cloud.trace_v2 import BatchWriteSpansRequest
from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.resourcedetector.gcp_resource_detector import (
    GoogleCloudResourceDetector,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from genkit.core.environment import is_dev_environment
from genkit.core.tracing import add_custom_exporter

from .metrics import record_generate_metrics

logger = structlog.get_logger(__name__)


class GenkitGCPExporter(CloudTraceSpanExporter):
    """Exports spans to a GCP telemetry server.

    This exporter sends span data in a specific format to a GCP telemetry server,
    for visualization and debugging.

    Super class will use google.auth.default() to get the project id.
    """

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export the spans to Cloud Trace.

        Iterates through the provided spans, and adds an attribute to the spans.

        Note:
            Leverages span transformation and formatting to opentelemetry-exporter-gcp-trace.
            See: https://cloud.google.com/python/docs/reference/cloudtrace/latest

        Args:
            spans: A sequence of OpenTelemetry ReadableSpan objects to export.

        Returns:
            SpanExportResult.SUCCESS upon successful processing (does not guarantee
            server-side success).
        """
        try:
            for span in spans:
                record_generate_metrics(span)

            self.client.batch_write_spans(
                request=BatchWriteSpansRequest(
                    name=f'projects/{self.project_id}',
                    spans=self._translate_to_cloud_trace(spans),
                ),
                retry=retries.Retry(
                    initial=0.1,
                    maximum=30.0,
                    multiplier=2,
                    predicate=retries.if_exception_type(
                        core_exceptions.DeadlineExceeded,
                    ),
                    deadline=120.0,
                ),
            )
        except Exception as ex:
            logger.error('Error while writing to Cloud Trace', exc_info=ex)
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS


def add_gcp_telemetry(force_export: bool = True) -> None:
    """Configure GCP telemetry export for traces and metrics.

    Args:
        force_export: Export regardless of environment. Defaults to True.
    """
    should_export = force_export or not is_dev_environment()
    if not should_export:
        return

    add_custom_exporter(GenkitGCPExporter(), 'gcp_telemetry_server')

    try:
        resource = Resource.create({
            SERVICE_NAME: 'genkit',
            SERVICE_INSTANCE_ID: str(uuid.uuid4()),
        })

        # Suppress detector warnings during GCP resource detection
        detector_logger = logging.getLogger('opentelemetry.resourcedetector.gcp_resource_detector')
        original_level = detector_logger.level
        detector_logger.setLevel(logging.ERROR)

        try:
            resource = resource.merge(GoogleCloudResourceDetector().detect())
        finally:
            detector_logger.setLevel(original_level)

        metric_reader = PeriodicExportingMetricReader(
            exporter=CloudMonitoringMetricsExporter(),
            export_interval_millis=60000,
        )
        metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader], resource=resource))
    except Exception as e:
        logger.error('Failed to configure metrics exporter', error=str(e))
