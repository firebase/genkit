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

#!/bin/bash
# Simple wrapper script for Claude Desktop MCP integration

# Set up Go environment automatically
export GOMODCACHE="$HOME/go/pkg/mod"
export GOPATH="$HOME/go"
export GOCACHE="$HOME/Library/Caches/go-build"

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the correct directory and run the server
cd "$SCRIPT_DIR"
/usr/local/go/bin/go run server.go 