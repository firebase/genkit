#!/usr/bin/env bash
# Copyright 2025 Google LLC
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source shared helper utilities.
source "$(dirname "${SCRIPT_DIR}")/_common.sh"

# Prompt for required env vars if not set.
check_env_var "GCLOUD_PROJECT" "" || true
check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/app/apikey" || true

# The Checks API requires specific OAuth scopes. Standard ADC credentials
# (from `gcloud auth application-default login`) don't include the `checks`
# scope, resulting in a 403 ACCESS_TOKEN_SCOPE_INSUFFICIENT error.
CHECKS_SCOPES="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/checks"
CHECKS_API="checks.googleapis.com"

# Verify the Checks API is enabled on the configured GCP project.
ensure_checks_api_enabled() {
    local project="${GCLOUD_PROJECT:-}"
    if [[ -z "$project" ]]; then
        echo -e "${YELLOW}⚠ GCLOUD_PROJECT not set — skipping API enablement check.${NC}"
        return
    fi

    echo -e "${BLUE}Checking if ${CHECKS_API} is enabled on project '${project}'...${NC}"

    if gcloud services list --project="${project}" --filter="config.name:${CHECKS_API}" --format="value(config.name)" 2>/dev/null | grep -q "${CHECKS_API}"; then
        echo -e "${GREEN}✓ ${CHECKS_API} is enabled${NC}"
    else
        echo -e "${YELLOW}✗ ${CHECKS_API} is NOT enabled on project '${project}'.${NC}"
        echo ""
        if [[ -t 0 ]] && [ -c /dev/tty ]; then
            echo -en "Run ${GREEN}gcloud services enable ${CHECKS_API} --project=${project}${NC} now? [Y/n]: "
            local response
            read -r response < /dev/tty
            if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
                echo ""
                gcloud services enable "${CHECKS_API}" --project="${project}"
                echo -e "${GREEN}✓ ${CHECKS_API} enabled${NC}"
            else
                echo -e "${YELLOW}Skipping. The Checks API calls will fail.${NC}"
            fi
        else
            echo "Run: gcloud services enable ${CHECKS_API} --project=${project}"
        fi
    fi
    echo ""
}

# Ensure ADC credentials include the Checks OAuth scope.
ensure_checks_adc() {
    echo -e "${BLUE}Checking ADC credentials for Checks API scopes...${NC}"

    # Try to get an access token; if it fails, we need to login.
    if ! gcloud auth application-default print-access-token &> /dev/null; then
        echo -e "${YELLOW}No Application Default Credentials found.${NC}"
        echo -e "The Checks API requires ADC with specific scopes."
        echo ""
        if [[ -t 0 ]] && [ -c /dev/tty ]; then
            echo -en "Run ${GREEN}gcloud auth application-default login --scopes=${CHECKS_SCOPES}${NC} now? [Y/n]: "
            local response
            read -r response < /dev/tty
            if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
                echo ""
                gcloud auth application-default login --scopes="${CHECKS_SCOPES}"
                echo ""
            else
                echo -e "${YELLOW}Skipping. You may get a 403 scope error.${NC}"
            fi
        else
            echo "Run: gcloud auth application-default login --scopes=${CHECKS_SCOPES}"
        fi
    else
        echo -e "${GREEN}✓ Application Default Credentials found${NC}"
        echo -e "${YELLOW}If you see ACCESS_TOKEN_SCOPE_INSUFFICIENT errors, re-run:${NC}"
        echo -e "${YELLOW}  gcloud auth application-default login --scopes=${CHECKS_SCOPES}${NC}"
    fi
    echo ""
}

ensure_checks_api_enabled
ensure_checks_adc


genkit start -- \
  uv tool run --from watchdog watchmedo auto-restart \
    -d src \
    -d ../../packages \
    -d ../../plugins \
    -p '*.py;*.prompt;*.json' \
    -R \
    -- uv run src/main.py "$@"
