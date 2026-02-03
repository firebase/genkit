#!/usr/bin/env bash
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Vertex AI Rerankers and Evaluators Demo
# =======================================
#
# Demonstrates using Vertex AI rerankers for RAG quality improvement
# and evaluators for assessing model outputs.
#
# Prerequisites:
#   - GOOGLE_CLOUD_PROJECT environment variable set
#   - gcloud CLI authenticated
#   - Discovery Engine API enabled (for rerankers)
#   - Vertex AI API enabled (for evaluators)
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

print_help() {
    print_banner "Vertex AI Rerankers & Evaluators" "🔍"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GOOGLE_CLOUD_PROJECT    Required. Your GCP project ID"
    echo ""
    echo "Required APIs:"
    echo "  - Vertex AI API"
    echo "  - Discovery Engine API (for rerankers)"
    echo ""
    echo "Getting Started:"
    echo "  1. Authenticate: gcloud auth application-default login"
    echo "  2. Set project: export GOOGLE_CLOUD_PROJECT=your-project"
    echo "  3. Enable APIs:"
    echo "     gcloud services enable aiplatform.googleapis.com"
    echo "     gcloud services enable discoveryengine.googleapis.com"
    print_help_footer
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "Vertex AI Rerankers & Evaluators" "🔍"

check_env_var "GOOGLE_CLOUD_PROJECT" "" || true

install_deps

genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
