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

# Check if ollama is installed
if ! command -v ollama &> /dev/null; then
  echo "Ollama not found. Installing..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Check if ollama server is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
  echo "Ollama server not running. Starting..."
  ollama serve &
  # Wait for server to be ready
  until curl -s http://localhost:11434/api/tags &> /dev/null; do
    sleep 1
  done
fi

ollama pull nomic-embed-text
ollama pull phi4:latest

genkit start -- \
  uv tool run --from watchdog watchmedo auto-restart \
    -d src \
    -d ../../packages \
    -d ../../plugins \
    -p '*.py;*.prompt;*.json' \
    -R \
    -- uv run src/main.py "$@"
