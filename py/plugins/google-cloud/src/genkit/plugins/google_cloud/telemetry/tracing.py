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
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import Any, cast

import structlog
from google.api_core import exceptions as core_exceptions, retry as retries
from google.cloud.trace_v2 import BatchWriteSpansRequest
from opentelemetry import metrics, trace
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.resourcedetector.gcp_resource_detector import (
    GoogleCloudResourceDetector,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
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
from genkit.core.trace.adjusting_exporter import AdjustingTraceExporter, RedactedSpan
from genkit.core.tracing import add_custom_exporter

from .action import action_telemetry
from .engagement import engagement_telemetry
from .feature import features_telemetry
from .generate import generate_telemetry
from .path import paths_telemetry

logger = structlog.get_logger(__name__)

# Constants matching JS/Go implementations
MIN_METRIC_EXPORT_INTERVAL_MS = 5000
DEFAULT_METRIC_EXPORT_INTERVAL_MS = 300000
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


class GcpTelemetry:
    """Central manager for GCP Telemetry configuration.

    Encapsulates configuration and manages the lifecycle of Tracing, Metrics,
    and Logging setup, ensuring consistent state (like project_id) across all
    telemetry components.
    """

    def __init__(
        self,
        project_id: str | None = None,
        credentials: dict[str, Any] | None = None,
        sampler: Sampler | None = None,
        log_input_and_output: bool = False,
        force_dev_export: bool = True,
        disable_metrics: bool = False,
        disable_traces: bool = False,
        metric_export_interval_ms: int | None = None,
        metric_export_timeout_ms: int | None = None,
    ) -> None:
        """Initialize the GCP Telemetry manager.

        Args:
            project_id: GCP project ID.
            credentials: Optional credentials dict.
            sampler: Trace sampler.
            log_input_and_output: If False, hides sensitive data.
            force_dev_export: Check to force export in dev environment.
            disable_metrics: If True, metrics are not exported.
            disable_traces: If True, traces are not exported.
            metric_export_interval_ms: Export interval in ms.
            metric_export_timeout_ms: Export timeout in ms.
        """
        self.credentials = credentials
        self.sampler = sampler
        self.log_input_and_output = log_input_and_output
        self.force_dev_export = force_dev_export
        self.disable_metrics = disable_metrics
        self.disable_traces = disable_traces

        # Resolve project ID immediately
        self.project_id = _resolve_project_id(project_id, credentials)

        # Determine metric export settings
        is_dev = is_dev_environment()

        default_interval = DEV_METRIC_EXPORT_INTERVAL_MS if is_dev else DEFAULT_METRIC_EXPORT_INTERVAL_MS
        self.metric_export_interval_ms = metric_export_interval_ms or default_interval

        if self.metric_export_interval_ms < MIN_METRIC_EXPORT_INTERVAL_MS:
            logger.warning(
                f'metric_export_interval_ms ({self.metric_export_interval_ms}) is below minimum '
                f'({MIN_METRIC_EXPORT_INTERVAL_MS}), using minimum'
            )
            self.metric_export_interval_ms = MIN_METRIC_EXPORT_INTERVAL_MS

        self.metric_export_timeout_ms = metric_export_timeout_ms or self.metric_export_interval_ms

    def initialize(self) -> None:
        """Actuates the telemetry configuration."""
        is_dev = is_dev_environment()
        should_export = self.force_dev_export or not is_dev

        if not should_export:
            logger.debug('Telemetry export disabled in dev environment')
            return

        self._configure_logging()
        self._configure_tracing()
        self._configure_metrics()

    def _configure_logging(self) -> None:
        """Configures structlog with trace correlation."""
        try:
            current_config = structlog.get_config()
            processors = current_config.get('processors', [])

            # Check if our bound method is already registered (by name or other heuristic if needed)
            # Since methods are bound, simple equality check might fail if new instance.
            # However, for simplicity and common usage, we'll append.
            # A better check would be to see if any processor matches our signature/name.

            # Simple deduplication: Check for function name in processors
            if not any(getattr(p, '__name__', '') == 'inject_trace_context' for p in processors):

                def inject_trace_context(
                    logger: Any,  # noqa: ANN401
                    method_name: str,
                    event_dict: MutableMapping[str, Any],
                ) -> Mapping[str, Any]:
                    return self._inject_trace_context(
                        cast(logging.Logger, logger), method_name, cast(dict[str, Any], event_dict)
                    )

                new_processors = list(processors)
                new_processors.insert(max(0, len(new_processors) - 1), inject_trace_context)
                structlog.configure(processors=new_processors)
                logger.debug('Configured structlog for GCP trace correlation')

        except Exception as e:
            logger.warning('Failed to configure structlog for trace correlation', error=str(e))

    def _configure_tracing(self) -> None:
        if self.disable_traces:
            return

        exporter_kwargs: dict[str, Any] = {}
        if self.project_id:
            exporter_kwargs['project_id'] = self.project_id
        if self.credentials:
            exporter_kwargs['credentials'] = self.credentials

        base_exporter = GenkitGCPExporter(**exporter_kwargs) if exporter_kwargs else GenkitGCPExporter()

        trace_exporter = GcpAdjustingTraceExporter(
            exporter=base_exporter,
            log_input_and_output=self.log_input_and_output,
            project_id=self.project_id,
            error_handler=lambda e: _handle_tracing_error(e),
        )

        add_custom_exporter(trace_exporter, 'gcp_telemetry_server')

    def _configure_metrics(self) -> None:
        if self.disable_metrics:
            return

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
                gcp_resource = GoogleCloudResourceDetector(raise_on_error=True).detect()
                resource = resource.merge(gcp_resource)
            except Exception as e:
                # For detection failure log the exception and use the default resource
                detector_logger.warning(f'Google Cloud resource detection failed: {e}')
            finally:
                detector_logger.setLevel(original_level)

            exporter_kwargs: dict[str, Any] = {}
            if self.project_id:
                exporter_kwargs['project_id'] = self.project_id
            if self.credentials:
                exporter_kwargs['credentials'] = self.credentials

            metrics_exporter = GenkitMetricExporter(
                exporter=CloudMonitoringMetricsExporter(**exporter_kwargs),
                error_handler=lambda e: _handle_metric_error(e),
            )

            reader = PeriodicExportingMetricReader(
                metrics_exporter,
                export_interval_millis=self.metric_export_interval_ms,
                export_timeout_millis=self.metric_export_timeout_ms,
            )

            provider = MeterProvider(metric_readers=[reader], resource=resource)
            metrics.set_meter_provider(provider)

        except Exception as e:
            _handle_metric_error(e)

    def _inject_trace_context(
        self, logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Structlog processor to inject GCP-compatible trace context."""
        span = trace.get_current_span()
        if span == trace.INVALID_SPAN:
            return event_dict

        ctx = span.get_span_context()
        if not ctx.is_valid:
            return event_dict

        if self.project_id:
            event_dict['logging.googleapis.com/trace'] = f'projects/{self.project_id}/traces/{ctx.trace_id:032x}'

        event_dict['logging.googleapis.com/spanId'] = f'{ctx.span_id:016x}'
        event_dict['logging.googleapis.com/trace_sampled'] = '1' if ctx.trace_flags.sampled else '0'

        return event_dict


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

        # Force DELTA temporality for all instrument types to match JS implementation.
        delta = AggregationTemporality.DELTA
        self._preferred_temporality = {
            Counter: delta,
            UpDownCounter: delta,
            Histogram: delta,
            ObservableCounter: delta,
            ObservableUpDownCounter: delta,
            ObservableGauge: delta,
        }

        self._preferred_aggregation = getattr(exporter, '_preferred_aggregation', None)

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
            **kwargs: Additional arguments for base class compatibility.

        Returns:
            The export result from the wrapped exporter.
        """
        # Modify start times before export
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
            metrics_data: The metrics data to modify in-place.
        """
        for resource_metrics in metrics_data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    for data_point in metric.data.data_points:
                        # Add 1 millisecond (1_000_000 nanoseconds) to start time
                        if hasattr(data_point, 'start_time_unix_nano'):
                            # Modifying frozen dataclass via workaround
                            object.__setattr__(
                                data_point,
                                'start_time_unix_nano',
                                data_point.start_time_unix_nano + 1_000_000,
                            )

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Delegate force flush to wrapped exporter.

        Args:
            timeout_millis: Timeout in milliseconds.

        Returns:
            True if flush succeeded.
        """
        if hasattr(self._exporter, 'force_flush'):
            return self._exporter.force_flush(timeout_millis)
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs: object) -> None:
        """Delegate shutdown to wrapped exporter.

        Args:
            timeout_millis: Timeout in milliseconds.
            **kwargs: Additional arguments for base class compatibility.
        """
        self._exporter.shutdown(timeout_millis, **kwargs)


class TimeAdjustedSpan(RedactedSpan):
    """Wraps a span to ensure non-zero duration for GCP.

    GCP Trace requires end_time > start_time.
    """

    @property
    def end_time(self) -> int | None:
        """Return the span end time, adjusted to be > start_time."""
        start = self._span.start_time
        end = self._span.end_time

        # GCP requires end_time > start_time.
        # If the span is unfinished (end_time is None) or has zero duration,
        # we provide a minimum 1 microsecond duration.
        if start is not None:
            if end is None or end <= start:
                return start + 1000

        return end


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
        self._log_input_and_output = log_input_and_output
        self._project_id = project_id

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
        span = super()._adjust(span)

        # Fix start/end times for GCP (must be end > start)
        return TimeAdjustedSpan(span, dict(span.attributes) if span.attributes else {})

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

    manager = GcpTelemetry(
        project_id=project_id,
        credentials=credentials,
        sampler=sampler,
        log_input_and_output=log_input_and_output,
        force_dev_export=force_dev_export,
        disable_metrics=disable_metrics,
        disable_traces=disable_traces,
        metric_export_interval_ms=metric_export_interval_ms,
        metric_export_timeout_ms=metric_export_timeout_ms,
    )

    manager.initialize()


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


def _handle_metric_error(error: Exception) -> None:
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
