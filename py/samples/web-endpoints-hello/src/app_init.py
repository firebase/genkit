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

"""Genkit instance creation and platform telemetry auto-detection.

This module creates the ``ai`` (Genkit) singleton shared across flows
and route handlers.  It is framework-agnostic — the ASGI app is created
later by the selected framework adapter (FastAPI or Litestar).

Importing this module triggers:

1. ``GEMINI_API_KEY`` prompt if not already in the environment.
2. Genkit initialization with the Google AI plugin.
3. Platform telemetry auto-detection (GCP, AWS, Azure, generic OTLP).
"""

import os

import structlog

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.google_genai.models.gemini import GoogleAIGeminiVersion

from .log_config import setup_logging

logger = structlog.get_logger(__name__)

setup_logging()

if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = input("Please enter your GEMINI_API_KEY: ")

ai = Genkit(
    plugins=[GoogleAI()],
    model=f"googleai/{GoogleAIGeminiVersion.GEMINI_3_FLASH_PREVIEW}",
)


# Auto-enable platform-specific telemetry unless explicitly disabled.
# Checks GENKIT_TELEMETRY_DISABLED env var; CLI --no-telemetry is applied later.
if os.environ.get("GENKIT_TELEMETRY_DISABLED", "").lower() not in ("1", "true", "yes"):
    _telemetry_enabled = False

    # GCP: Cloud Run sets K_SERVICE; GCE/GKE set
    # GOOGLE_CLOUD_PROJECT + GCE_METADATA_HOST.  GOOGLE_CLOUD_PROJECT alone
    # is not enough — it is commonly set on dev machines for gcloud CLI use
    # and does not imply the app is running on GCP infrastructure.
    _on_gcp = bool(
        os.environ.get("K_SERVICE")
        or os.environ.get("GCE_METADATA_HOST")
        or (os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get("GENKIT_TELEMETRY_GCP"))
    )
    if _on_gcp:
        try:
            from genkit.plugins.google_cloud import (
                add_gcp_telemetry,
            )

            add_gcp_telemetry()
            _telemetry_enabled = True
            logger.info(
                "GCP telemetry enabled (Cloud Trace + Monitoring)",
                service=os.environ.get("K_SERVICE", "unknown"),
            )
        except ImportError:
            logger.warning(
                "genkit-plugin-google-cloud not installed, skipping GCP telemetry. "
                "Install with: pip install genkit-plugin-google-cloud"
            )

    # AWS: ECS/App Runner set AWS_EXECUTION_ENV or ECS_CONTAINER_METADATA_URI.
    elif os.environ.get("AWS_EXECUTION_ENV") or os.environ.get("ECS_CONTAINER_METADATA_URI"):
        try:
            from genkit.plugins.amazon_bedrock import (
                add_aws_telemetry,
            )

            add_aws_telemetry()
            _telemetry_enabled = True
            logger.info(
                "AWS telemetry enabled (X-Ray)",
                env=os.environ.get("AWS_EXECUTION_ENV", "unknown"),
            )
        except ImportError:
            logger.warning(
                "genkit-plugin-amazon-bedrock not installed, skipping AWS telemetry. "
                "Install with: pip install genkit-plugin-amazon-bedrock"
            )

    # Azure: Container Apps set CONTAINER_APP_NAME; App Service sets WEBSITE_SITE_NAME.
    elif os.environ.get("CONTAINER_APP_NAME") or os.environ.get("WEBSITE_SITE_NAME"):
        try:
            from genkit.plugins.microsoft_foundry import (
                add_azure_telemetry,
            )

            add_azure_telemetry()
            _telemetry_enabled = True
            logger.info(
                "Azure telemetry enabled (Application Insights)",
                app=os.environ.get("CONTAINER_APP_NAME", os.environ.get("WEBSITE_SITE_NAME", "unknown")),
            )
        except ImportError:
            logger.warning(
                "genkit-plugin-microsoft-foundry not installed, skipping Azure telemetry. "
                "Install with: pip install genkit-plugin-microsoft-foundry"
            )

    # Generic OTLP: if OTEL_EXPORTER_OTLP_ENDPOINT is set, use the observability plugin.
    if not _telemetry_enabled and os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        try:
            from genkit.plugins.observability import (
                configure_telemetry,
            )

            configure_telemetry(backend="otlp")
            logger.info(
                "Generic OTLP telemetry enabled",
                endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
            )
        except ImportError:
            logger.warning(
                "genkit-plugin-observability not installed, skipping generic telemetry. "
                "Install with: pip install genkit-plugin-observability"
            )
else:
    logger.info("Telemetry disabled via GENKIT_TELEMETRY_DISABLED env var")
