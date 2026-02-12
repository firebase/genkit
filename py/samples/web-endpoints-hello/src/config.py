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

"""Application settings and CLI argument parsing.

Configuration is loaded with the following priority (highest wins):

1. CLI arguments       (``--port``, ``--server``, ``--framework``)
2. Environment variables  (``export GEMINI_API_KEY=...``)
3. ``.<env>.env`` file    (e.g. ``.staging.env``)
4. ``.env`` file          (shared defaults)
5. Defaults defined in :class:`Settings`

This means ``GEMINI_API_KEY`` can come from:

- ``export GEMINI_API_KEY=...``             (shell / CI)
- ``.env`` or ``.local.env``                (local dev)
- Docker ``-e`` / Cloud Run env vars        (deployed)
- Platform secrets manager                  (production)
"""

import argparse
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_env_files(env: str | None) -> tuple[str, ...]:
    """Build the list of .env files to load, most specific last.

    pydantic-settings loads files left-to-right, with later files
    overriding earlier ones. We always load ``.env`` as shared defaults,
    then layer the environment-specific file on top (e.g. ``.local.env``).

    The ``.<name>.env`` convention keeps all env files with the ``.env``
    extension, so they sort together in file listings, get syntax
    highlighting, and are auto-gitignored by ``**/*.env``.
    """
    files: list[str] = [".env"]
    if env:
        files.append(f".{env}.env")
    return tuple(files)


