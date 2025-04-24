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


"""Telemetry and tracing functionality for the Genkit framework.

This module provides functionality for collecting and exporting telemetry data
from Genkit operations. It uses OpenTelemetry for tracing and exports span
data to a telemetry GCP server for monitoring and debugging purposes.

The module includes:
    - A custom span exporter for sending trace data to a telemetry GCP server
"""

from collections.abc import Sequence

import structlog
from google.api_core import exceptions as core_exceptions, retry as retries
from google.cloud.trace_v2 import BatchWriteSpansRequest
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import (
    SpanExportResult,
)

from genkit.core.tracing import add_custom_exporter

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
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error('Error while writing to Cloud Trace', exc_info=ex)
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS

    def add_tracer_attributes(self, spans: Sequence[ReadableSpan]) -> Sequence[ReadableSpan]:
        """Adds the instrumentation library attribute.

        Args:
            spans: Sequence of spans to modify.

        Returns:
            Sequence of spans modified.
        """
        modified_spans: list[ReadableSpan] = []

        for span in spans:
            modified_spans.append(
                span.attributes.update({
                    'instrumentationLibrary': {
                        'name': 'genkit-tracer',
                        'version': 'v1',
                    },
                })
            )

        return modified_spans


def add_gcp_telemetry() -> None:
    """Inits and adds GCP telemetry exporter."""
    add_custom_exporter(GenkitGCPExporter(), 'gcp_telemetry_server')
