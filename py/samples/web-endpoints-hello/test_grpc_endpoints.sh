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

# gRPC integration tests — exercises all gRPC endpoints with grpcurl.
#
# Prerequisites:
#   - grpcurl:
#       macOS:  brew install grpcurl
#       Linux:  go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
#               or download from https://github.com/fullstorydev/grpcurl/releases
#   - grpcui (optional):
#       macOS:  brew install grpcui
#       Linux:  go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
#
# Usage:
#   1. Start the server:  ./run.sh
#   2. In another terminal: ./test_grpc_endpoints.sh
#
# The gRPC server must be running on localhost:50051 (default).
# Override with: GRPC_ADDR=localhost:50052 ./test_grpc_endpoints.sh
#
# To explore interactively with the gRPC web UI:
#   grpcui -plaintext localhost:50051

set -euo pipefail

GRPC_ADDR="${GRPC_ADDR:-localhost:50051}"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

# ── Check prerequisites ──────────────────────────────────────────────

if ! command -v grpcurl &>/dev/null; then
    echo -e "${RED}Error: grpcurl is not installed.${NC}"
    echo ""
    echo "Install it:"
    echo "  brew install grpcurl                                            # macOS"
    echo "  go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest  # Linux (Go)"
    echo "  ./setup.sh                                                     # auto-installs"
    echo ""
    echo "Or download a prebuilt binary:"
    echo "  https://github.com/fullstorydev/grpcurl/releases"
    exit 1
fi

# ── Test infrastructure ──────────────────────────────────────────────

PASS=0
FAIL=0
TOTAL=0

run_grpc_test() {
    local label="$1"
    local method="$2"
    shift 2
    local data="${1:-}"

    TOTAL=$((TOTAL + 1))
    local start_time end_time elapsed

    start_time=$(date +%s)

    local cmd_args=(-plaintext -max-time 60)
    if [[ -n "$data" ]]; then
        cmd_args+=(-d "$data")
    fi

    local output
    if output=$(grpcurl "${cmd_args[@]}" "$GRPC_ADDR" "$method" 2>&1); then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo -e "${GREEN}✓ PASS${NC} ${CYAN}${label}${NC} ${DIM}(${elapsed}s)${NC}"
        PASS=$((PASS + 1))
    else
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo -e "${RED}✗ FAIL${NC} ${CYAN}${label}${NC} ${DIM}(${elapsed}s)${NC}"
        echo -e "  ${DIM}${output:0:200}${NC}"
        FAIL=$((FAIL + 1))
    fi
}

run_grpc_stream_test() {
    local label="$1"
    local method="$2"
    shift 2
    local data="${1:-}"

    TOTAL=$((TOTAL + 1))
    local start_time end_time elapsed

    start_time=$(date +%s)

    local cmd_args=(-plaintext -max-time 60)
    if [[ -n "$data" ]]; then
        cmd_args+=(-d "$data")
    fi

    local output
    if output=$(grpcurl "${cmd_args[@]}" "$GRPC_ADDR" "$method" 2>&1); then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        # Check that we got some streaming output (multiple JSON objects).
        if echo "$output" | grep -q '"text"'; then
            echo -e "${GREEN}✓ PASS${NC} ${CYAN}${label}${NC} ${DIM}(${elapsed}s, streaming)${NC}"
            PASS=$((PASS + 1))
        else
            echo -e "${RED}✗ FAIL${NC} ${CYAN}${label}${NC} ${DIM}(${elapsed}s, no stream chunks)${NC}"
            echo -e "  ${DIM}${output:0:200}${NC}"
            FAIL=$((FAIL + 1))
        fi
    else
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo -e "${RED}✗ FAIL${NC} ${CYAN}${label}${NC} ${DIM}(${elapsed}s)${NC}"
        echo -e "  ${DIM}${output:0:200}${NC}"
        FAIL=$((FAIL + 1))
    fi
}

# ── Verify server is reachable ───────────────────────────────────────

echo "Testing gRPC endpoints at: ${GRPC_ADDR}"
echo ""

# Quick connectivity check via reflection.
if ! grpcurl -plaintext -max-time 5 "$GRPC_ADDR" list &>/dev/null; then
    echo -e "${RED}Error: Cannot connect to gRPC server at ${GRPC_ADDR}${NC}"
    echo ""
    echo "Make sure the server is running:"
    echo "  ./run.sh"
    echo ""
    echo "Or check the gRPC port:"
    echo "  GRPC_ADDR=localhost:50052 ./test_grpc_endpoints.sh"
    exit 1
fi

echo -e "${GREEN}✓ Connected to gRPC server (reflection enabled)${NC}"
echo ""

# List available services.
echo -e "${CYAN}Available services:${NC}"
grpcurl -plaintext "$GRPC_ADDR" list
echo ""

echo "Running tests:"
echo "======================================================="

# ── Fire tests ───────────────────────────────────────────────────────

run_grpc_test \
    "Health check" \
    "genkit.sample.v1.GenkitService/Health" \
    '{}'

run_grpc_test \
    "TellJoke (default)" \
    "genkit.sample.v1.GenkitService/TellJoke" \
    '{}'

run_grpc_test \
    "TellJoke (custom name)" \
    "genkit.sample.v1.GenkitService/TellJoke" \
    '{"name": "Waffles", "username": "Alice"}'

run_grpc_test \
    "TranslateText" \
    "genkit.sample.v1.GenkitService/TranslateText" \
    '{"text": "Hello, how are you?", "target_language": "Japanese"}'

run_grpc_test \
    "DescribeImage" \
    "genkit.sample.v1.GenkitService/DescribeImage" \
    '{}'

run_grpc_test \
    "GenerateCharacter" \
    "genkit.sample.v1.GenkitService/GenerateCharacter" \
    '{"name": "Luna"}'

run_grpc_test \
    "PirateChat" \
    "genkit.sample.v1.GenkitService/PirateChat" \
    '{"question": "What is Python?"}'

run_grpc_stream_test \
    "TellStory (server streaming)" \
    "genkit.sample.v1.GenkitService/TellStory" \
    '{"topic": "a robot learning to paint"}'

run_grpc_test \
    "GenerateCode" \
    "genkit.sample.v1.GenkitService/GenerateCode" \
    '{"description": "a function that checks if a number is prime", "language": "python"}'

run_grpc_test \
    "ReviewCode (Dotprompt)" \
    "genkit.sample.v1.GenkitService/ReviewCode" \
    '{"code": "def add(a, b):\n    return a + b", "language": "python"}'

# ── Summary ──────────────────────────────────────────────────────────

echo ""
echo "=================================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC} (${TOTAL} total)"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi

echo ""
echo -e "${DIM}Tip: Explore interactively with the gRPC web UI:${NC}"
echo -e "  ${CYAN}grpcui -plaintext ${GRPC_ADDR}${NC}"
