#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Firestore Retriever Demo
# ========================
#
# Demonstrates using Firestore as a vector store.
#
# Prerequisites:
#   - GOOGLE_CLOUD_PROJECT environment variable set
#   - gcloud CLI authenticated
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

print_help() {
    print_banner "Firestore Retriever Demo" "🔥"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GOOGLE_CLOUD_PROJECT    Required. Your GCP project ID"
    echo ""
    echo "Getting Started:"
    echo "  1. Authenticate: gcloud auth application-default login"
    echo "  2. Set project: export GOOGLE_CLOUD_PROJECT=your-project"
    echo "  3. Create a Firestore index for vector search (see logs for link)"
    print_help_footer
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "Firestore Retriever Demo" "🔥"

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
