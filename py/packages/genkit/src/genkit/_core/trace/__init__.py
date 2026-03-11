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

"""Trace module for OpenTelemetry span management."""

import os

from ._adjusting_exporter import AdjustingTraceExporter, RedactedSpan
from ._default_exporter import (
    TraceServerExporter,
    create_span_processor,
    init_telemetry_server_exporter,
)
from ._path import (
    build_path,
    decorate_path_with_subtype,
    to_display_path,
)
from ._realtime_processor import RealtimeSpanProcessor


def is_realtime_telemetry_enabled() -> bool:
    """Return True if realtime telemetry (live span export) is enabled via env."""
    return os.environ.get('GENKIT_ENABLE_REALTIME_TELEMETRY', '').lower() == 'true'


__all__ = [
    'AdjustingTraceExporter',
    'RealtimeSpanProcessor',
    'RedactedSpan',
    'TraceServerExporter',
    'build_path',
    'create_span_processor',
    'decorate_path_with_subtype',
    'init_telemetry_server_exporter',
    'is_realtime_telemetry_enabled',
    'to_display_path',
]
