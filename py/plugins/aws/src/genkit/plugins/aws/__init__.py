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

"""AWS Plugin for Genkit.

This plugin provides AWS observability integration for Genkit,
enabling telemetry export to AWS X-Ray (distributed tracing) and
CloudWatch (metrics and logs).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ AWS X-Ray           │ Amazon's tool to see how requests flow through    │
    │                     │ your app. Like GPS tracking for your API calls.   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ CloudWatch          │ Amazon's monitoring dashboard. See graphs of      │
    │                     │ your app's health, errors, and performance.       │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Telemetry           │ Data about what your app is doing. Like a         │
    │                     │ fitness tracker but for your code.                │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Trace               │ The full journey of one request through your      │
    │                     │ system. All the steps it took.                    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Span                │ One step in a trace. "Called model" or            │
    │                     │ "Ran tool" - each is a separate span.             │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ SigV4               │ AWS's way of proving you're allowed to send       │
    │                     │ data. Like showing your ID at the door.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ OTLP                │ OpenTelemetry Protocol - standard format for      │
    │                     │ sending traces. Works with many cloud providers.  │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                HOW TRACES GET TO AWS X-RAY                              │
    │                                                                         │
    │    Your Genkit App                                                      │
    │    ai.generate(prompt="Hello!")                                         │
    │         │                                                               │
    │         │  (1) Spans created automatically for each action              │
    │         ▼                                                               │
    │    ┌─────────────────┐                                                  │
    │    │  OpenTelemetry  │   Records: flow started, model called,           │
    │    │  SDK            │   tool executed, response returned               │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (2) Spans adjusted (PII redacted, errors marked)         │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  AWS Exporter   │   Adds SigV4 signature (proves identity)         │
    │    │                 │   Formats for X-Ray requirements                 │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (3) HTTPS to xray.{region}.amazonaws.com                 │
    │             ▼                                                           │
    │    ════════════════════════════════════════════════════                 │
    │             │  Internet                                                 │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  AWS X-Ray      │   Trace visualization in AWS Console             │
    │    │  Console        │   See waterfall diagrams, errors, latency        │
    │    └─────────────────┘                                                  │
    └─────────────────────────────────────────────────────────────────────────┘

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           AWS Plugin                                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  └── add_aws_telemetry() - Enable X-Ray/CloudWatch export               │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  telemetry/__init__.py - Telemetry Module                               │
    │  └── Re-exports from submodules                                         │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  telemetry/tracing.py - Distributed Tracing                             │
    │  ├── AWS X-Ray OTLP exporter configuration                              │
    │  ├── SigV4 authentication for AWS endpoints                             │
    │  ├── AwsXRayIdGenerator for X-Ray-compatible trace IDs                  │
    │  └── OpenTelemetry integration                                          │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                     Telemetry Data Flow                                 │
    │                                                                         │
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐      │
    │  │ Genkit App   │───►│ OpenTelemetry│───►│ AWS Observability    │      │
    │  │ (actions,    │    │ SDK + ADOT   │    │ (X-Ray, CloudWatch)  │      │
    │  │  flows)      │    └──────────────┘    └──────────────────────┘      │
    │  └──────────────┘                                                       │
    │                                                                         │
    │  Authentication: AWS SigV4 via botocore credentials                     │
    │  Protocol: OTLP/HTTP to regional AWS endpoints                          │
    └─────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.plugins.aws import add_aws_telemetry

    # Enable telemetry export to AWS X-Ray
    add_aws_telemetry()

    # With explicit region
    add_aws_telemetry(region='us-west-2')

    # Traces are now exported to:
    # - AWS X-Ray (distributed tracing)
    # Future: CloudWatch (metrics, logs)
    ```

OTLP Endpoints (Collector-less Export):
    AWS X-Ray and CloudWatch support direct OTLP export without a collector:

    - Traces: https://xray.{region}.amazonaws.com/v1/traces
    - Logs: https://logs.{region}.amazonaws.com/v1/logs

    Both endpoints use AWS SigV4 authentication.

IAM Permissions Required:
    - Traces: AWSXrayWriteOnlyPolicy or xray:PutTraceSegments permission
    - Logs: logs:PutLogEvents, logs:DescribeLogGroups, logs:DescribeLogStreams

Caveats:
    - Requires AWS credentials (environment variables, IAM role, or explicit)
    - Telemetry is disabled by default in development mode (GENKIT_ENV=dev)
    - Region must be configured via AWS_REGION environment variable or explicitly

See Also:
    - AWS X-Ray: https://docs.aws.amazon.com/xray/
    - CloudWatch: https://docs.aws.amazon.com/cloudwatch/
    - ADOT Python: https://aws-otel.github.io/docs/getting-started/python-sdk
    - Genkit documentation: https://genkit.dev/
"""

from .telemetry import add_aws_telemetry


def package_name() -> str:
    """Get the package name for the AWS plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.aws'


__all__ = ['package_name', 'add_aws_telemetry']
