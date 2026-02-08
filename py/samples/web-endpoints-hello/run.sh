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
#   ./run.sh                          # Start with FastAPI + gRPC (default)
#   ./run.sh --framework litestar     # Start with Litestar + gRPC
#   ./run.sh --framework quart        # Start with Quart + gRPC
#   ./run.sh --server granian          # Use granian instead of uvicorn
#   ./run.sh --no-grpc                # REST only, no gRPC server
#   ./run.sh --grpc-port 50052        # Custom gRPC port
#   ./run.sh --help                   # Show this help message

set -euo pipefail
cd "$(dirname "$0")"

# shellcheck source=scripts/_common.sh
source "$(dirname "$0")/scripts/_common.sh"

print_help() {
    print_banner "Genkit Endpoints Demo" "⚡"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --framework fastapi|litestar|quart  ASGI framework (default: fastapi)"
    echo "  --server granian|uvicorn|hypercorn  ASGI server (default: uvicorn)"
    echo "  --port PORT                   REST server port (default: 8080)"
    echo "  --grpc-port PORT              gRPC server port (default: 50051)"
    echo "  --no-grpc                     Disable gRPC server (REST only)"
    echo "  --env ENV                     Load .<ENV>.env file"
    echo "  --no-telemetry                Disable telemetry"
    echo "  --help                        Show this help message"
    echo ""
    echo "Servers started:"
    echo "  REST  (ASGI)   http://localhost:8080  (Swagger UI at /docs)"
    echo "  gRPC           localhost:50051        (reflection enabled)"
    echo "  Genkit DevUI   http://localhost:4000  (dev mode only)"
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

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "Genkit Endpoints Demo" "⚡"

check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/apikey" || true

install_deps

# Generate gRPC stubs if they don't exist.
if [[ ! -f src/generated/genkit_sample_pb2_grpc.py ]]; then
    echo -e "${BLUE}Generating gRPC stubs...${NC}"
    bash scripts/generate_proto.sh
fi

# Auto-open Swagger UI once the server is ready.
(
    sleep 3
    echo -e "${GREEN}Opening Swagger UI...${NC}"
    open_browser_for_url "http://localhost:8080/docs"
) &

# Build watchmedo args. Always watch src/; also watch monorepo core
# libraries when running inside the genkit repo (enables hot reload on
# framework/plugin changes). When copied as a standalone template, the
# ../../packages and ../../plugins dirs won't exist and are skipped.
WATCH_DIRS=(-d src)
[[ -d ../../packages ]] && WATCH_DIRS+=(-d ../../packages)
[[ -d ../../plugins ]]  && WATCH_DIRS+=(-d ../../plugins)

# Pass --debug by default for local development (enables Swagger UI
# and relaxes the CSP so the docs pages can load CDN resources).
genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        "${WATCH_DIRS[@]}" \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run python -m src --debug "$@"
