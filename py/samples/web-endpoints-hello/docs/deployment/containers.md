# Containers

The sample includes a multi-stage `Containerfile` that produces a
minimal, secure production image using Google's distroless base.

## Image architecture

```
┌──────────────────────────────────────────────┐
│  Builder stage (python:3.13-slim)            │
│                                              │
│  1. Install uv                               │
│  2. Copy pyproject.toml                      │
│  3. uv pip install → /app/.venv/             │
└──────────────┬───────────────────────────────┘
               │ COPY site-packages
               ▼
┌──────────────────────────────────────────────┐
│  Runtime stage (distroless/python3:nonroot)  │
│                                              │
│  - No shell, no package manager              │
│  - Runs as uid 65534 (nonroot)               │
│  - ~50 MB base image                         │
│  - Python 3.13 (Debian 13 trixie)            │
│                                              │
│  CMD ["-m", "src"]                           │
└──────────────────────────────────────────────┘
```

## Building

```bash
# Podman (preferred)
podman build -f Containerfile -t genkit-endpoints .

# Docker
docker build -f Containerfile -t genkit-endpoints .
```

## Running

```bash
podman run \
  -p 8080:8080 \
  -p 50051:50051 \
  -e GEMINI_API_KEY=<your-key> \
  genkit-endpoints
```

## Why distroless?

| Property | distroless | python:3.13-slim |
|----------|-----------|------------------|
| Base size | ~50 MB | ~150 MB |
| Shell | No | Yes (`/bin/sh`) |
| Package manager | No | Yes (`apt`) |
| setuid binaries | No | Yes |
| Default user | nonroot (65534) | root (0) |
| Attack surface | Minimal | Moderate |

The distroless image contains only the Python runtime and CA
certificates — nothing else. This dramatically reduces the attack
surface for production deployments.

## Debugging with slim

If you need a shell for debugging, swap the runtime stage:

```dockerfile
# Replace:
FROM gcr.io/distroless/python3-debian13:nonroot

# With:
FROM python:3.13-slim AS runtime
```

And update the CMD:

```dockerfile
ENTRYPOINT ["python3", "-m", "src"]
```

## Layer caching

The `Containerfile` is structured for optimal layer caching:

1. **`pyproject.toml` copied first** — dependency installation is
   cached as long as dependencies don't change.
2. **Application code copied last** — code changes only rebuild the
   final layer.

## Exposed ports

| Port | Protocol | Service |
|------|----------|---------|
| `8080` | HTTP | REST API (FastAPI/Litestar/Quart) |
| `50051` | gRPC | gRPC service with reflection |

## Environment variables

The container respects all environment variables listed in the
[Deployment Overview](overview.md#environment-variables). Key ones
for container orchestration:

- `PORT` — REST port (Cloud Run sets this automatically)
- `GRPC_PORT` — gRPC port
- `WEB_CONCURRENCY` — Worker count for gunicorn mode
- `LOG_FORMAT=json` — Structured logging for log aggregators
