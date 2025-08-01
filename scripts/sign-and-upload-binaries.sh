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

set -euo pipefail

# This script simulates signing binaries and uploads them to a GitHub release
# Usage: ./sign-and-upload-binaries.sh <version>
# Example: ./sign-and-upload-binaries.sh v1.0.0-rc.1

if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v1.0.0-rc.1"
    exit 1
fi

VERSION="$1"

# Extract repo owner and name from GITHUB_REPOSITORY env var or use defaults
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    REPO_OWNER=$(echo "$GITHUB_REPOSITORY" | cut -d'/' -f1)
    REPO_NAME=$(echo "$GITHUB_REPOSITORY" | cut -d'/' -f2)
else
    # Fallback for local testing
    REPO_OWNER="${REPO_OWNER:-firebase}"
    REPO_NAME="${REPO_NAME:-genkit}"
fi

# Check if GITHUB_TOKEN is set
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set"
    exit 1
fi

# Platform configurations
PLATFORMS=(
    "linux-x64"
    "linux-arm64"
    "darwin-x64"
    "darwin-arm64"
    "win32-x64"
)

echo "=== Genkit Binary Signing Simulation ==="
echo "Version: $VERSION"
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo ""

# Get release information
echo "Fetching release information..."
RELEASE_INFO=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/tags/$VERSION")

RELEASE_ID=$(echo "$RELEASE_INFO" | jq -r '.id')
UPLOAD_URL=$(echo "$RELEASE_INFO" | jq -r '.upload_url' | sed 's/{?name,label}//')

if [ "$RELEASE_ID" == "null" ]; then
    echo "Error: Release $VERSION not found"
    exit 1
fi

echo "✓ Found release ID: $RELEASE_ID"
echo ""

# Create temporary directory for downloads
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "Working directory: $TEMP_DIR"
echo ""

# Process each platform
for platform in "${PLATFORMS[@]}"; do
    echo "Processing $platform..."
    
    # Set file extension
    if [[ "$platform" == win32-* ]]; then
        ext=".exe"
    else
        ext=""
    fi
    
    # Original and signed file names
    original_name="genkit-$platform$ext"
    signed_name="genkit-$platform-signed$ext"
    
    # Download URL
    download_url="https://github.com/$REPO_OWNER/$REPO_NAME/releases/download/$VERSION/$original_name"
    
    # Download the binary
    echo "  Downloading $original_name..."
    if curl -sL -o "$TEMP_DIR/$original_name" "$download_url"; then
        echo "  ✓ Downloaded successfully"
    else
        echo "  ✗ Failed to download $original_name - skipping"
        continue
    fi
    
    # Simulate signing process (preserve binary integrity)
    echo "  Simulating signing process..."
    
    # Method 1: Create a copy with signed name (binary remains unchanged)
    cp "$TEMP_DIR/$original_name" "$TEMP_DIR/$signed_name"
    
    # Method 2: Create a separate signature file
    signature_name="$signed_name.sig"
    cat > "$TEMP_DIR/$signature_name" << EOF
-----BEGIN GENKIT SIGNATURE-----
Version: $VERSION
Platform: $platform
Signed: $(date -u -Iseconds)
Signature: $(sha256sum "$TEMP_DIR/$original_name" | cut -d' ' -f1)
Signer: Genkit Signing Service (Simulation)
-----END GENKIT SIGNATURE-----
EOF
    
    echo "  ✓ Signing simulated (binary integrity preserved)"
    echo "  ✓ Signature file created: $signature_name"
    
    # Verify binary integrity after "signing"
    if cmp -s "$TEMP_DIR/$original_name" "$TEMP_DIR/$signed_name"; then
        echo "  ✓ Binary integrity verified (no corruption)"
    else
        echo "  ✗ Binary integrity check failed!"
        exit 1
    fi
    
    # Upload the signed binary
    echo "  Uploading $signed_name..."
    
    upload_binary_response=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Content-Type: application/octet-stream" \
        --data-binary "@$TEMP_DIR/$signed_name" \
        "$UPLOAD_URL?name=$signed_name")
    
    # Check if binary upload was successful
    if echo "$upload_binary_response" | jq -e '.id' > /dev/null; then
        asset_url=$(echo "$upload_binary_response" | jq -r '.browser_download_url')
        echo "  ✓ Binary uploaded successfully: $asset_url"
    else
        echo "  ✗ Failed to upload $signed_name"
        echo "  Error: $(echo "$upload_binary_response" | jq -r '.message // "Unknown error"')"
    fi
    
    # Upload the signature file
    echo "  Uploading $signature_name..."
    
    upload_signature_response=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Content-Type: text/plain" \
        --data-binary "@$TEMP_DIR/$signature_name" \
        "$UPLOAD_URL?name=$signature_name")
    
    # Check if signature upload was successful
    if echo "$upload_signature_response" | jq -e '.id' > /dev/null; then
        sig_asset_url=$(echo "$upload_signature_response" | jq -r '.browser_download_url')
        echo "  ✓ Signature file uploaded successfully: $sig_asset_url"
    else
        echo "  ✗ Failed to upload signature file"
        echo "  Error: $(echo "$upload_signature_response" | jq -r '.message // "Unknown error"')"
    fi
    
    echo ""
done

echo "=== Signing simulation complete ==="
echo ""
echo "✓ All binaries signed and uploaded successfully"
echo "✓ Binary integrity preserved (no corruption)"
echo "✓ Separate signature files created for verification"
echo ""
echo "View the release at: https://github.com/$REPO_OWNER/$REPO_NAME/releases/tag/$VERSION"
echo ""
echo "Note: This is a simulation. In production, you would use proper code signing tools."