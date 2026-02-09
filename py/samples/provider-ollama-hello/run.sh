#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Ollama Hello World Demo
# =======================
#
# Demonstrates local LLM inference, tools, vision, and embeddings with Genkit.
#
# Prerequisites:
#   - Ollama installed and running locally
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

# Models used by this sample
MODELS=(
    "gemma3:latest"       # General generation & structured output
    "mistral-nemo:latest" # Tool calling (gablorken, currency, weather)
    "llava:latest"        # Vision / image description
    "nomic-embed-text"    # Embeddings for RAG
)

check_ollama() {
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}Error: Ollama not found${NC}"
        echo "Install from: https://ollama.com/download"
        return 1
    fi
    
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo -e "${YELLOW}Warning: Ollama server not responding${NC}"
        echo "Start with: ollama serve"
        echo ""
    else
        echo -e "${GREEN}✓${NC} Ollama server is running"
    fi
}

pull_models() {
    echo ""
    echo "Pulling required models..."
    for model in "${MODELS[@]}"; do
        echo -e "  Pulling ${CYAN}${model}${NC}..."
        ollama pull "$model" 2>/dev/null || echo -e "  ${YELLOW}⚠${NC} Could not pull ${model} (will retry on first use)"
    done
    echo ""
}

print_help() {
    print_banner "Ollama Hello World" "🦙"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  - Ollama installed: https://ollama.com/download"
    echo "  - Ollama running: ollama serve"
    echo ""
    echo "Models (auto-pulled on first run):"
    for model in "${MODELS[@]}"; do
        echo "  - $model"
    done
    print_help_footer
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "Ollama Hello World" "🦙"

check_ollama || true
pull_models

install_deps

genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
