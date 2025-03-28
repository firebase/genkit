#!/bin/bash
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

set -e

cd /home/ihan/github.com/firebase/genkit

# Backup current changes
git add .
git stash

# Create a new branch from main
git checkout firebase/main -b ivenh/2240-new

# Apply stashed changes
git stash pop || true

# Resolve each conflict with --ours (our changes)
git checkout --ours go/ai/prompt.go
git checkout --ours go/ai/prompt_test.go
git checkout --ours go/go.mod
git checkout --ours go/go.sum
git checkout --ours go/internal/registry/registry.go
git checkout --ours py/bin/sanitize_schema_typing.py
git checkout --ours py/packages/aioia/src/aioia/__init__.py
git checkout --ours py/packages/aioia/src/aioia/servers/middleware/__init__.py
git checkout --ours py/packages/aioia/src/aioia/servers/middleware/_logging.py
git checkout --ours py/plugins/chroma/src/genkit/plugins/chroma/__init__.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/__init__.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/models/__init__.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/models/handler.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/models/model.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/models/model_info.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/openai_plugin.py
git checkout --ours py/plugins/compat-oai/src/genkit/plugins/compat_oai/typing.py
git checkout --ours py/plugins/compat-oai/tests/conftest.py
git checkout --ours py/plugins/compat-oai/tests/test_handler.py
git checkout --ours py/plugins/compat-oai/tests/test_model.py
git checkout --ours py/plugins/compat-oai/tests/test_plugin.py
git checkout --ours py/plugins/firebase/src/genkit/plugins/firebase/__init__.py
git checkout --ours py/plugins/google-ai/src/genkit/plugins/google_ai/__init__.py
git checkout --ours py/plugins/google-ai/src/genkit/plugins/google_ai/google_ai.py
git checkout --ours py/plugins/google-ai/src/genkit/plugins/google_ai/models/__init__.py

# Add all resolved files
git add .

# Commit the changes
git commit -m "fix(go/ai): DefinePartial, DefineHelper, and registry improvements"

# Push the changes
git push -f origin ivenh/2240-new 