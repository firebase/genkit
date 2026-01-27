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

# Check for GCP project
if [ -z "$GCLOUD_PROJECT" ] && [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
  PROJECT=$(gcloud config get-value project 2>/dev/null)
  if [ -z "$PROJECT" ]; then
    echo "ERROR: No GCP project configured."
    echo "Please set GCLOUD_PROJECT or run: gcloud config set project <your-project>"
    exit 1
  fi
  export GCLOUD_PROJECT="$PROJECT"
fi

# Check for gcloud ADC
if ! gcloud auth application-default print-access-token &>/dev/null; then
  echo "WARNING: gcloud ADC not configured."
  echo "Run: gcloud auth application-default login"
fi

echo "NOTE: Ensure Firestore index is created. See README.md for details."

genkit start -- \
  uv tool run --from watchdog watchmedo auto-restart \
    -d src \
    -d ../../packages \
    -d ../../plugins \
    -p '*.py;*.prompt;*.json' \
    -R \
    -- uv run src/main.py "$@"
