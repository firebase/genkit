#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# AWS Bedrock Hello World Demo
# ============================
#
# Demonstrates usage of AWS Bedrock models with Genkit.
#
# Prerequisites:
#   - AWS credentials configured (env vars, credentials file, or IAM role)
#   - AWS_REGION environment variable set
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

print_help() {
    print_banner "AWS Bedrock Hello World" "☁️"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_REGION              Required. AWS region (e.g., us-east-1)"
    echo "  AWS_ACCESS_KEY_ID       AWS access key ID (or use credentials file)"
    echo "  AWS_SECRET_ACCESS_KEY   AWS secret access key (or use credentials file)"
    echo "  AWS_PROFILE             AWS profile name from credentials file"
    echo ""
    echo "Setup Guide: https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html"
    print_help_footer
}

case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

print_banner "AWS Bedrock Hello World" "☁️"

check_env_var "AWS_REGION" "https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html" || true

install_deps

genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
