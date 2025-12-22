#!/bin/bash
# Run script for Genkit MCP Sample

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

cd "$(dirname "$0")"

# Check for OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set."
    echo "Some features may not work without it."
fi

# Set MCP_ALLOWED_DIR if not already set
if [ -z "$MCP_ALLOWED_DIR" ]; then
    export MCP_ALLOWED_DIR="/tmp"
    echo "MCP_ALLOWED_DIR not set, using default: $MCP_ALLOWED_DIR"
fi

mvn exec:java
