#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Jaeger v2 local development helper
# ====================================
#
# Manages a Jaeger v2 all-in-one container via podman (preferred) or
# docker (fallback) for local trace visualization. Jaeger v2 natively
# accepts OTLP (no agent needed).
#
# Auto-installs podman if neither podman nor docker is found
# (macOS: brew, Linux: package manager).
# Auto-initializes and starts the podman machine on macOS.
#
# Usage:
#   ./scripts/jaeger.sh start     # Start Jaeger (installs deps if needed)
#   ./scripts/jaeger.sh stop      # Stop the container
#   ./scripts/jaeger.sh status    # Check if running
#   ./scripts/jaeger.sh logs      # Tail container logs
#   ./scripts/jaeger.sh open      # Open Jaeger UI in browser
#   ./scripts/jaeger.sh restart   # Stop + start
#
# Ports:
#   4317  — OTLP gRPC receiver
#   4318  — OTLP HTTP receiver (used by default)
#   16686 — Jaeger UI
#
# Once running, start the sample with:
#   python src/main.py --otel-endpoint http://localhost:4318

set -euo pipefail

CONTAINER_NAME="genkit-jaeger"
JAEGER_IMAGE="docker.io/jaegertracing/jaeger:latest"
JAEGER_UI_PORT=16686
OTLP_GRPC_PORT=4317
OTLP_HTTP_PORT=4318

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── Container runtime detection ─────────────────────────────────────
# Prefer podman; fall back to docker.

CONTAINER_CMD=""

_detect_container_cmd() {
    if command -v podman &>/dev/null; then
        CONTAINER_CMD="podman"
    elif command -v docker &>/dev/null; then
        CONTAINER_CMD="docker"
    fi
}

_detect_container_cmd

