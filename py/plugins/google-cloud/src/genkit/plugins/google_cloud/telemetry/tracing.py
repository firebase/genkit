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
import os
from collections.abc import Sequence

import structlog
from google.cloud.trace_v2 import BatchWriteSpansRequest
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
)

from genkit.core.tracing import add_custom_exporter, init_provider

logger = structlog.getLogger(__name__)


class GenkitGCPExporter(CloudTraceSpanExporter):
    """Exports spans to a GCP telemetry server.

    This exporter sends span data in a specific format to a GCP telemetry server,
    for visualization and debugging.

    Attributes:
        project_id: GCP project ID for the project to send spans to. Alternatively, can be
            configured with :envvar:`OTEL_EXPORTER_GCP_TRACE_PROJECT_ID`.
        client: Cloud Trace client. If not given, will be taken from gcloud
            default credentials
        resource_regex: Resource attributes with keys matching this regex will be added to
            exported spans as labels (default: None). Alternatively, can be configured with
            :envvar:`OTEL_EXPORTER_GCP_TRACE_RESOURCE_REGEX`.
    """

    def __init__(
        self,
        project_id=None,
        client=None,
        resource_regex=None,
    ):
        """Initializes the GenkitGCPExporter.

        Args:
            project_id: GCP project ID for the project to send spans to. Alternatively, can be
                configured with :envvar:`OTEL_EXPORTER_GCP_TRACE_PROJECT_ID`.
            client: Cloud Trace client. If not given, will be taken from gcloud
                default credentials
            resource_regex: Resource attributes with keys matching this regex will be added to
                exported spans as labels (default: None). Alternatively, can be configured with
                :envvar:`OTEL_EXPORTER_GCP_TRACE_RESOURCE_REGEX`.
        """
        super().__init__(
            project_id=project_id,
            client=client,
            resource_regex=resource_regex,
        )

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
                    name=f"projects/{self.project_id}",
                    spans=self._translate_to_cloud_trace(spans),
                )
            )
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error("Error while writing to Cloud Trace", exc_info=ex)
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS

    def add_tracer_attributes(
        self, spans: Sequence[ReadableSpan]
    ) -> Sequence[ReadableSpan]:
        """Adds the instrumentation library attribute.

        Args:
            spans: Sequence of spans to modify.

        Returns:
            Sequence of spans modified.
        """
        modified_spans: list[ReadableSpan] = []

        for span in spans:
            modified_spans.append(
                span.attributes.update(
                    {
                        'instrumentationLibrary': {
                            'name': 'genkit-tracer',
                            'version': 'v1',
                        },
                    }
                )
            )

        return modified_spans


def init_telemetry_gcp_exporter() -> (SpanExporter | None):
    """Initializes tracing with a provider and optional exporter."""
    telemetry_project_id = os.environ.get('GCP_PROJECT_ID')  # TODO: set correct envvar
    processor = None
    if telemetry_project_id:
        processor = GenkitGCPExporter(
            project_id=telemetry_project_id,
        )
    else:
        logger.warn(
            'GCP_PROJECT_ID is not set.'  # TODO: Get a better explanation of the error
        )

    return processor


def add_gcp_telemetry():
    """Inits and adds GCP telemetry exporter."""
    add_custom_exporter(
        init_telemetry_gcp_exporter(),
        "gcp_telemetry_server"
    )
