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

# Deploy via Firebase Hosting + Cloud Run
# ========================================
#
# This script:
#   1. Deploys the Genkit FastAPI app to Cloud Run
#   2. Creates a firebase.json with rewrites that proxy all traffic
#      from Firebase Hosting to the Cloud Run service
#   3. Deploys Firebase Hosting
#
# The result is a Firebase-hosted URL (e.g. https://project.web.app)
# that proxies API requests to your Cloud Run-deployed FastAPI app.
#
# This is the recommended workaround for Python Genkit apps since
# firebase-functions-python does not yet support onCallGenkit.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - firebase CLI installed (npm install -g firebase-tools)
#   - GEMINI_API_KEY set in your environment
#   - A Firebase project linked to a GCP project
#
# Usage:
#   ./deploy_firebase_hosting.sh --project=my-project
#   ./deploy_firebase_hosting.sh --project=my-project --region=europe-west1

set -euo pipefail

cd "$(dirname "$0")"

SERVICE_NAME="genkit-asgi"
REGION="${REGION:-us-central1}"
PROJECT=""

# Parse arguments.
for arg in "$@"; do
  case "$arg" in
    --project=*) PROJECT="${arg#*=}" ;;
    --region=*) REGION="${arg#*=}" ;;
    --help|-h)
      echo "Usage: ./deploy_firebase_hosting.sh --project=PROJECT [--region=REGION]"
      echo ""
      echo "Environment variables:"
      echo "  GEMINI_API_KEY    Required. Your Gemini API key."
      echo "  REGION            Cloud Run region (default: us-central1)."
      echo ""
      echo "Options:"
      echo "  --project=ID      Firebase/GCP project ID (required)."
      echo "  --region=REGION   Cloud Run region."
      exit 0
      ;;
  esac
done

# Validate required inputs.
if [[ -z "$PROJECT" ]]; then
  echo "ERROR: --project is required."
  echo "Usage: ./deploy_firebase_hosting.sh --project=my-project"
  exit 1
fi

# ── Prerequisites ──────────────────────────────────────────────────────

# 1. Check gcloud CLI is installed.
check_gcloud_installed || exit 1

# 2. Check authentication.
check_gcloud_auth || exit 1

# 3. Check GEMINI_API_KEY (interactive prompt if missing).
check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/apikey" || exit 1

# 4. Check for firebase CLI.
if ! command -v firebase &> /dev/null; then
  echo -e "${YELLOW}firebase CLI not found.${NC}"
  echo "Install it: npm install -g firebase-tools"
  exit 1
fi

echo "🚀 Step 1/2: Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
echo ""

# Deploy the app to Cloud Run first.
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT}" \
  --source . \
  --region "${REGION}" \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 512Mi \
  --cpu 1

echo ""
echo "🚀 Step 2/2: Deploying Firebase Hosting with Cloud Run proxy..."
echo ""

# Create a minimal firebase.json that proxies all requests to Cloud Run.
# Using a temp directory so we don't pollute the sample with hosting artifacts.
HOSTING_DIR=$(mktemp -d)
trap 'rm -rf "$HOSTING_DIR"' EXIT

mkdir -p "${HOSTING_DIR}/public"
echo '<!DOCTYPE html><html><body>Redirecting...</body></html>' > "${HOSTING_DIR}/public/index.html"

cat > "${HOSTING_DIR}/firebase.json" << EOF
{
  "hosting": {
    "public": "public",
    "rewrites": [
      {
        "source": "**",
        "run": {
          "serviceId": "${SERVICE_NAME}",
          "region": "${REGION}"
        }
      }
    ]
  }
}
EOF

firebase deploy \
  --only hosting \
  --project "${PROJECT}" \
  --config "${HOSTING_DIR}/firebase.json" \
  --public "${HOSTING_DIR}/public"

echo ""
echo "✅ Deployed! Your app is available at:"
echo "   https://${PROJECT}.web.app"
echo ""
echo "   Cloud Run:        gcloud run services describe ${SERVICE_NAME} --project ${PROJECT} --region ${REGION} --format 'value(status.url)'"
echo "   Firebase Hosting: https://${PROJECT}.web.app"
