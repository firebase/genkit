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


"""Firebase Plugin for Genkit."""

from genkit.plugins.google_cloud.telemetry.tracing import add_gcp_telemetry


def package_name() -> str:
    """Get the package name for the Firebase plugin.

    Returns:
        Package name string.
    """
    return 'genkit.plugins.firebase'


def add_firebase_telemetry() -> None:
    """Add Firebase telemetry export to Google Cloud Observability.

    Exports traces to Cloud Trace and metrics to Cloud Monitoring.
    In development (GENKIT_ENV=dev), telemetry is disabled by default.
    """
    add_gcp_telemetry(force_export=False)


__all__ = ['package_name', 'add_firebase_telemetry']
