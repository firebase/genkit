# Using as a Template

This sample is designed to be copied out of the monorepo and used as
a standalone project starter for your own Genkit application.

## Copy the sample

```bash
cp -r py/samples/web-endpoints-hello my-project
cd my-project
```

## Pin Genkit dependencies

Inside the monorepo, `genkit` and `genkit-plugin-*` resolve to local
workspace packages. After copying, edit `pyproject.toml` to pin them
to a release version so they install from PyPI:

```toml
# Change from (no version):
"genkit",
"genkit-plugin-google-genai",

# To (pinned to release):
"genkit>=0.5.0",
"genkit-plugin-google-genai>=0.5.0",
```

## Install and run

```bash
./setup.sh              # Install tools (uv, just, podman/docker, genkit CLI)
export GEMINI_API_KEY=<your-key>
just dev                # Start app + Jaeger
```

## What to customize

### Your flows (`src/flows.py`)

Replace the sample flows with your own:

```python
@ai.flow()
async def my_flow(ai: Genkit, input: MyInput) -> MyOutput:
    response = await ai.generate(
        model="googleai/gemini-2.0-flash",
        prompt=f"Do something with {input.text}",
        output=Output(schema=MyOutput),
    )
    return response.output
```

### Your schemas (`src/schemas.py`)

Define Pydantic models for your inputs and outputs:

```python
class MyInput(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)

class MyOutput(BaseModel):
    result: str
    confidence: float = Field(ge=0.0, le=1.0)
```

### Your routes (`src/frameworks/`)

Update the framework adapter to expose your flows as endpoints.
All three adapters (FastAPI, Litestar, Quart) follow the same
pattern — update whichever you use.

### Configuration (`src/config.py`)

Add your own settings to the `Settings` class:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    my_custom_setting: str = "default"
```

Settings are automatically loaded from environment variables and
`.env` files.

## What to keep

These modules are production infrastructure — keep them as-is:

| Module | Purpose |
|--------|---------|
| `cache.py` | Response cache (saves LLM costs) |
| `circuit_breaker.py` | Failure protection |
| `rate_limit.py` | Rate limiting (REST + gRPC) |
| `security.py` | OWASP headers, CORS, body size |
| `connection.py` | HTTP pool tuning |
| `logging.py` | Structured logging |
| `telemetry.py` | OpenTelemetry tracing |

## What to remove

If you don't need certain features:

| Feature | Remove | Effect |
|---------|--------|--------|
| gRPC | `grpc_server.py`, `protos/`, `generated/` | REST only |
| Sentry | `sentry_init.py` | No error tracking |
| Litestar/Quart | `frameworks/litestar_app.py`, `frameworks/quart_app.py` | FastAPI only |
| Sample flows | All flows in `flows.py` | Replace with yours |

## Directory structure after customization

```
my-project/
├── src/
│   ├── flows.py            # YOUR flows
│   ├── schemas.py          # YOUR Pydantic models
│   ├── config.py           # YOUR settings
│   ├── frameworks/
│   │   └── fastapi_app.py  # YOUR routes
│   └── ...                 # Keep: cache, breaker, security, etc.
├── tests/                  # YOUR tests
├── pyproject.toml          # Updated dependencies
├── Containerfile           # Ready for deployment
└── deploy_*.sh             # One-command deploy scripts
```
