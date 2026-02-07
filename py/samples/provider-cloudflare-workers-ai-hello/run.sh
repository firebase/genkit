#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common utilities if available
if [[ -f "${SCRIPT_DIR}/../_common.sh" ]]; then
    source "${SCRIPT_DIR}/../_common.sh"
fi

# Prompt for required environment variables
if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    echo "CLOUDFLARE_ACCOUNT_ID is not set."
    echo "Get your Account ID from: https://dash.cloudflare.com/"
    read -p "Enter your Cloudflare Account ID: " CLOUDFLARE_ACCOUNT_ID
    export CLOUDFLARE_ACCOUNT_ID
fi

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    echo "CLOUDFLARE_API_TOKEN is not set."
    echo "Create an API token at: https://dash.cloudflare.com/profile/api-tokens"
    read -p "Enter your Cloudflare API Token: " CLOUDFLARE_API_TOKEN
    export CLOUDFLARE_API_TOKEN
fi

echo "Starting CF AI Hello sample..."
echo "Using Account ID: ${CLOUDFLARE_ACCOUNT_ID:0:8}..."

cd "${SCRIPT_DIR}"

genkit start -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
