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

"""Tests for application configuration and CLI argument parsing.

Covers Settings defaults, environment variable loading, .env file
resolution, and parse_args() CLI argument handling.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/config_test.py -v
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import (
    Settings,
    _build_env_files,  # noqa: PLC2701 — testing internal implementation
    make_settings,
    parse_args,
)


def test_build_env_files_no_env() -> None:
    """Without an env name, only .env is returned."""
    files = _build_env_files(None)
    assert files == (".env",)


def test_build_env_files_with_env() -> None:
    """With an env name, both .env and .<env>.env are returned."""
    files = _build_env_files("staging")
    assert files == (".env", ".staging.env")


def test_build_env_files_local() -> None:
    """Common 'local' env name produces .local.env."""
    files = _build_env_files("local")
    assert files == (".env", ".local.env")


def test_settings_defaults() -> None:
    """Settings has sensible defaults for all fields."""
    settings = Settings()

    assert settings.port == 8080
    assert settings.grpc_port == 50051
    assert settings.server == "uvicorn"
    assert settings.framework == "fastapi"
    assert settings.log_level == "info"
    assert settings.telemetry_disabled is False
    # gemini_api_key defaults to '' but may be set via env; skip asserting value.
    assert isinstance(settings.gemini_api_key, str)
    assert settings.otel_service_name == "genkit-endpoints-hello"
    assert not settings.otel_exporter_otlp_endpoint
    assert settings.otel_exporter_otlp_protocol == "http/protobuf"
    assert settings.debug is False
    assert settings.log_format == "json"
    assert settings.shutdown_grace == 10.0
    assert settings.cache_enabled is True
    assert settings.cache_ttl == 300
    assert settings.cache_max_size == 1024
    assert settings.cb_enabled is True
    assert settings.cb_failure_threshold == 5
    assert settings.cb_recovery_timeout == 30.0
    assert settings.llm_timeout == 120_000
    assert settings.keep_alive_timeout == 75
    assert settings.httpx_pool_max == 100
    assert settings.httpx_pool_max_keepalive == 20
    assert not settings.cors_allowed_origins
    assert settings.cors_allowed_methods == "GET,POST,OPTIONS"
    assert settings.cors_allowed_headers == "Content-Type,Authorization,X-Request-ID"
    assert not settings.trusted_hosts
    assert settings.rate_limit_default == "60/minute"
    assert settings.max_body_size == 1_048_576
    assert settings.request_timeout == 120.0
    assert settings.hsts_max_age == 31_536_000
    assert settings.gzip_min_size == 500
    assert not settings.sentry_dsn
    assert settings.sentry_traces_sample_rate == 0.1
    assert not settings.sentry_environment


def test_settings_from_env_vars() -> None:
    """Settings can be overridden via environment variables."""
    env = {
        "PORT": "9090",
        "GRPC_PORT": "50052",
        "SERVER": "uvicorn",
        "FRAMEWORK": "litestar",
        "LOG_LEVEL": "debug",
    }
    with patch.dict("os.environ", env, clear=False):
        settings = Settings()

    assert settings.port == 9090
    assert settings.grpc_port == 50052
    assert settings.server == "uvicorn"
    assert settings.framework == "litestar"
    assert settings.log_level == "debug"


def test_settings_extra_fields_ignored() -> None:
    """Unknown environment variables don't cause errors."""
    with patch.dict("os.environ", {"UNKNOWN_FIELD": "test"}, clear=False):
        settings = Settings()

    assert settings.port == 8080  # Defaults still work.


def test_settings_server_choices() -> None:
    """Only valid server choices are accepted."""
    for valid in ("granian", "uvicorn", "hypercorn"):
        with patch.dict("os.environ", {"SERVER": valid}, clear=False):
            settings = Settings()
            assert settings.server == valid


def test_settings_framework_choices() -> None:
    """Only valid framework choices are accepted."""
    for valid in ("fastapi", "litestar", "quart"):
        with patch.dict("os.environ", {"FRAMEWORK": valid}, clear=False):
            settings = Settings()
            assert settings.framework == valid


def test_make_settings_returns_settings() -> None:
    """make_settings returns a Settings instance."""
    settings = make_settings()
    assert isinstance(settings, Settings)


def test_make_settings_with_env_name() -> None:
    """make_settings with an env name doesn't crash (files may not exist)."""
    settings = make_settings(env="test")
    assert isinstance(settings, Settings)


