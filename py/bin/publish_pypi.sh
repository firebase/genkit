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

#!/usr/bin/env bash

set -euo pipefail

if ((EUID == 0)); then
  echo "Please do not run as root"
  exit 1
fi

# Navigate to the correct project directory
cd "$PROJECT_TYPE/$PROJECT_NAME"

# Validate new version information
NEW_VERSION=$(toml get pyproject.toml project.version --raw)
PACKAGE_NAME=$(toml get pyproject.toml project.name --raw)

echo "New Version is $NEW_VERSION"
echo "Package Name is $PACKAGE_NAME"

response=$(curl -s "https://pypi.org/pypi/$PACKAGE_NAME/json" || echo "{}")
LATEST_VERSION=$(echo $response | jq --raw-output "select(.releases != null) | .releases | keys_unsorted | last")

if [ -z "$LATEST_VERSION" ]; then
  echo "Package not found on PyPI."
  LATEST_VERSION="0.0.0"
else
  echo "Latest version on PyPI: $LATEST_VERSION"
  if [ "$(printf '%s\n' "$LATEST_VERSION" "$NEW_VERSION" | sort -rV | head -n 1)" != "$NEW_VERSION" ] || [ "$NEW_VERSION" == "$LATEST_VERSION" ]; then
    echo "The new version $NEW_VERSION is not greater than the latest version $LATEST_VERSION on PyPI."
    exit 1
  fi
fi

# Build distributions for the specific project
TOP_DIR=$(git rev-parse --show-toplevel)
uv --directory="${TOP_DIR}/py/$PROJECT_TYPE" --project "$PROJECT_NAME" build

# Validate Twine check
TWINE_CHECK=$(twine check "${TOP_DIR}/py/dist/*")
echo "$TWINE_CHECK"

if echo "$TWINE_CHECK" | grep -q "FAIL"; then
  echo "Twine check failed"
  exit 1
else
  echo "Twine passed"
fi