_install_podman() {
    echo -e "${YELLOW}Neither podman nor docker found. Installing podman...${NC}"

    if [[ "$(uname -s)" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install podman
        else
            echo -e "${RED}Error: Homebrew is required to install podman on macOS.${NC}"
            echo "Install Homebrew: https://brew.sh"
            echo "Then run: brew install podman"
            echo "Or install Docker Desktop: https://www.docker.com/products/docker-desktop"
            exit 1
        fi
    elif [[ "$(uname -s)" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y podman
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y podman
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm podman
        else
            echo -e "${RED}Error: Could not detect package manager.${NC}"
            echo "Install podman manually: https://podman.io/docs/installation"
            echo "Or install docker: https://docs.docker.com/engine/install/"
            exit 1
        fi
    else
        echo -e "${RED}Error: Unsupported OS. Install podman or docker manually.${NC}"
        echo "See: https://podman.io/docs/installation"
        exit 1
    fi

    echo -e "${GREEN}podman installed successfully.${NC}"
    CONTAINER_CMD="podman"
}

_ensure_container_runtime() {
    # Install podman if neither runtime is available.
    if [[ -z "$CONTAINER_CMD" ]]; then
        _install_podman
    fi

    # On macOS, podman runs containers in a Linux VM (the "machine").
    # Initialize and start it if needed. Docker Desktop handles this
    # transparently, so we only need this for podman.
    if [[ "$CONTAINER_CMD" == "podman" && "$(uname -s)" == "Darwin" ]]; then
        if ! podman machine inspect &>/dev/null 2>&1; then
            echo -e "${YELLOW}Initializing podman machine...${NC}"
            podman machine init --cpus 2 --memory 2048 --disk-size 20
        fi

        if ! podman machine inspect --format '{{.State}}' 2>/dev/null | grep -qi "running"; then
            echo -e "${YELLOW}Starting podman machine...${NC}"
            podman machine start
            echo -e "${GREEN}Podman machine started.${NC}"
        fi
    fi
}

_is_running() {
    $CONTAINER_CMD container inspect "$CONTAINER_NAME" &>/dev/null 2>&1
}

cmd_start() {
    _ensure_container_runtime

    if _is_running; then
        echo -e "${GREEN}Jaeger is already running (via ${CONTAINER_CMD}).${NC}"
        echo -e "  UI:        ${BLUE}http://localhost:${JAEGER_UI_PORT}${NC}"
        echo -e "  OTLP HTTP: ${BLUE}http://localhost:${OTLP_HTTP_PORT}${NC}"
        echo -e "  OTLP gRPC: ${BLUE}http://localhost:${OTLP_GRPC_PORT}${NC}"
        return 0
    fi

    echo -e "${BLUE}Pulling Jaeger v2 image (via ${CONTAINER_CMD})...${NC}"
    $CONTAINER_CMD pull "$JAEGER_IMAGE" 2>/dev/null || true

    echo -e "${BLUE}Starting Jaeger v2 (all-in-one)...${NC}"

    $CONTAINER_CMD run -d \
        --name "$CONTAINER_NAME" \
        --replace \
        -p "${OTLP_GRPC_PORT}:4317" \
        -p "${OTLP_HTTP_PORT}:4318" \
        -p "${JAEGER_UI_PORT}:16686" \
        "$JAEGER_IMAGE"

    # Wait for readiness.
    echo -n "Waiting for Jaeger..."
    for _ in $(seq 1 15); do
        if curl -sf "http://localhost:${JAEGER_UI_PORT}/" >/dev/null 2>&1; then
            echo -e " ${GREEN}ready!${NC}"
            echo ""
            echo -e "  UI:        ${BLUE}http://localhost:${JAEGER_UI_PORT}${NC}"
            echo -e "  OTLP HTTP: ${BLUE}http://localhost:${OTLP_HTTP_PORT}${NC}"
            echo -e "  OTLP gRPC: ${BLUE}http://localhost:${OTLP_GRPC_PORT}${NC}"
            echo ""
            echo -e "Run the sample with tracing:"
            echo -e "  ${GREEN}python src/main.py --otel-endpoint http://localhost:${OTLP_HTTP_PORT}${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    echo -e " ${RED}timeout${NC}"
    echo "Check logs with: $0 logs"
    return 1
}

cmd_stop() {
    if _is_running; then
        echo -e "${YELLOW}Stopping Jaeger (via ${CONTAINER_CMD})...${NC}"
        $CONTAINER_CMD stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        $CONTAINER_CMD rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        echo -e "${GREEN}Jaeger stopped.${NC}"
    else
        echo "Jaeger is not running."
    fi
}

cmd_status() {
    if _is_running; then
        echo -e "${GREEN}Jaeger is running (via ${CONTAINER_CMD}).${NC}"
        echo -e "  UI:        ${BLUE}http://localhost:${JAEGER_UI_PORT}${NC}"
        echo -e "  OTLP HTTP: ${BLUE}http://localhost:${OTLP_HTTP_PORT}${NC}"
        $CONTAINER_CMD container inspect "$CONTAINER_NAME" --format '  Container: {{.Id}}  Started: {{.State.StartedAt}}'
    else
        echo -e "${YELLOW}Jaeger is not running.${NC}"
        echo "Start with: $0 start"
    fi
}

cmd_logs() {
    if _is_running; then
        $CONTAINER_CMD logs -f "$CONTAINER_NAME"
    else
        echo "Jaeger is not running."
    fi
}

cmd_open() {
    local url="http://localhost:${JAEGER_UI_PORT}"
    if _is_running; then
        echo -e "Opening Jaeger UI: ${BLUE}${url}${NC}"
        if command -v open &>/dev/null; then
            open "$url"
        elif command -v xdg-open &>/dev/null; then
            xdg-open "$url"
        else
            echo "Open in your browser: $url"
        fi
    else
        echo -e "${YELLOW}Jaeger is not running. Start first: $0 start${NC}"
    fi
}

cmd_restart() {
    cmd_stop
    cmd_start
}

# ── Main ──────────────────────────────────────────────────────────────

case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    open)    cmd_open ;;
    restart) cmd_restart ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|open|restart}"
        echo ""
        echo "Manage a local Jaeger v2 container for trace visualization."
        echo "Uses podman (preferred) or docker (fallback)."
        exit 1
        ;;
esac
