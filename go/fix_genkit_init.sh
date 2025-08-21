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

# Script to fix genkit.Init usage across the Go codebase

echo "Fixing genkit.Init usage patterns..."

# Find all .go files that have the old pattern and fix them
find . -name "*.go" -type f -exec grep -l "g, err := genkit\.Init" {} \; | while read file; do
    echo "Fixing $file..."
    
    # Fix the assignment pattern - handle multi-line cases
    sed -i.bak -E '/g, err := genkit\.Init/{
        N
        N
        N
        N
        N
        s/g, err := genkit\.Init([^)]*\))\n[[:space:]]*if err != nil \{[[:space:]]*\n[[:space:]]*log\.Fatal[^}]*\}/g := genkit.Init\1/
    }' "$file"
    
    # Simpler pattern for single line cases
    sed -i.bak2 's/g, err := genkit\.Init(/g := genkit.Init(/g' "$file"
    
    # Remove unused log imports if the file no longer has log.Fatal calls
    if ! grep -q "log\." "$file"; then
        sed -i.bak3 '/^[[:space:]]*"log"[[:space:]]*$/d' "$file"
    fi
    
    # Clean up backup files
    rm -f "$file.bak" "$file.bak2" "$file.bak3"
done

echo "Done!"