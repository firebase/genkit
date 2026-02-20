# Deployment Overview

This sample is designed to deploy anywhere that runs containers or
Python. Six cloud platforms are supported out of the box, each with
a dedicated deploy script and CI/CD workflow.

## Supported platforms

| Platform | Deploy script | CI workflow | Runtime |
|----------|---------------|-------------|---------|
| **Google Cloud Run** | `deploy_cloudrun.sh` | `deploy-cloudrun.yml` | Container |
| **Google App Engine** | `deploy_appengine.sh` | `deploy-appengine.yml` | Container |
| **Firebase Hosting** | `deploy_firebase_hosting.sh` | `deploy-firebase.yml` | Cloud Functions |
| **AWS App Runner** | `deploy_aws.sh` | `deploy-aws.yml` | Container |
| **Azure Container Apps** | `deploy_azure.sh` | `deploy-azure.yml` | Container |
| **Fly.io** | `deploy_flyio.sh` | `deploy-flyio.yml` | Container |

## Deployment modes

### Single-process (default)

```bash
python -m src
```

Runs REST (`:8080`) and gRPC (`:50051`) in a single process using
`asyncio.gather()`. Best for:

- Local development
- Single-vCPU containers (Cloud Run, App Runner)
- Serverless platforms

### Multi-worker (gunicorn)

```bash
gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'
```

Gunicorn manages multiple worker processes for multi-core utilization.
Best for:

- Multi-vCPU VMs or containers
- High-throughput production deployments
- When process-level isolation is needed

!!! note
    Gunicorn mode only serves REST. Run the gRPC server separately
    if needed.

### Container

```bash
podman build -f Containerfile -t genkit-endpoints .
podman run -p 8080:8080 -p 50051:50051 -e GEMINI_API_KEY=<key> genkit-endpoints
```

See [Containers](containers.md) for details on the distroless image.

## Environment variables

All configuration is via environment variables (12-factor app):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Google AI API key |
| `PORT` | `8080` | REST server port |
| `GRPC_PORT` | `50051` | gRPC server port |
| `FRAMEWORK` | `fastapi` | REST framework (`fastapi`, `litestar`, `quart`) |
| `SERVER` | `granian` | ASGI server (`granian`, `uvicorn`, `hypercorn`) |
| `LOG_FORMAT` | `console` | `console` (dev) or `json` (production) |
| `LOG_LEVEL` | `info` | Logging level |
| `RATE_LIMIT_DEFAULT` | `60/minute` | Rate limit per client IP |
| `CACHE_TTL` | `300` | Response cache TTL (seconds) |
| `CACHE_ENABLED` | `true` | Enable/disable response cache |
| `CB_FAILURE_THRESHOLD` | `5` | Circuit breaker failure threshold |
| `CB_RECOVERY_TIMEOUT` | `30` | Circuit breaker recovery timeout (seconds) |
| `SENTRY_DSN` | *(empty)* | Sentry error tracking DSN |

## Quick deploy

=== "Cloud Run"

    ```bash
    ./deploy_cloudrun.sh
    ```

=== "App Engine"

    ```bash
    ./deploy_appengine.sh
    ```

=== "AWS App Runner"

    ```bash
    ./deploy_aws.sh
    ```

=== "Azure Container Apps"

    ```bash
    ./deploy_azure.sh
    ```

=== "Fly.io"

    ```bash
    ./deploy_flyio.sh
    ```
