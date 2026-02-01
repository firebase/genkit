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


"""Telemetry and tracing functionality for the Genkit Google Cloud plugin.

This module provides functionality for collecting and exporting telemetry data
from Genkit operations to Google Cloud. It uses OpenTelemetry for tracing and
exports span data to Google Cloud Trace for monitoring and debugging purposes.

Architecture Overview:
    The telemetry system follows a pipeline architecture that processes spans
    (traces) and metrics before exporting them to Google Cloud:

    ```
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         TELEMETRY DATA FLOW                             │
    │                                                                         │
    │  Genkit Actions (flows, models, tools)                                  │
    │         │                                                               │
    │         ▼                                                               │
    │  ┌─────────────────┐                                                    │
    │  │ OpenTelemetry   │  Creates spans with genkit:* attributes            │
    │  │ Tracer          │  (type, name, input, output, state, path, etc.)    │
    │  └────────┬────────┘                                                    │
    │           │                                                             │
    │           ▼                                                             │
    │  ┌─────────────────────────────────────────────────────────────┐        │
    │  │           GcpAdjustingTraceExporter                         │        │
    │  │  ┌─────────────────────────────────────────────────────┐    │        │
    │  │  │ 1. _tick_telemetry()                                │    │        │
    │  │  │    - pathsTelemetry.tick()    → Error metrics/logs  │    │        │
    │  │  │    - featuresTelemetry.tick() → Feature metrics     │    │        │
    │  │  │    - generateTelemetry.tick() → Model metrics       │    │        │
    │  │  │    - actionTelemetry.tick()   → Action I/O logs     │    │        │
    │  │  │    - engagementTelemetry.tick() → Feedback metrics  │    │        │
    │  │  │    - Sets genkit:rootState for root spans           │    │        │
    │  │  └─────────────────────────────────────────────────────┘    │        │
    │  │  ┌─────────────────────────────────────────────────────┐    │        │
    │  │  │ 2. AdjustingTraceExporter._adjust()                 │    │        │
    │  │  │    - Redact genkit:input/output → "<redacted>"      │    │        │
    │  │  │    - Mark error spans with /http/status_code: 599   │    │        │
    │  │  │    - Mark failed spans with genkit:failedSpan       │    │        │
    │  │  │    - Mark root spans with genkit:feature            │    │        │
    │  │  │    - Mark model spans with genkit:model             │    │        │
    │  │  │    - Normalize labels (: → /) for GCP compatibility │    │        │
    │  │  └─────────────────────────────────────────────────────┘    │        │
    │  └────────────────────────┬────────────────────────────────────┘        │
    │                           │                                             │
    │           ┌───────────────┴───────────────┐                             │
    │           ▼                               ▼                             │
    │  ┌─────────────────┐             ┌─────────────────┐                    │
    │  │ GenkitGCPExporter│             │ Cloud Logging   │                    │
    │  │ (Cloud Trace)   │             │ (via structlog) │                    │
    │  └────────┬────────┘             └─────────────────┘                    │
    │           │                                                             │
    │           ▼                                                             │
    │  ┌─────────────────┐                                                    │
    │  │ Google Cloud    │                                                    │
    │  │ Trace API       │                                                    │
    │  └─────────────────┘                                                    │
    │                                                                         │
    │  ─────────────────────── METRICS PIPELINE ────────────────────────      │
    │                                                                         │
    │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
    │  │ OpenTelemetry   │───▶│ GenkitMetric    │───▶│ Cloud Monitoring│      │
    │  │ Meter           │    │ Exporter        │    │ API             │      │
    │  │ (counters,      │    │ (adjusts start  │    │                 │      │
    │  │  histograms)    │    │  times for      │    │                 │      │
    │  └─────────────────┘    │  DELTA→CUMUL.)  │    └─────────────────┘      │
    │                         └─────────────────┘                             │
    └─────────────────────────────────────────────────────────────────────────┘
    ```

Key Components:
    1. **GcpAdjustingTraceExporter**: Extends AdjustingTraceExporter to add
       GCP-specific telemetry recording before spans are adjusted and exported.

    2. **AdjustingTraceExporter** (from genkit.core.trace): Base class that
       handles PII redaction, error marking, and label normalization.

    3. **GenkitGCPExporter**: Extends CloudTraceSpanExporter with retry logic
       for reliable delivery to Google Cloud Trace.

    4. **GenkitMetricExporter**: Wraps CloudMonitoringMetricsExporter and
       adjusts start times to prevent overlap when GCP converts DELTA to
       CUMULATIVE aggregation.

    5. **Telemetry Handlers** (in separate modules):
       - feature.py: Tracks root span requests/latency
       - path.py: Tracks error paths and failure metrics
       - generate.py: Tracks model usage (tokens, latency, media)
       - action.py: Logs tool and action I/O
       - engagement.py: Tracks user feedback and acceptance

Telemetry Types and When They Fire:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Telemetry Type │ Condition                    │ What It Records         │
    ├────────────────┼──────────────────────────────┼─────────────────────────┤
    │ paths          │ Always (for all spans)       │ Error paths, failures   │
    │ features       │ genkit:isRoot = true         │ Request count, latency  │
    │ generate       │ type=action, subtype=model   │ Tokens, latency, media  │
    │ action         │ type in (action,flow,...)    │ Input/output logs       │
    │ engagement     │ type=userEngagement          │ Feedback, acceptance    │
    └────────────────┴──────────────────────────────┴─────────────────────────┘

Span Attributes Used:
    The system reads these genkit:* attributes from spans:
    - genkit:type - Span type (action, flow, flowStep, util, userEngagement)
    - genkit:metadata:subtype - Subtype (model, tool, etc.)
    - genkit:isRoot - Whether this is the root/entry span
    - genkit:name - Action/flow name
    - genkit:path - Hierarchical path like /{flow,t:flow}/{step,t:flowStep}
    - genkit:input - JSON-encoded input data
    - genkit:output - JSON-encoded output data
    - genkit:state - Span state (success, error)
    - genkit:isFailureSource - Whether this span is the source of a failure

Configuration Options (matching JS/Go parity):
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Option                      │ Type     │ Default    │ Description       │
    ├─────────────────────────────┼──────────┼────────────┼───────────────────┤
    │ project_id                  │ str      │ Auto       │ GCP project ID    │
    │ credentials                 │ dict     │ ADC        │ Service account   │
    │ log_input_and_output        │ bool     │ False      │ Disable redaction │
    │ force_dev_export            │ bool     │ True       │ Export in dev     │
    │ disable_metrics             │ bool     │ False      │ Skip metrics      │
    │ disable_traces              │ bool     │ False      │ Skip traces       │
    │ metric_export_interval_ms   │ int      │ 60000      │ Export interval   │
    │ metric_export_timeout_ms    │ int      │ None       │ Export timeout    │
    │ sampler                     │ Sampler  │ AlwaysOn   │ Trace sampler     │
    └─────────────────────────────┴──────────┴────────────┴───────────────────┘

Project ID Resolution Order:
    1. Explicit project_id parameter
    2. FIREBASE_PROJECT_ID environment variable
    3. GOOGLE_CLOUD_PROJECT environment variable
    4. GCLOUD_PROJECT environment variable
    5. project_id from credentials dict

Usage:
    ```python
    from genkit.plugins.google_cloud import add_gcp_telemetry

    # Enable telemetry with default settings (PII redaction enabled)
    add_gcp_telemetry()

    # Enable telemetry with input/output logging (disable PII redaction)
    add_gcp_telemetry(log_input_and_output=True)

    # Force export even in dev environment
    add_gcp_telemetry(force_dev_export=True)

    # Disable metrics but keep traces
    add_gcp_telemetry(disable_metrics=True)

    # Custom metric export interval (minimum 5000ms for GCP)
    add_gcp_telemetry(metric_export_interval_ms=30000)
    ```

Caveats:
    - By default, model inputs and outputs are redacted for privacy
    - Set log_input_and_output=True only in trusted environments
    - In dev environment, telemetry is skipped unless force_dev_export=True
    - GCP requires minimum 5000ms metric export interval (see quotas link below)

GCP Documentation References:
    Cloud Trace:
        - Overview: https://cloud.google.com/trace/docs
        - IAM Roles: https://cloud.google.com/trace/docs/iam
        - Required role: roles/cloudtrace.agent (Cloud Trace Agent)

    Cloud Monitoring:
        - Overview: https://cloud.google.com/monitoring/docs
        - Quotas & Limits: https://cloud.google.com/monitoring/quotas
        - Required role: roles/monitoring.metricWriter (Monitoring Metric Writer)
          or roles/telemetry.metricsWriter (Cloud Telemetry Metrics Writer)

    OpenTelemetry GCP Exporters:
        - Documentation: https://google-cloud-opentelemetry.readthedocs.io/
        - Cloud Trace Exporter: https://google-cloud-opentelemetry.readthedocs.io/en/stable/cloud_trace/cloud_trace.html
        - Cloud Monitoring Exporter: https://google-cloud-opentelemetry.readthedocs.io/en/stable/cloud_monitoring/cloud_monitoring.html

Cross-Language Parity:
    This implementation maintains parity with:
    - JavaScript: js/plugins/google-cloud/src/gcpOpenTelemetry.ts
    - Go: go/plugins/googlecloud/googlecloud.go
    - Go: go/plugins/firebase/telemetry.go (FirebaseTelemetryOptions)

    Key parity points:
    - Same configuration options with equivalent semantics
    - Same telemetry dispatch logic (when each handler fires)
    - Same metrics names and dimensions
    - Same span adjustment pipeline (redaction, marking, normalization)
    - Same project ID resolution order
"""

