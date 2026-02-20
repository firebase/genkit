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

# Deploy to Google App Engine (Flex)
# ===================================
#
# Uses the app.yaml in this directory to deploy a custom runtime (Containerfile)
# to App Engine Flex. App Engine sets the PORT env var automatically.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GEMINI_API_KEY set in your environment
#   - A GCP project with App Engine enabled (gcloud app create --region=us-central)
#
# Usage:
#   ./deploy_appengine.sh                        # Interactive project selection
#   ./deploy_appengine.sh --project=my-project   # Explicit project

set -euo pipefail

cd "$(dirname "$0")"
source "$(dirname "$0")/scripts/_common.sh"

PROJECT=""

# Parse arguments.
for arg in "$@"; do
  case "$arg" in
    --project=*) PROJECT="${arg#*=}" ;;
    --help|-h)
      echo "Usage: ./deploy_appengine.sh [--project=PROJECT]"
      echo ""
      echo "Environment variables:"
      echo "  GEMINI_API_KEY    Required. Your Gemini API key."
      echo ""
      echo "Options:"
      echo "  --project=ID      GCP project ID."
      exit 0
      ;;
  esac
done

# ── Prerequisites ──────────────────────────────────────────────────────

# 1. Check gcloud CLI is installed.
check_gcloud_installed || exit 1

# 2. Check authentication.
check_gcloud_auth || exit 1

# 3. Check GEMINI_API_KEY (interactive prompt if missing).
check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/apikey" || exit 1

# Build project flag.
PROJECT_FLAG=""
if [[ -n "$PROJECT" ]]; then
  PROJECT_FLAG="--project=${PROJECT}"
fi

# App Engine Flex expects a file named "Dockerfile". Create a temporary
# symlink so `gcloud app deploy` finds our Containerfile.
_CLEANUP_DOCKERFILE=""
if [[ -f Containerfile && ! -f Dockerfile ]]; then
  ln -s Containerfile Dockerfile
  _CLEANUP_DOCKERFILE=true
fi
trap 'if [[ "${_CLEANUP_DOCKERFILE}" == "true" ]]; then rm -f Dockerfile; fi' EXIT

echo "🚀 Deploying to App Engine Flex..."
echo ""

# App Engine doesn't support --set-env-vars on `gcloud app deploy`.
# Instead, we append the env var to a temporary copy of app.yaml.
# For production, use Secret Manager instead of plaintext env vars.
TEMP_YAML=$(mktemp)
trap 'rm -f "$TEMP_YAML"' EXIT

cp app.yaml "$TEMP_YAML"
cat >> "$TEMP_YAML" <<EOF

# Auto-injected by deploy_appengine.sh — use Secret Manager for production.
env_variables:
  GEMINI_API_KEY: "${GEMINI_API_KEY}"
EOF

echo "⚠️  GEMINI_API_KEY is set via env_variables in app.yaml."
echo "   For production, use Secret Manager instead:"
echo "   https://cloud.google.com/appengine/docs/flexible/reference/app-yaml#secrets"
echo ""

# Deploy using the temporary app.yaml with env vars injected.
# shellcheck disable=SC2086
gcloud app deploy "$TEMP_YAML" \
  ${PROJECT_FLAG} \
  --quiet

echo ""
echo "✅ Deployed! View your app:"
# shellcheck disable=SC2086
echo "   gcloud app browse ${PROJECT_FLAG}"
