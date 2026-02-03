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


cd "$(dirname "$0")"
source "../_common.sh"

print_help() {
    print_banner "MCP Sample" "🔌"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GOOGLE_GENAI_API_KEY    Required. Your Gemini API key"
    print_help_footer
}

# Parse arguments
case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
esac

# Main execution
print_banner "MCP Sample" "🔌"

check_env_var "GOOGLE_GENAI_API_KEY" "https://makersuite.google.com/app/apikey" || true
# Also check for uvx/pnpm logic if needed, but not strictly required for Dev UI start

install_deps

# Start with hot reloading and auto-open browser
# Using exec to ensure signals are passed correctly
genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