import logging
import os
import uuid
from collections.abc import Callable, Sequence
from typing import Any

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
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    MetricsData,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import Sampler

from genkit.core.environment import is_dev_environment
from genkit.core.trace import AdjustingTraceExporter
from genkit.core.tracing import add_custom_exporter

from .action import action_telemetry
from .engagement import engagement_telemetry
from .feature import features_telemetry
from .generate import generate_telemetry
from .path import paths_telemetry

logger = structlog.get_logger(__name__)

# Constants matching JS/Go implementations
MIN_METRIC_EXPORT_INTERVAL_MS = 5000
DEFAULT_METRIC_EXPORT_INTERVAL_MS = 60000
DEV_METRIC_EXPORT_INTERVAL_MS = 5000
PROD_METRIC_EXPORT_INTERVAL_MS = 300000


def _resolve_project_id(
    project_id: str | None = None,
    credentials: dict[str, Any] | None = None,
) -> str | None:
    """Resolve the GCP project ID from various sources.

    Resolution order (matching JS/Go):
    1. Explicit project_id parameter
    2. FIREBASE_PROJECT_ID environment variable
    3. GOOGLE_CLOUD_PROJECT environment variable
    4. GCLOUD_PROJECT environment variable
    5. Project ID from credentials

    Args:
        project_id: Explicitly provided project ID.
        credentials: Optional credentials dict with project_id.

    Returns:
        The resolved project ID or None.
    """
    if project_id:
        return project_id

    # Check environment variables in order of priority
    for env_var in ('FIREBASE_PROJECT_ID', 'GOOGLE_CLOUD_PROJECT', 'GCLOUD_PROJECT'):
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value

    # Check credentials for project_id
    if credentials and 'project_id' in credentials:
        return credentials['project_id']

    return None


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
        except Exception as ex:
            logger.error('Error while writing to Cloud Trace', exc_info=ex)
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS


