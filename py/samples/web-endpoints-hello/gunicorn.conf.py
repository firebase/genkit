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

"""Gunicorn configuration for production multi-worker deployments.

Gunicorn manages worker processes so the application can use all CPU
cores.  Each worker runs its own event loop and Genkit instance.

When to use gunicorn:
    - Multi-core production deployments (Cloud Run, GKE, EC2, etc.)
    - When you need process-level isolation between requests
    - When running behind a load balancer (Cloud Run, ALB, etc.)

When NOT to use gunicorn (use ``python -m src`` instead):
    - Local development (hot reload via ``run.sh`` / ``watchmedo``)
    - Single-core containers (Cloud Run min instances = 1 vCPU)
    - When you need the gRPC server to run alongside REST
      (gunicorn only manages the ASGI app; run gRPC separately)

Usage::

    # Start with gunicorn (REST only, multi-worker)
    gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'

    # Override workers via env var
    WEB_CONCURRENCY=8 gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'

    # Override via CLI
    gunicorn -c gunicorn.conf.py -w 8 'src.asgi:create_app()'

Environment variables:

    WEB_CONCURRENCY  — Number of worker processes (default: CPU count * 2 + 1)
    PORT             — Bind port (default: 8080)
    BIND_HOST        — Bind address (default: 0.0.0.0)
    LOG_LEVEL        — Logging level (default: info)
    KEEP_ALIVE       — Keep-alive timeout in seconds (default: 75)
"""

import multiprocessing
import os

# --- Bind ---
_host = os.environ.get("BIND_HOST", "0.0.0.0")  # noqa: S104 — bind to all interfaces for container deployments
_port = os.environ.get("PORT", "8080")
bind = f"{_host}:{_port}"

# --- Workers ---
# Default: (2 * CPU cores) + 1, capped at 12 to avoid memory pressure.
# Cloud Run: set WEB_CONCURRENCY to match your vCPU allocation.
# Single-vCPU: use WEB_CONCURRENCY=1 (or skip gunicorn entirely).
_default_workers = min((multiprocessing.cpu_count() * 2) + 1, 12)
workers = int(os.environ.get("WEB_CONCURRENCY", str(_default_workers)))

# Use uvicorn's ASGI worker class for async support.
worker_class = "uvicorn.workers.UvicornWorker"

# --- Timeouts ---
# Graceful shutdown: Cloud Run sends SIGTERM and waits up to 10s.
graceful_timeout = int(os.environ.get("GRACEFUL_TIMEOUT", "10"))

# Worker timeout: kill workers that hang longer than this (120s gives
# LLM calls enough time to complete; adjust for your use case).
timeout = int(os.environ.get("WORKER_TIMEOUT", "120"))

# Keep-alive: 75s to avoid load balancer disconnect races.
# Must be > load balancer idle timeout (typically 60s).
keepalive = int(os.environ.get("KEEP_ALIVE", "75"))

# --- Logging ---
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"  # stderr

# Use JSON access log format in production for structured logging.
_log_format = os.environ.get("LOG_FORMAT", "console")
if _log_format == "json":
    access_log_format = (
        '{"timestamp":"%(t)s","method":"%(m)s","path":"%(U)s",'
        '"status":%(s)s,"duration_ms":%(M)s,"size":%(b)s,'
        '"remote_addr":"%(h)s","user_agent":"%(a)s"}'
    )

# --- Process naming ---
proc_name = "genkit-endpoints"

# --- Server mechanics ---
# Preload the app in the master process for faster worker startup
# and shared memory. Disable if your app has import-time side effects
# that should run per-worker.
preload_app = False

# Reuse port for zero-downtime restarts on Linux (SO_REUSEPORT).
reuse_port = True

# Maximum requests per worker before recycling (prevents memory leaks).
# Jitter adds randomness so workers don't all restart simultaneously.
max_requests = int(os.environ.get("MAX_REQUESTS", "10000"))
max_requests_jitter = int(os.environ.get("MAX_REQUESTS_JITTER", "1000"))

# --- Hooks ---


def on_starting(server):  # noqa: ANN001, ANN201 — gunicorn hook signature is fixed
    """Log startup configuration."""
    server.log.info(
        "Starting gunicorn",
        extra={
            "workers": workers,
            "bind": bind,
            "worker_class": worker_class,
            "keepalive": keepalive,
            "timeout": timeout,
        },
    )


def post_fork(server, worker):  # noqa: ANN001, ANN201 — gunicorn hook signature is fixed
    """Per-worker initialization after fork."""
    server.log.info("Worker spawned", extra={"pid": worker.pid})
