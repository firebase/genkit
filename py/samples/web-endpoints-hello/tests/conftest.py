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

"""Pytest configuration for web-endpoints-hello tests.

Handles two concerns:
1. Path setup — adds the sample root to sys.path so ``from src.app_init
   import ...`` works regardless of where pytest is invoked.
2. OpenTelemetry — sets up a TracerProvider with an InMemorySpanExporter
   *before* any test module imports. OTel only allows setting the global
   provider once per process, so this must happen here in conftest.
"""

import sys
from pathlib import Path

# Add the sample root (web-endpoints-hello/) to sys.path so tests can
# import ``src.*`` whether pytest runs from py/ or from the sample dir.
_SAMPLE_ROOT = str(Path(__file__).resolve().parent.parent)
if _SAMPLE_ROOT not in sys.path:
    sys.path.insert(0, _SAMPLE_ROOT)

# Set up OpenTelemetry before any test module loads. This is necessary
# because trace.set_tracer_provider() can only be called once per process.
from opentelemetry import trace  # noqa: E402 — must import after env var setup above
from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # noqa: E402 — must import after env var setup above
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402 — must import after env var setup above
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402 — must import after env var setup above
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: E402 — must import after env var setup above
    InMemorySpanExporter,
)

otel_exporter = InMemorySpanExporter()
_resource = Resource(attributes={SERVICE_NAME: "test-service"})
_provider = TracerProvider(resource=_resource)
_provider.add_span_processor(SimpleSpanProcessor(otel_exporter))
trace.set_tracer_provider(_provider)