class GenkitMetricExporter(MetricExporter):
    """Metric exporter wrapper that adjusts start times for GCP compatibility.

    Cloud Monitoring does not support delta metrics for custom metrics and will
    convert any DELTA aggregations to CUMULATIVE ones on export. There is implicit
    overlap in the start/end times that the Metric reader sends -- the end_time
    of the previous export becomes the start_time of the current export.

    This wrapper adds a microsecond to start times to ensure discrete export
    timeframes and prevent data being overwritten.

    This matches the JavaScript MetricExporterWrapper in gcpOpenTelemetry.ts.

    Args:
        exporter: The underlying CloudMonitoringMetricsExporter.
        error_handler: Optional callback for export errors.
    """

    def __init__(
        self,
        exporter: CloudMonitoringMetricsExporter,
        error_handler: Callable[[Exception], None] | None = None,
    ) -> None:
        """Initialize the metric exporter wrapper.

        Args:
            exporter: The underlying CloudMonitoringMetricsExporter.
            error_handler: Optional callback for export errors.
        """
        self._exporter = exporter
        self._error_handler = error_handler

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs: object,
    ) -> MetricExportResult:
        """Export metrics after adjusting start times.

        Modifies start times of each data point to ensure no overlap with
        previous exports when GCP converts DELTA to CUMULATIVE.

        Args:
            metrics_data: The metrics data to export.
            timeout_millis: Export timeout in milliseconds.
            **kwargs: Additional arguments (for base class compatibility).

        Returns:
            The export result.
        """
        self._modify_start_times(metrics_data)

        try:
            return self._exporter.export(metrics_data, timeout_millis, **kwargs)
        except Exception as e:
            if self._error_handler:
                self._error_handler(e)
            raise

    def _modify_start_times(self, metrics_data: MetricsData) -> None:
        """Add 1ms to start times to prevent overlap.

        Args:
            metrics_data: The metrics data to modify.
        """
        for resource_metrics in metrics_data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    for data_point in metric.data.data_points:
                        # Add 1 millisecond (1_000_000 nanoseconds) to start time
                        if hasattr(data_point, 'start_time_unix_nano'):
                            # pyrefly: ignore[read-only] - modifying frozen dataclass via workaround
                            object.__setattr__(
                                data_point,
                                'start_time_unix_nano',
                                data_point.start_time_unix_nano + 1_000_000,
                            )

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Force flush the underlying exporter.

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if flush succeeded.
        """
        if hasattr(self._exporter, 'force_flush'):
            return self._exporter.force_flush(timeout_millis)
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs: object) -> None:
        """Shut down the underlying exporter.

        Args:
            timeout_millis: Timeout in milliseconds.
            **kwargs: Additional arguments (for base class compatibility).
        """
        self._exporter.shutdown(timeout_millis, **kwargs)


class GcpAdjustingTraceExporter(AdjustingTraceExporter):
    """GCP-specific span exporter that adds telemetry recording.

    This extends the base AdjustingTraceExporter to add GCP-specific telemetry
    recording (metrics and logs) for each span, matching the JavaScript
    implementation in gcpOpenTelemetry.ts.

    The telemetry handlers record:
    - Feature metrics (requests, latency) for root spans
    - Path metrics for failure tracking
    - Generate metrics (tokens, latency) for model actions
    - Action logs for tools and generate
    - Engagement metrics for user feedback

    Example:
        ```python
        exporter = GcpAdjustingTraceExporter(
            exporter=GenkitGCPExporter(),
            log_input_and_output=False,
            project_id='my-project',
        )
        ```
    """

    def __init__(
        self,
        exporter: SpanExporter,
        log_input_and_output: bool = False,
        project_id: str | None = None,
        error_handler: Callable[[Exception], None] | None = None,
    ) -> None:
        """Initialize the GCP adjusting trace exporter.

        Args:
            exporter: The underlying SpanExporter to wrap.
            log_input_and_output: If True, preserve input/output in spans and logs.
                Defaults to False (redact for privacy).
            project_id: Optional GCP project ID for log correlation.
            error_handler: Optional callback invoked when export errors occur.
        """
        super().__init__(
            exporter=exporter,
            log_input_and_output=log_input_and_output,
            project_id=project_id,
            error_handler=error_handler,
        )

    def _adjust(self, span: ReadableSpan) -> ReadableSpan:
        """Apply all adjustments to a span including telemetry.

        This overrides the base method to add telemetry recording before
        the standard adjustments (redaction, marking, normalization).

        Args:
            span: The span to adjust.

        Returns:
            The adjusted span.
        """
        # Record telemetry before adjustments (uses original attributes)
        span = self._tick_telemetry(span)

        # Apply standard adjustments from base class
        return super()._adjust(span)

    def _tick_telemetry(self, span: ReadableSpan) -> ReadableSpan:
        """Record telemetry for a span and apply root state marking.

        This matches the JavaScript tickTelemetry method in gcpOpenTelemetry.ts.
        It calls the appropriate telemetry handlers based on span type.

        Args:
            span: The span to record telemetry for.

        Returns:
            The span, potentially with genkit:rootState added for root spans.
        """
        attrs = span.attributes or {}
        if 'genkit:type' not in attrs:
            return span

        span_type = str(attrs.get('genkit:type', ''))
        subtype = str(attrs.get('genkit:metadata:subtype', ''))
        is_root = bool(attrs.get('genkit:isRoot'))

        try:
            # Always record path telemetry for error tracking
            paths_telemetry.tick(span, self._log_input_and_output, self._project_id)

            if is_root:
                # Report top level feature request and latency only for root spans
                features_telemetry.tick(span, self._log_input_and_output, self._project_id)

                # Set root state explicitly
                # (matches JS: span.attributes['genkit:rootState'] = span.attributes['genkit:state'])
                state = attrs.get('genkit:state')
                if state:
                    # Import here to avoid circular imports
                    from genkit.core.trace.adjusting_exporter import RedactedSpan  # noqa: PLC0415

                    new_attrs = dict(attrs)
                    new_attrs['genkit:rootState'] = state
                    span = RedactedSpan(span, new_attrs)
            else:
                if span_type == 'action' and subtype == 'model':
                    # Report generate metrics for all model actions
                    generate_telemetry.tick(span, self._log_input_and_output, self._project_id)

                if span_type == 'action' and subtype == 'tool':
                    # TODO(#4359): Report input and output for tool actions (matching JS comment)
                    pass

                if span_type in ('action', 'flow', 'flowStep', 'util'):
                    # Report request and latency metrics for all actions
                    action_telemetry.tick(span, self._log_input_and_output, self._project_id)

            if span_type == 'userEngagement':
                # Report user acceptance and feedback metrics
                engagement_telemetry.tick(span, self._log_input_and_output, self._project_id)

        except Exception as e:
            logger.warning('Error recording telemetry', error=str(e))

        return span


def add_gcp_telemetry(
    project_id: str | None = None,
    credentials: dict[str, Any] | None = None,
    sampler: Sampler | None = None,
    log_input_and_output: bool = False,
    force_dev_export: bool = True,
    disable_metrics: bool = False,
    disable_traces: bool = False,
    metric_export_interval_ms: int | None = None,
    metric_export_timeout_ms: int | None = None,
    # Legacy parameter name for backwards compatibility
    force_export: bool | None = None,
) -> None:
    """Configure GCP telemetry export for traces and metrics.

    This function sets up OpenTelemetry export to Google Cloud Trace and
    Cloud Monitoring. By default, model inputs and outputs are redacted
    for privacy protection.

    Configuration options match the JavaScript (GcpTelemetryConfigOptions) and
    Go (FirebaseTelemetryOptions/GoogleCloudTelemetryOptions) implementations.

    Args:
        project_id: Google Cloud project ID. If provided, takes precedence over
            environment variables and credentials. Required when using external
            credentials (e.g., Workload Identity Federation).
        credentials: Service account credentials dict for authenticating with
            Google Cloud. Primarily for use outside of GCP. On GCP, credentials
            are typically inferred via Application Default Credentials (ADC).
        sampler: OpenTelemetry trace sampler. Controls which traces are collected
            and exported. Defaults to AlwaysOnSampler. Common options:
            - AlwaysOnSampler: Collect all traces
            - AlwaysOffSampler: Collect no traces
            - TraceIdRatioBasedSampler: Sample a percentage of traces
        log_input_and_output: If True, preserve model input/output in traces
            and logs. Defaults to False (redact for privacy). Only enable this
            in trusted environments where PII exposure is acceptable.
            Maps to JS: !disableLoggingInputAndOutput
        force_dev_export: If True, export telemetry even in dev environment.
            Defaults to True. Set to False for production-only telemetry.
            Maps to JS: forceDevExport
        disable_metrics: If True, metrics will not be exported. Traces and
            logs may still be exported. Defaults to False.
            Maps to JS/Go: disableMetrics
        disable_traces: If True, traces will not be exported. Metrics and
            logs may still be exported. Defaults to False.
            Maps to JS/Go: disableTraces
        metric_export_interval_ms: Metrics export interval in milliseconds.
            GCP requires a minimum of 5000ms. Defaults to 60000ms.
            Dev environment uses 5000ms, production uses 300000ms by default
            in JS/Go (but we use 60000ms for consistent behavior).
            Maps to JS/Go: metricExportIntervalMillis
        metric_export_timeout_ms: Timeout for metrics export in milliseconds.
            Defaults to the export interval if not specified.
            Maps to JS/Go: metricExportTimeoutMillis
        force_export: Deprecated. Use force_dev_export instead.

    Example:
        ```python
        # Default: PII redaction enabled
        add_gcp_telemetry()

        # Enable input/output logging (disable PII redaction)
        add_gcp_telemetry(log_input_and_output=True)

        # Force export in dev environment with specific project
        add_gcp_telemetry(force_dev_export=True, project_id='my-project')

        # Disable metrics but keep traces
        add_gcp_telemetry(disable_metrics=True)

        # Custom metric export interval (minimum 5000ms)
        add_gcp_telemetry(metric_export_interval_ms=30000)

        # With custom credentials for non-GCP environments
        add_gcp_telemetry(
            project_id='my-project',
            credentials={'type': 'service_account', ...},
        )
        ```

    Note:
        This matches the JavaScript implementation's GcpTelemetryConfigOptions
        and Go's FirebaseTelemetryOptions/GoogleCloudTelemetryOptions.

    See Also:
        - JS: js/plugins/google-cloud/src/types.ts (GcpTelemetryConfigOptions)
        - Go: go/plugins/firebase/telemetry.go (FirebaseTelemetryOptions)
        - Go: go/plugins/googlecloud/types.go (GoogleCloudTelemetryOptions)
    """
    # Handle legacy force_export parameter
    if force_export is not None:
        logger.warning('force_export is deprecated, use force_dev_export instead')
        force_dev_export = force_export

    # Resolve project ID from various sources
    resolved_project_id = _resolve_project_id(project_id, credentials)

    # Determine if we should export based on environment
    is_dev = is_dev_environment()
    should_export = force_dev_export or not is_dev

    if not should_export:
        logger.debug('Telemetry export disabled in dev environment')
        return

    # Determine metric export interval
    if metric_export_interval_ms is None:
        metric_export_interval_ms = DEV_METRIC_EXPORT_INTERVAL_MS if is_dev else DEFAULT_METRIC_EXPORT_INTERVAL_MS

    # Ensure minimum interval for GCP
    if metric_export_interval_ms < MIN_METRIC_EXPORT_INTERVAL_MS:
        logger.warning(
            f'metric_export_interval_ms ({metric_export_interval_ms}) is below minimum '
            f'({MIN_METRIC_EXPORT_INTERVAL_MS}), using minimum'
        )
        metric_export_interval_ms = MIN_METRIC_EXPORT_INTERVAL_MS

    # Default timeout to interval if not specified
    if metric_export_timeout_ms is None:
        metric_export_timeout_ms = metric_export_interval_ms

    # Configure trace export
    if not disable_traces:
        # Create the base GCP exporter with optional credentials
        exporter_kwargs: dict[str, Any] = {}
        if resolved_project_id:
            exporter_kwargs['project_id'] = resolved_project_id
        if credentials:
            exporter_kwargs['credentials'] = credentials

        base_exporter = GenkitGCPExporter(**exporter_kwargs) if exporter_kwargs else GenkitGCPExporter()

        # Wrap with GcpAdjustingTraceExporter for PII redaction and telemetry
        # This matches the JS implementation in gcpOpenTelemetry.ts
        trace_exporter = GcpAdjustingTraceExporter(
            exporter=base_exporter,
            log_input_and_output=log_input_and_output,
            project_id=resolved_project_id,
            error_handler=lambda e: _handle_tracing_error(e),
        )

        add_custom_exporter(trace_exporter, 'gcp_telemetry_server')

    # Configure metrics export
    if not disable_metrics:
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

            # Create the base metric exporter
            base_metric_exporter = CloudMonitoringMetricsExporter(
                project_id=resolved_project_id,
            )

            # Wrap with our exporter that adjusts start times
            metric_exporter = GenkitMetricExporter(
                exporter=base_metric_exporter,
                error_handler=lambda e: _handle_metrics_error(e),
            )

            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=metric_export_interval_ms,
                export_timeout_millis=metric_export_timeout_ms,
            )
            metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader], resource=resource))
        except Exception as e:
            logger.error('Failed to configure metrics exporter', error=str(e))


# Error handling helpers (matches JS getErrorHandler pattern)
_tracing_error_logged = False
_metrics_error_logged = False


def _handle_tracing_error(error: Exception) -> None:
    """Handle trace export errors with helpful messages.

    Only logs detailed instructions once to avoid spam.

    Args:
        error: The export error.
    """
    global _tracing_error_logged
    if _tracing_error_logged:
        return

    error_str = str(error).lower()
    if 'permission' in error_str or 'denied' in error_str or '403' in error_str:
        _tracing_error_logged = True
        logger.error(
            'Unable to send traces to Google Cloud. '
            'Ensure the service account has the "Cloud Trace Agent" (roles/cloudtrace.agent) role. '
            f'Error: {error}'
        )
    else:
        logger.error('Error exporting traces to GCP', error=str(error))


def _handle_metrics_error(error: Exception) -> None:
    """Handle metrics export errors with helpful messages.

    Only logs detailed instructions once to avoid spam.

    Args:
        error: The export error.
    """
    global _metrics_error_logged
    if _metrics_error_logged:
        return

    error_str = str(error).lower()
    if 'permission' in error_str or 'denied' in error_str or '403' in error_str:
        _metrics_error_logged = True
        logger.error(
            'Unable to send metrics to Google Cloud. '
            'Ensure the service account has the "Monitoring Metric Writer" '
            '(roles/monitoring.metricWriter) or "Cloud Telemetry Metrics Writer" '
            '(roles/telemetry.metricsWriter) role. '
            f'Error: {error}'
        )
    else:
        logger.error('Error exporting metrics to GCP', error=str(error))
