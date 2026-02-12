# Setup

## Prerequisites

The `./setup.sh` script auto-detects your OS and installs all tools:

```bash
./setup.sh           # Install everything
./setup.sh --check   # Just check what's installed
```

| Tool | macOS | Debian / Ubuntu | Fedora |
|------|-------|-----------------|--------|
| **uv** | curl installer | curl installer | curl installer |
| **just** | `brew install just` | `apt install just` (24.04+) or official installer | `dnf install just` (39+) or official installer |
| **podman** (or docker) | `brew install podman` | `apt install podman` | `dnf install podman` |
| **genkit CLI** | `npm install -g genkit-cli` | `npm install -g genkit-cli` | `npm install -g genkit-cli` |
| **grpcurl** | `brew install grpcurl` | `go install .../grpcurl@latest` or prebuilt binary | `go install .../grpcurl@latest` or prebuilt binary |
| **grpcui** | `brew install grpcui` | `go install .../grpcui@latest` | `go install .../grpcui@latest` |
| **shellcheck** | `brew install shellcheck` | `apt install shellcheck` | `dnf install ShellCheck` |

## Get a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key

```bash
export GEMINI_API_KEY=<your-api-key>
```

## Per-Environment Secrets (optional)

For local dev / staging / prod separation, use
[dotenvx](https://dotenvx.com/) or `.env` files:

```bash
# .local.env (git-ignored, local development)
GEMINI_API_KEY=AIza...

# .staging.env
GEMINI_API_KEY=AIza_staging_key...

# .production.env
GEMINI_API_KEY=AIza_prod_key...
```

```bash
# Load a specific environment
dotenvx run -f .staging.env -- ./run.sh
```

For deployed environments, use the platform's native secrets instead
(see [Cloud Platforms](../deployment/cloud-platforms.md)).

## Install Dependencies

```bash
# Install all project dependencies (production + dev + test)
uv sync --all-extras

# Or just production deps
uv sync
```
