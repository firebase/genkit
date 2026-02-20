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

# Eject this sample from the Genkit monorepo into a standalone project.
#
# What it does:
#   1. Pins all genkit* dependencies in pyproject.toml to a release version
#   2. Updates CI workflow working-directory from monorepo path to "."
#   3. Updates the project name (optional, via --name)
#   4. Fixes monorepo-specific paths (e.g. pyright venvPath) to standalone values
#   5. Removes the workspace lockfile reference and generates a fresh one
#
# Usage:
#   ./scripts/eject.sh                     # Pin to latest PyPI version
#   ./scripts/eject.sh --version 0.5.0     # Pin to a specific version
#   ./scripts/eject.sh --name my-project   # Also rename the project
#   ./scripts/eject.sh --dry-run           # Show what would change

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GENKIT_VERSION=""
PROJECT_NAME=""
DRY_RUN=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Eject this sample from the Genkit monorepo into a standalone project."
    echo ""
    echo "Options:"
    echo "  --version VERSION   Pin genkit dependencies to VERSION (default: auto-detect from PyPI)"
    echo "  --name NAME         Rename the project in pyproject.toml"
    echo "  --dry-run           Show what would change without modifying files"
    echo "  --help              Show this help message"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version) GENKIT_VERSION="$2"; shift 2 ;;
        --name)    PROJECT_NAME="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help)    usage ;;
        *)         echo "Unknown option: $1"; usage ;;
    esac
done

# Auto-detect version from the monorepo (if inside it) or PyPI.
if [[ -z "$GENKIT_VERSION" ]]; then
    # Try monorepo first (most accurate during development).
    mono_toml="${PROJECT_DIR}/../../packages/genkit/pyproject.toml"
    if [[ -f "$mono_toml" ]]; then
        GENKIT_VERSION=$(grep '^version' "$mono_toml" | head -1 | sed 's/.*= *"//' | sed 's/".*//')
        echo -e "${BLUE}Detected genkit version from monorepo: ${GREEN}${GENKIT_VERSION}${NC}"
    else
        # Fall back to PyPI.
        GENKIT_VERSION=$(pip index versions genkit 2>/dev/null \
            | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)
        if [[ -n "$GENKIT_VERSION" ]]; then
            echo -e "${BLUE}Detected latest genkit version from PyPI: ${GREEN}${GENKIT_VERSION}${NC}"
        else
            echo -e "${RED}Could not detect genkit version. Use --version to specify.${NC}"
            exit 1
        fi
    fi
fi

PIN=">=${GENKIT_VERSION}"
echo ""
echo -e "${BLUE}Ejecting with genkit${PIN}${NC}"
echo ""

changes=0

# 1. Pin genkit* dependencies in pyproject.toml.
echo -e "${BLUE}[1/5] Pinning genkit dependencies in pyproject.toml${NC}"
TOML="${PROJECT_DIR}/pyproject.toml"

# Match lines like:  "genkit",  or  "genkit-plugin-google-genai"  (no version)
# and add the version pin.  Lines that already have >= are left alone.
pin_deps() {
    local file="$1"
    local pin="$2"
    local tmpfile
    tmpfile=$(mktemp)
    local in_deps=false

    while IFS= read -r line; do
        # Track whether we're inside a dependency section.
        # Dependency sections start with "dependencies = [" or have keys like
        # aws = [, gcp = [, etc. inside [project.optional-dependencies].
        if echo "$line" | grep -qE '^\[project\]|^\[project\.optional-dependencies\]'; then
            in_deps=true
        elif echo "$line" | grep -qE '^\[tool\.' ; then
            in_deps=false
        fi

        # Only pin lines that are inside dependency sections and match
        # "genkit" or "genkit-plugin-*" WITHOUT an existing version pin.
        if [[ "$in_deps" == true ]] && \
           echo "$line" | grep -qE '"genkit(-plugin-[a-z-]+)?"' && \
           ! echo "$line" | grep -qE '>='; then
            line=$(echo "$line" | sed -E "s/\"(genkit(-plugin-[a-z-]+)?)\"/\"\1${pin}\"/g")
            echo -e "  ${GREEN}→${NC} $line"
            changes=$((changes + 1))
        fi
        echo "$line" >> "$tmpfile"
    done < "$file"

    if [[ "$DRY_RUN" == false ]]; then
        mv "$tmpfile" "$file"
    else
        rm -f "$tmpfile"
    fi
}

