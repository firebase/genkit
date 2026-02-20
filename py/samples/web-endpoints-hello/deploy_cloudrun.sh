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

# Deploy to Google Cloud Run
# ==========================
#
# Builds the container from source using Cloud Build and deploys it to
# Cloud Run. Cloud Run sets the PORT env var automatically and auto-scales
# to zero when idle.
#
# Usage:
#   ./deploy_cloudrun.sh                          # Interactive setup
#   ./deploy_cloudrun.sh --project=my-project     # Explicit project
#   ./deploy_cloudrun.sh --region=europe-west1    # Non-default region

set -euo pipefail

cd "$(dirname "$0")"
source "$(dirname "$0")/scripts/_common.sh"

SERVICE_NAME="genkit-asgi"
REGION="${REGION:-us-central1}"
PROJECT=""

# Parse arguments.
for arg in "$@"; do
  case "$arg" in
    --project=*) PROJECT="${arg#*=}" ;;
    --region=*) REGION="${arg#*=}" ;;
    --help|-h)
      echo "Usage: ./deploy_cloudrun.sh [--project=PROJECT] [--region=REGION]"
      echo ""
      echo "Environment variables:"
      echo "  GEMINI_API_KEY    Required. Your Gemini API key."
      echo "  REGION            Cloud Run region (default: us-central1)."
      echo ""
      echo "Options:"
      echo "  --project=ID      GCP project ID."
      echo "  --region=REGION   Cloud Run region (overrides REGION env var)."
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

# 4. Enable required APIs.
if [[ -n "$PROJECT" ]]; then
  export GOOGLE_CLOUD_PROJECT="$PROJECT"
fi
REQUIRED_APIS=("run.googleapis.com" "cloudbuild.googleapis.com")
enable_required_apis "${REQUIRED_APIS[@]}" || true

# ── Deploy ─────────────────────────────────────────────────────────────

PROJECT_FLAG=""
if [[ -n "$PROJECT" ]]; then
  PROJECT_FLAG="--project=${PROJECT}"
fi

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
echo ""

# Cloud Build expects "Dockerfile" and ".dockerignore". Create temporary
# symlinks so `gcloud run deploy --source .` finds our Containerfile.
_CLEANUP_SYMLINKS=""
if [[ -f Containerfile && ! -f Dockerfile ]]; then
  ln -s Containerfile Dockerfile
  _CLEANUP_SYMLINKS=true
fi
if [[ -f .containerignore && ! -f .dockerignore ]]; then
  ln -s .containerignore .dockerignore
  _CLEANUP_SYMLINKS=true
fi
trap 'if [[ "${_CLEANUP_SYMLINKS}" == "true" ]]; then rm -f Dockerfile .dockerignore; fi' EXIT

# Deploy from source — Cloud Build creates the container image.
# shellcheck disable=SC2086
gcloud run deploy "${SERVICE_NAME}" \
  ${PROJECT_FLAG} \
  --source . \
  --region "${REGION}" \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 512Mi \
  --cpu 1

echo ""
echo "✅ Deployed! Get the URL with:"
# shellcheck disable=SC2086
echo "   gcloud run services describe ${SERVICE_NAME} ${PROJECT_FLAG} --region ${REGION} --format 'value(status.url)'"