def test_parse_args_defaults() -> None:
    """parse_args with no arguments returns Nones for optional fields."""
    with patch("sys.argv", ["prog"]):
        args = parse_args()

    assert args.env is None
    assert args.framework is None
    assert args.server is None
    assert args.port is None
    assert args.grpc_port is None
    assert args.no_grpc is None
    assert args.no_telemetry is None
    assert args.otel_endpoint is None
    assert args.otel_protocol is None
    assert args.otel_service_name is None


def test_parse_args_port_override() -> None:
    """--port sets the port value."""
    with patch("sys.argv", ["prog", "--port", "9090"]):
        args = parse_args()

    assert args.port == 9090


def test_parse_args_grpc_port() -> None:
    """--grpc-port sets the gRPC port value."""
    with patch("sys.argv", ["prog", "--grpc-port", "50052"]):
        args = parse_args()

    assert args.grpc_port == 50052


def test_parse_args_no_grpc() -> None:
    """--no-grpc disables the gRPC server."""
    with patch("sys.argv", ["prog", "--no-grpc"]):
        args = parse_args()

    assert args.no_grpc is True


def test_parse_args_framework_choice() -> None:
    """--framework accepts valid choices."""
    for fw in ("fastapi", "litestar", "quart"):
        with patch("sys.argv", ["prog", "--framework", fw]):
            args = parse_args()
        assert args.framework == fw


def test_parse_args_server_choice() -> None:
    """--server accepts valid choices."""
    for srv in ("granian", "uvicorn", "hypercorn"):
        with patch("sys.argv", ["prog", "--server", srv]):
            args = parse_args()
        assert args.server == srv


def test_parse_args_env_name() -> None:
    """--env sets the environment name."""
    with patch("sys.argv", ["prog", "--env", "staging"]):
        args = parse_args()

    assert args.env == "staging"


def test_parse_args_no_telemetry() -> None:
    """--no-telemetry disables telemetry."""
    with patch("sys.argv", ["prog", "--no-telemetry"]):
        args = parse_args()

    assert args.no_telemetry is True


def test_parse_args_otel_options() -> None:
    """OTel CLI options are parsed correctly."""
    with patch(
        "sys.argv",
        [
            "prog",
            "--otel-endpoint",
            "http://localhost:4318",
            "--otel-protocol",
            "grpc",
            "--otel-service-name",
            "my-service",
        ],
    ):
        args = parse_args()

    assert args.otel_endpoint == "http://localhost:4318"
    assert args.otel_protocol == "grpc"
    assert args.otel_service_name == "my-service"


def test_parse_args_debug() -> None:
    """--debug enables debug mode."""
    with patch("sys.argv", ["prog", "--debug"]):
        args = parse_args()

    assert args.debug is True


def test_parse_args_log_format() -> None:
    """--log-format sets the log output format."""
    with patch("sys.argv", ["prog", "--log-format", "console"]):
        args = parse_args()

    assert args.log_format == "console"


def test_parse_args_request_timeout() -> None:
    """--request-timeout sets the per-request timeout."""
    with patch("sys.argv", ["prog", "--request-timeout", "60.0"]):
        args = parse_args()

    assert args.request_timeout == 60.0


def test_parse_args_max_body_size() -> None:
    """--max-body-size sets the max request body size."""
    with patch("sys.argv", ["prog", "--max-body-size", "2097152"]):
        args = parse_args()

    assert args.max_body_size == 2097152


def test_parse_args_rate_limit() -> None:
    """--rate-limit sets the rate limit string."""
    with patch("sys.argv", ["prog", "--rate-limit", "100/minute"]):
        args = parse_args()

    assert args.rate_limit == "100/minute"


