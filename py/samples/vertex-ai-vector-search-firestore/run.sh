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

# Check for required environment variables
required_vars="LOCATION PROJECT_ID FIRESTORE_COLLECTION VECTOR_SEARCH_DEPLOYED_INDEX_ID VECTOR_SEARCH_INDEX_ENDPOINT_PATH VECTOR_SEARCH_API_ENDPOINT"
missing_vars=""
for var in $required_vars; do
  if [ -z "${!var}" ]; then
    missing_vars="$missing_vars $var"
  fi
done

if [ -n "$missing_vars" ]; then
  echo "ERROR: Missing required environment variables:$missing_vars"
  echo "See README.md for setup instructions."
  exit 1
fi

# Check for gcloud ADC
if ! gcloud auth application-default print-access-token &>/dev/null; then
  echo "WARNING: gcloud ADC not configured."
  echo "Run: gcloud auth application-default login"
fi

genkit start -- uv run src/main.py "$@"