pin_deps "$TOML" "$PIN"

# 2. Update CI workflow working-directory.
echo ""
echo -e "${BLUE}[2/5] Updating GitHub Actions working-directory${NC}"
MONOREPO_WD="py/samples/web-endpoints-hello"

for wf in "${PROJECT_DIR}"/.github/workflows/*.yml; do
    if [[ ! -f "$wf" ]]; then continue; fi
    if grep -q "$MONOREPO_WD" "$wf"; then
        echo -e "  ${GREEN}→${NC} $(basename "$wf"): ${MONOREPO_WD} → ."
        changes=$((changes + 1))
        if [[ "$DRY_RUN" == false ]]; then
            sed -i.bak "s|${MONOREPO_WD}|.|g" "$wf"
            rm -f "${wf}.bak"
        fi
    fi
done

# 3. Rename the project (optional).
if [[ -n "$PROJECT_NAME" ]]; then
    echo ""
    echo -e "${BLUE}[3/5] Renaming project to ${GREEN}${PROJECT_NAME}${NC}"
    OLD_NAME=$(grep '^name' "$TOML" | head -1 | sed 's/.*= *"//' | sed 's/".*//')
    if [[ "$OLD_NAME" != "$PROJECT_NAME" ]]; then
        echo -e "  ${GREEN}→${NC} name: ${OLD_NAME} → ${PROJECT_NAME}"
        changes=$((changes + 1))
        if [[ "$DRY_RUN" == false ]]; then
            sed -i.bak "s/^name = \"${OLD_NAME}\"/name = \"${PROJECT_NAME}\"/" "$TOML"
            rm -f "${TOML}.bak"
        fi
    else
        echo "  (already ${PROJECT_NAME})"
    fi
else
    echo ""
    echo -e "${BLUE}[3/5] Project name${NC} (unchanged — use --name to rename)"
fi

# 4. Fix monorepo-specific paths in pyproject.toml.
echo ""
echo -e "${BLUE}[4/5] Fixing monorepo-specific paths${NC}"
# Pyright venvPath points to "../../" inside the monorepo; standalone needs ".".
if grep -q 'venvPath.*"\.\./\.\."' "$TOML"; then
    echo -e "  ${GREEN}→${NC} pyright venvPath: ../.. → ."
    changes=$((changes + 1))
    if [[ "$DRY_RUN" == false ]]; then
        sed -i.bak 's|venvPath.*=.*"\.\./\.\."|venvPath               = "."|' "$TOML"
        rm -f "${TOML}.bak"
    fi
fi

# 5. Regenerate the lockfile.
echo ""
echo -e "${BLUE}[5/5] Regenerating lockfile${NC}"
if [[ "$DRY_RUN" == false ]]; then
    # Remove stale workspace lockfile reference if present.
    rm -f "${PROJECT_DIR}/uv.lock"
    (cd "$PROJECT_DIR" && uv lock 2>&1) || {
        echo -e "${YELLOW}uv lock failed — you may need to install uv or fix dependency versions.${NC}"
        echo "  Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    }
    echo -e "  ${GREEN}→${NC} uv.lock regenerated"
    changes=$((changes + 1))
else
    echo "  (skipped in --dry-run)"
fi

# Summary.
echo ""
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Dry run complete — ${changes} change(s) would be made.${NC}"
    echo "Run without --dry-run to apply."
else
    echo -e "${GREEN}Ejected! ${changes} change(s) applied.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. cd $(basename "$PROJECT_DIR")"
    echo "  2. uv sync"
    echo "  3. export GEMINI_API_KEY=<your-key>"
    echo "  4. ./run.sh"
fi
