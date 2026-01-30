#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# RAG with Pinecone Demo
# ======================
#
# Demonstrates Retrieval Augmented Generation using Pinecone.
#
# Prerequisites:
#   - GEMINI_API_KEY environment variable set
#   - PINECONE_API_KEY environment variable set
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

print_help() {
    print_banner "RAG with Pinecone" "🌲"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GEMINI_API_KEY     Required. Your Gemini API key"
    echo "  PINECONE_API_KEY   Required. Your Pinecone API key"
    echo ""
    echo "This demo shows:"
    echo "  - Document indexing with Pinecone"
    echo "  - Semantic retrieval"
    echo "  - Augmented generation"
    echo ""
    echo "Get API keys from:"
    echo "  - Google: https://makersuite.google.com/app/apikey"
    echo "  - Pinecone: https://app.pinecone.io/"
    print_help_footer
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "RAG with Pinecone" "🌲"

check_env_var "GEMINI_API_KEY" "https://makersuite.google.com/app/apikey" || true
check_env_var "PINECONE_API_KEY" "https://app.pinecone.io/" || true

install_deps

genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
