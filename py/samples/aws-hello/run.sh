#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# AWS Telemetry Hello World Demo
# ==============================
#
# Demonstrates usage of AWS X-Ray telemetry with Genkit.
#
# Prerequisites:
#   - AWS credentials configured (env vars, credentials file, or IAM role)
#   - AWS_REGION environment variable set
#   - GOOGLE_GENAI_API_KEY for the model provider
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

print_help() {
    print_banner "AWS Telemetry Hello World" "📊"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_REGION              Required. AWS region for X-Ray endpoint"
    echo "  AWS_ACCESS_KEY_ID       AWS access key ID (or use credentials file)"
    echo "  AWS_SECRET_ACCESS_KEY   AWS secret access key (or use credentials file)"
    echo "  AWS_PROFILE             AWS profile name from credentials file"
    echo "  GOOGLE_GENAI_API_KEY    Required. Google AI API key for the model"
    echo ""
    echo "Setup Guides:"
    echo "  AWS X-Ray:     https://docs.aws.amazon.com/xray/"
    echo "  Google AI:     https://aistudio.google.com/app/apikey"
    print_help_footer
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "AWS Telemetry Hello World" "📊"

check_env_var "AWS_REGION" "https://docs.aws.amazon.com/xray/" || true
check_env_var "GOOGLE_GENAI_API_KEY" "https://aistudio.google.com/app/apikey"

install_deps

genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
