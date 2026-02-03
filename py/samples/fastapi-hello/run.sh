#!/bin/bash
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

set -e
cd "$(dirname "$0")"
source ../_common.sh

check_api_key "GEMINI_API_KEY"

echo "Starting FastAPI BugBot with Genkit Dev UI..."
echo "API: http://localhost:8080"
echo "Dev UI: http://localhost:4000"
echo ""

genkit start -- uv run src/main.py