class Settings(BaseSettings):
    """Application settings loaded from env vars and .env files.

    Fields are read from environment variables and/or ``.env`` files.
    The ``model_config`` is set dynamically by ``make_settings()``.
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Secure-by-default philosophy ─────────────────────────────────
    #
    # Every default below is chosen so that a fresh deployment with NO
    # configuration is locked down.  Development convenience (Swagger UI,
    # colored logs, open CORS, gRPC reflection) requires *explicit*
    # opt-in via --debug, DEBUG=true, or the local.env.example overrides.
    #
    # If you add a new setting, ask: "If someone forgets to configure
    # this, should the system be open or closed?"  Choose closed.

    # Debug: off by default.  Enables Swagger UI, gRPC reflection, and
    # relaxed CSP.  Use --debug or DEBUG=true for local development.
    debug: bool = False

    gemini_api_key: str = ""
    port: int = 8080
    grpc_port: int = 50051
    server: Literal["granian", "uvicorn", "hypercorn"] = "uvicorn"
    framework: Literal["fastapi", "litestar", "quart"] = "fastapi"
    log_level: str = "info"
    telemetry_disabled: bool = False

    # OpenTelemetry collector config — set via env vars or CLI.
    # OTEL_EXPORTER_OTLP_ENDPOINT takes standard OTel precedence.
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_protocol: Literal["grpc", "http/protobuf"] = "http/protobuf"
    otel_service_name: str = "genkit-endpoints-hello"

    # Graceful shutdown: 10s matches Cloud Run's default SIGTERM window.
    shutdown_grace: float = 10.0

    # Log format: "json" is the safe production default (structured,
    # machine-parseable, no ANSI escape codes).  Override to "console"
    # in local.env for human-friendly colored output during development.
    log_format: str = "json"

    # Response cache for idempotent flows.
    cache_enabled: bool = True
    cache_ttl: int = 300
    cache_max_size: int = 1024

    # Circuit breaker for LLM API calls.
    cb_enabled: bool = True
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 30.0

    # Connection tuning.
    llm_timeout: int = 120_000
    # Keep-alive: 75s > typical load-balancer idle timeout (60s) to
    # prevent premature connection drops.
    keep_alive_timeout: int = 75
    # httpx outbound connection pool sizing.
    httpx_pool_max: int = 100
    httpx_pool_max_keepalive: int = 20

    # ── Security settings (secure-by-default) ────────────────────────
    #
    # CORS: empty = deny all cross-origin requests (same-origin only).
    # Override to "*" in local.env for browser dev tools, or set to a
    # comma-separated allowlist in production
    # (e.g. "https://app.example.com,https://admin.example.com").
    cors_allowed_origins: str = ""
    # CORS allowed methods (comma-separated).
    cors_allowed_methods: str = "GET,POST,OPTIONS"
    # CORS allowed headers (comma-separated).  Explicit allowlist is
    # safer than wildcard — limits the headers clients can send.
    cors_allowed_headers: str = "Content-Type,Authorization,X-Request-ID"
    # Trusted hosts: empty = disabled (no Host-header validation).
    # A warning is logged at startup in production (non-debug) mode.
    # Set to your domain(s) to reject host-header poisoning attacks
    # (e.g. "app.example.com,admin.example.com").
    trusted_hosts: str = ""
    # Rate limiting: applied per-client IP on both REST and gRPC.
    rate_limit_default: str = "60/minute"
    # Max request body: 1 MB.  Protects against memory exhaustion.
    # Applies to both REST (MaxBodySizeMiddleware) and gRPC
    # (grpc.max_receive_message_length).
    max_body_size: int = 1_048_576
    # Per-request timeout in seconds.  Prevents hung workers from
    # blocking the event loop indefinitely.  Should be ≥ LLM timeout.
    request_timeout: float = 120.0
    # HSTS max-age in seconds (1 year).  Only sent over HTTPS.
    # Set to 0 to disable HSTS entirely.
    hsts_max_age: int = 31_536_000
    # GZip compression minimum response size in bytes.  Responses
    # smaller than this are not compressed (overhead > savings).
    gzip_min_size: int = 500

    # Sentry — only active when SENTRY_DSN is set (safe default: off).
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    sentry_environment: str = ""


def make_settings(env: str | None = None) -> Settings:
    """Create Settings with the appropriate .env files for the environment."""
    env_files = _build_env_files(env)
    return Settings(_env_file=env_files)  # type: ignore[call-arg] — pydantic-settings accepts _env_file at runtime


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Configuration priority (highest wins)::

        1. CLI arguments      (--port, --server, --framework)
        2. Environment vars    (export GEMINI_API_KEY=...)
        3. .<env>.env file     (e.g. .staging.env via --env)
        4. .env file           (shared defaults)
        5. Settings defaults   (port=8080, server=uvicorn, framework=fastapi)
    """
    parser = argparse.ArgumentParser(
        description="Genkit + ASGI demo server (FastAPI, Litestar, or Quart)",
    )
    parser.add_argument(
        "--env",
        default=None,
        metavar="ENV",
        help="Environment name — loads .<ENV>.env on top of .env (e.g. --env staging loads .staging.env)",
    )
    parser.add_argument(
        "--framework",
        choices=["fastapi", "litestar", "quart"],
        default=None,
        help="ASGI framework (default from settings: fastapi)",
    )
    parser.add_argument(
        "--server",
        choices=["granian", "uvicorn", "hypercorn"],
        default=None,
        help="ASGI server override (default from settings: uvicorn)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port override (default from settings: $PORT or 8080)",
    )
    parser.add_argument(
        "--grpc-port",
        type=int,
        default=None,
        help="gRPC server port (default from settings: $GRPC_PORT or 50051)",
    )
    parser.add_argument(
        "--no-grpc",
        action="store_true",
        default=None,
        help="Disable the gRPC server (only serve REST/ASGI)",
    )
    parser.add_argument(
        "--no-telemetry",
        action="store_true",
        default=None,
        help="Disable all telemetry export (traces, metrics)",
    )
    parser.add_argument(
        "--otel-endpoint",
        default=None,
        metavar="URL",
        help=(
            "OpenTelemetry collector endpoint "
            "(e.g. http://localhost:4318 for Jaeger v2). "
            "Also reads OTEL_EXPORTER_OTLP_ENDPOINT env var."
        ),
    )
    parser.add_argument(
        "--otel-protocol",
        choices=["grpc", "http/protobuf"],
        default=None,
        help="OTLP export protocol (default: http/protobuf)",
    )
    parser.add_argument(
        "--otel-service-name",
        default=None,
        metavar="NAME",
        help="Service name for traces (default: genkit-asgi-hello)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Enable debug mode (Swagger UI, relaxed CSP). Do not use in production.",
    )
    parser.add_argument(
        "--log-format",
        choices=["json", "console"],
        default=None,
        help="Log output format (default from settings: json)",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Per-request timeout in seconds (default from settings: 120)",
    )
    parser.add_argument(
        "--max-body-size",
        type=int,
        default=None,
        metavar="BYTES",
        help="Max request body size in bytes (default from settings: 1048576)",
    )
    parser.add_argument(
        "--rate-limit",
        default=None,
        metavar="RATE",
        help="Rate limit string, e.g. '60/minute' (default from settings: 60/minute)",
    )
    # Use parse_known_args so extra arguments injected by wrapper tools
    # (e.g. `genkit start` injects "start" into the subprocess argv)
    # are silently ignored instead of causing an error.
    args, _unknown = parser.parse_known_args()
    return args