def test_parse_args_invalid_framework() -> None:
    """Invalid --framework raises SystemExit."""
    with patch("sys.argv", ["prog", "--framework", "django"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_parse_args_invalid_server() -> None:
    """Invalid --server raises SystemExit."""
    with patch("sys.argv", ["prog", "--server", "gunicorn"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_settings_security_from_env() -> None:
    """Security settings can be overridden via environment variables."""
    env = {
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
        "CORS_ALLOWED_METHODS": "GET,POST,PUT",
        "CORS_ALLOWED_HEADERS": "Content-Type,Authorization",
        "TRUSTED_HOSTS": "app.example.com",
        "MAX_BODY_SIZE": "2097152",
        "REQUEST_TIMEOUT": "60.0",
        "HSTS_MAX_AGE": "86400",
        "GZIP_MIN_SIZE": "1000",
        "RATE_LIMIT_DEFAULT": "100/minute",
    }
    with patch.dict("os.environ", env, clear=False):
        settings = Settings()

    assert settings.cors_allowed_origins == "https://app.example.com"
    assert settings.cors_allowed_methods == "GET,POST,PUT"
    assert settings.cors_allowed_headers == "Content-Type,Authorization"
    assert settings.trusted_hosts == "app.example.com"
    assert settings.max_body_size == 2097152
    assert settings.request_timeout == 60.0
    assert settings.hsts_max_age == 86400
    assert settings.gzip_min_size == 1000
    assert settings.rate_limit_default == "100/minute"


def test_settings_connection_from_env() -> None:
    """Connection settings can be overridden via environment variables."""
    env = {
        "HTTPX_POOL_MAX": "200",
        "HTTPX_POOL_MAX_KEEPALIVE": "40",
        "LLM_TIMEOUT": "60000",
        "KEEP_ALIVE_TIMEOUT": "90",
    }
    with patch.dict("os.environ", env, clear=False):
        settings = Settings()

    assert settings.httpx_pool_max == 200
    assert settings.httpx_pool_max_keepalive == 40
    assert settings.llm_timeout == 60000
    assert settings.keep_alive_timeout == 90


# ──────────────────────────────────────────────────────────────────
# debug=False invariant tests — configuration layer
#
# These verify that the config system never accidentally sets
# debug=True or misparses boolean env vars. If pydantic-settings
# changes its boolean parsing, these tests catch the regression.
# ──────────────────────────────────────────────────────────────────


def test_invariant_debug_default_is_false() -> None:
    """The production default for debug MUST be False."""
    settings = Settings()
    assert settings.debug is False, "debug must default to False (secure)"


def test_invariant_debug_env_false_string() -> None:
    """DEBUG=false (string) must parse to False."""
    with patch.dict("os.environ", {"DEBUG": "false"}, clear=False):
        settings = Settings()
    assert settings.debug is False


def test_invariant_debug_env_zero_string() -> None:
    """DEBUG=0 (string) must parse to False."""
    with patch.dict("os.environ", {"DEBUG": "0"}, clear=False):
        settings = Settings()
    assert settings.debug is False


def test_invariant_debug_env_empty_string_rejects() -> None:
    """DEBUG='' (empty string) must be rejected, not silently accepted.

    Pydantic-settings raises ValidationError for empty string booleans.
    This is secure: ambiguous input is rejected rather than defaulting
    to True or False.
    """
    with patch.dict("os.environ", {"DEBUG": ""}, clear=False):
        with pytest.raises(ValidationError):
            Settings()


def test_invariant_debug_env_true_string() -> None:
    """DEBUG=true (string) must parse to True."""
    with patch.dict("os.environ", {"DEBUG": "true"}, clear=False):
        settings = Settings()
    assert settings.debug is True


def test_invariant_debug_env_one_string() -> None:
    """DEBUG=1 (string) must parse to True."""
    with patch.dict("os.environ", {"DEBUG": "1"}, clear=False):
        settings = Settings()
    assert settings.debug is True


def test_invariant_cli_debug_default_is_none() -> None:
    """--debug is not set by default (None), so settings.debug wins."""
    with patch("sys.argv", ["prog"]):
        args = parse_args()
    assert args.debug is None, "CLI default must be None (defer to settings)"


def test_invariant_cli_debug_flag_sets_true() -> None:
    """--debug flag must set debug to True."""
    with patch("sys.argv", ["prog", "--debug"]):
        args = parse_args()
    assert args.debug is True


def test_invariant_log_format_default_is_json() -> None:
    """Production log format must default to 'json' (machine-parseable)."""
    settings = Settings()
    assert settings.log_format == "json", "log_format must default to 'json' for structured logging"


def test_invariant_cors_default_is_same_origin() -> None:
    """CORS must default to empty string (same-origin), not wildcard."""
    settings = Settings()
    assert not settings.cors_allowed_origins, "cors_allowed_origins must default to '' (same-origin)"
