#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Genkit Endpoints Demo (REST + gRPC)
# ====================================
#
# Demonstrates integrating Genkit with ASGI web frameworks and gRPC.
# Both servers start in parallel: REST on :8080, gRPC on :50051.
#
# Prerequisites:
#   - GEMINI_API_KEY environment variable set
#
# Usage:
#   ./run.sh                          # Start everything (default)
#   ./run.sh start                    # Same — start all services
#   ./run.sh start --framework litestar  # Start with Litestar + gRPC
#   ./run.sh start --framework quart     # Start with Quart + gRPC
#   ./run.sh start --server granian      # Use granian instead of uvicorn
#   ./run.sh start --no-grpc             # REST only, no gRPC server
#   ./run.sh start --grpc-port 50052     # Custom gRPC port
#   ./run.sh --help                      # Show this help message

set -euo pipefail
cd "$(dirname "$0")"

# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/scripts/_common.sh"

print_help() {
    print_banner "Genkit Endpoints Demo" "⚡"
    echo "Usage: ./run.sh [start] [options]"
    echo ""
    echo "Commands:"
    echo "  start                         Start all services (default)"
    echo ""
    echo "Options:"
    echo "  --framework fastapi|litestar|quart  ASGI framework (default: fastapi)"
    echo "  --server granian|uvicorn|hypercorn  ASGI server (default: uvicorn)"
    echo "  --port PORT                   REST server port (default: 8080)"
    echo "  --grpc-port PORT              gRPC server port (default: 50051)"
    echo "  --no-grpc                     Disable gRPC server (REST only)"
    echo "  --env ENV                     Load .<ENV>.env file"
    echo "  --no-telemetry                Disable Jaeger + OTLP tracing"
    echo "  --help                        Show this help message"
    echo ""
    echo "Services started:"
    echo "  Swagger UI     http://localhost:8080/docs  (REST API explorer)"
    echo "  grpcui         http://localhost:...        (gRPC web UI, if installed)"
    echo "  Jaeger UI      http://localhost:16686      (trace viewer)"
    echo "  Genkit DevUI   http://localhost:4000       (flow/trace inspector)"
    echo "  REST  (ASGI)   http://localhost:8080       (app server)"
    echo "  gRPC           localhost:50051             (reflection enabled)"
    echo ""
    echo "Test gRPC endpoints:"
    echo "  grpcui -plaintext localhost:50051      # Web UI"
    echo "  grpcurl -plaintext localhost:50051 list  # CLI"
    echo ""
    echo "Environment Variables:"
    echo "  GEMINI_API_KEY    Required. Your Gemini API key"
    echo ""
    echo "Get an API key from: https://aistudio.google.com/apikey"
    print_help_footer
}

# Handle --help before anything else.
case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

# Consume the optional "start" subcommand.  If the first argument is
# "start", shift it off so it isn't forwarded to the Python app.
# Bare `./run.sh` (no args) behaves the same as `./run.sh start`.
case "${1:-}" in
    start) shift ;;
esac

# Parse flags we need to act on in run.sh (before forwarding to app).
NO_TELEMETRY=false
NO_GRPC=false
GRPC_PORT=50051
REST_PORT=8080
_next_is_grpc_port=false
_next_is_rest_port=false
for arg in "$@"; do
    if $_next_is_grpc_port; then
        _next_is_grpc_port=false
        # Only consume the value if it doesn't look like another flag.
        if [[ "$arg" != --* ]]; then
            GRPC_PORT="$arg"
            continue
        fi
    fi
    if $_next_is_rest_port; then
        _next_is_rest_port=false
        if [[ "$arg" != --* ]]; then
            REST_PORT="$arg"
            continue
        fi
    fi
    case "$arg" in
        --no-telemetry) NO_TELEMETRY=true ;;
        --no-grpc)      NO_GRPC=true ;;
        --grpc-port)    _next_is_grpc_port=true ;;
        --port)         _next_is_rest_port=true ;;
    esac
done

print_banner "Genkit Endpoints Demo" "⚡"

check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/apikey" || true

# Set the service name for OpenTelemetry traces. Genkit's TracerProvider
# is created at import time (before our code runs), so we must set this
# as an env var so OTel's Resource.create() picks it up automatically.
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-genkit-endpoints-hello}"

install_deps

# Generate gRPC stubs if they don't exist.
if [[ ! -f src/generated/genkit_sample_pb2_grpc.py ]]; then
    echo -e "${BLUE}Generating gRPC stubs...${NC}"
    bash scripts/generate_proto.sh
fi

# ── Jaeger (tracing) ────────────────────────────────────────────────
# Auto-start Jaeger so traces are visible at http://localhost:16686.
# Pass --no-telemetry to skip this step.
JAEGER_OTLP_PORT="${JAEGER_OTLP_PORT:-4318}"
OTEL_ARGS=()
if [[ "$NO_TELEMETRY" == "false" ]]; then
    if ./scripts/jaeger.sh start 2>/dev/null; then
        OTEL_ARGS=(--otel-endpoint "http://localhost:${JAEGER_OTLP_PORT}")
        echo -e "${GREEN}Jaeger started — traces at http://localhost:16686${NC}"
    else
        echo -e "${YELLOW}Jaeger skipped (continuing without tracing)${NC}"
    fi
fi

# ── Auto-open browser tabs ──────────────────────────────────────────
# Open Swagger UI once the REST server is ready.
(
    sleep 3
    echo -e "${GREEN}Opening Swagger UI...${NC}"
    open_browser_for_url "http://localhost:${REST_PORT}/docs"
) &

# Open grpcui if gRPC is enabled and grpcui is installed.
if [[ "$NO_GRPC" == "false" ]]; then
    if command -v grpcui &>/dev/null; then
        (
            # Wait for gRPC server to be ready (slightly longer than REST).
            sleep 5
            echo -e "${GREEN}Opening grpcui on port ${GRPC_PORT}...${NC}"
            grpcui -open-browser -plaintext "localhost:${GRPC_PORT}"
        ) &
    else
        echo -e "${YELLOW}grpcui not found — install with: go install github.com/fullstorydev/grpcui/cmd/grpcui@latest${NC}"
    fi
fi

# ── Start the app ───────────────────────────────────────────────────
# Build watchmedo args. Always watch src/; also watch monorepo core
# libraries when running inside the genkit repo (enables hot reload on
# framework/plugin changes). When copied as a standalone template, the
# ../../packages and ../../plugins dirs won't exist and are skipped.
WATCH_DIRS=(-d src)
[[ -d ../../packages ]] && WATCH_DIRS+=(-d ../../packages)
[[ -d ../../plugins ]]  && WATCH_DIRS+=(-d ../../plugins)

# Pass --debug by default for local development (enables Swagger UI
# and relaxes the CSP so the docs pages can load CDN resources).
# genkit_start_with_browser also opens the Genkit DevUI in a browser.
genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        ${WATCH_DIRS[@]+"${WATCH_DIRS[@]}"} \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run python -m src --debug ${OTEL_ARGS[@]+"${OTEL_ARGS[@]}"} "$@"
