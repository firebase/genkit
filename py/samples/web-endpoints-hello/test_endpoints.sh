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

# Integration test script — exercises all endpoints with curl in parallel.
#
# Usage:
#   1. Start the server:  ./run.sh
#   2. In another terminal: ./test_endpoints.sh
#
# All requests fire in parallel and results print as they arrive.
# Set BASE_URL to test against a deployed instance:
#   BASE_URL=https://my-app.run.app ./test_endpoints.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
RESULTS_DIR=$(mktemp -d)
trap 'rm -rf "$RESULTS_DIR"' EXIT

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

# --- Output strategy -------------------------------------------------------
# With flock: background jobs print results directly (instant, no interleave).
# Without flock: jobs write to files, a foreground loop polls and prints.
#
# flock ships with util-linux on Linux. On macOS: brew install flock

LOCKFILE="${RESULTS_DIR}/.lock"
HAS_FLOCK=false

if command -v flock &>/dev/null; then
  HAS_FLOCK=true
elif [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
  echo -e "${DIM}Installing flock via Homebrew for clean output...${NC}"
  if brew install flock &>/dev/null; then
    HAS_FLOCK=true
  fi
fi

TOTAL_TESTS=0

# --- Shared helpers --------------------------------------------------------

format_pass() {
  local label="$1" status="$2" elapsed="$3"
  echo -e "${GREEN}✓ PASS${NC} ${CYAN}${label}${NC} ${DIM}(HTTP ${status}, ${elapsed}s)${NC}"
}

format_fail() {
  local label="$1" status="$2" elapsed="$3" body="$4"
  echo -e "${RED}✗ FAIL${NC} ${CYAN}${label}${NC} ${DIM}(HTTP ${status}, ${elapsed}s)${NC}"
  echo -e "  ${DIM}${body:0:200}${NC}"
}

# --- flock strategy: print from background jobs ----------------------------

if $HAS_FLOCK; then

PASS_FILE="${RESULTS_DIR}/.pass"
FAIL_FILE="${RESULTS_DIR}/.fail"
echo 0 > "$PASS_FILE"
echo 0 > "$FAIL_FILE"

emit_result() {
  local label="$1" status="$2" body="$3" elapsed="$4"
  (
    flock 9
    if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
      format_pass "$label" "$status" "$elapsed"
      echo $(( $(cat "$PASS_FILE") + 1 )) > "$PASS_FILE"
    else
      format_fail "$label" "$status" "$elapsed" "$body"
      echo $(( $(cat "$FAIL_FILE") + 1 )) > "$FAIL_FILE"
    fi
  ) 9>"$LOCKFILE"
}

run_test() {
  local label="$1"; shift
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  {
    local start_time end_time elapsed
    start_time=$(date +%s)
    RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 60 "$@" 2>&1)
    end_time=$(date +%s); elapsed=$((end_time - start_time))
    BODY=$(echo "$RESPONSE" | sed '$d')
    STATUS=$(echo "$RESPONSE" | tail -1)
    emit_result "$label" "$STATUS" "$BODY" "$elapsed"
  } &
}

run_stream_test() {
  local label="$1"; shift
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  {
    local start_time end_time elapsed
    start_time=$(date +%s)
    STREAM_OUTPUT=$(curl -s -N --max-time 30 "$@" 2>&1 || true)
    end_time=$(date +%s); elapsed=$((end_time - start_time))
    if echo "$STREAM_OUTPUT" | grep -q '"chunk"'; then
      emit_result "$label" "200" "SSE chunks received" "$elapsed"
    else
      emit_result "$label" "0" "${STREAM_OUTPUT:0:200}" "$elapsed"
    fi
  } &
}

collect_results() {
  wait
  PASS=$(cat "$PASS_FILE")
  FAIL=$(cat "$FAIL_FILE")
}

# --- Polling fallback: write files, print from foreground ------------------

else  # no flock

run_test() {
  local label="$1"; shift
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  local idx="$TOTAL_TESTS"
  {
    local start_time end_time elapsed
    start_time=$(date +%s)
    RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 60 "$@" 2>&1)
    end_time=$(date +%s); elapsed=$((end_time - start_time))
    BODY=$(echo "$RESPONSE" | sed '$d')
    STATUS=$(echo "$RESPONSE" | tail -1)
    # Atomic write: tmp then rename.
    printf '%s\n%s\n%s\n%s\n' "$label" "$STATUS" "$elapsed" "$BODY" \
      > "${RESULTS_DIR}/${idx}.tmp"
    mv "${RESULTS_DIR}/${idx}.tmp" "${RESULTS_DIR}/${idx}.done"
  } &
}

run_stream_test() {
  local label="$1"; shift
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  local idx="$TOTAL_TESTS"
  {
    local start_time end_time elapsed
    start_time=$(date +%s)
    STREAM_OUTPUT=$(curl -s -N --max-time 30 "$@" 2>&1 || true)
    end_time=$(date +%s); elapsed=$((end_time - start_time))
    if echo "$STREAM_OUTPUT" | grep -q '"chunk"'; then
      printf '%s\n%s\n%s\n%s\n' "$label" "200" "$elapsed" "SSE chunks received" \
        > "${RESULTS_DIR}/${idx}.tmp"
    else
      printf '%s\n%s\n%s\n%s\n' "$label" "0" "$elapsed" "${STREAM_OUTPUT:0:200}" \
        > "${RESULTS_DIR}/${idx}.tmp"
    fi
    mv "${RESULTS_DIR}/${idx}.tmp" "${RESULTS_DIR}/${idx}.done"
  } &
}

collect_results() {
  # Poll for results and print them as they arrive.
  PASS=0
  FAIL=0
  local printed=0

  while [[ "$printed" -lt "$TOTAL_TESTS" ]]; do
    for idx in $(seq 1 "$TOTAL_TESTS"); do
      local result_file="${RESULTS_DIR}/${idx}.done"
      local shown_file="${RESULTS_DIR}/${idx}.shown"

      [[ -f "$shown_file" ]] && continue
      [[ ! -f "$result_file" ]] && continue

      local label status elapsed body
      label=$(sed -n '1p' "$result_file")
      status=$(sed -n '2p' "$result_file")
      elapsed=$(sed -n '3p' "$result_file")
      body=$(sed -n '4p' "$result_file")

      if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
        format_pass "$label" "$status" "$elapsed"
        PASS=$((PASS + 1))
      else
        format_fail "$label" "$status" "$elapsed" "$body"
        FAIL=$((FAIL + 1))
      fi

      touch "$shown_file"
      printed=$((printed + 1))
    done
    [[ "$printed" -lt "$TOTAL_TESTS" ]] && sleep 0.2
  done
}

fi  # end strategy selection

# --- Fire tests ------------------------------------------------------------

echo "Testing against: ${BASE_URL}"
echo "Results appear as each test completes:"
echo "======================================================="

run_test "GET  /health" \
  "${BASE_URL}/health"

run_test "POST /tell-joke (default)" \
  -X POST "${BASE_URL}/tell-joke" \
  -H 'Content-Type: application/json' \
  -d '{}'

run_test "POST /tell-joke (custom + auth)" \
  -X POST "${BASE_URL}/tell-joke" \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Alice' \
  -d '{"name": "Waffles"}'

run_stream_test "POST /tell-joke/stream (SSE)" \
  -X POST "${BASE_URL}/tell-joke/stream" \
  -H 'Content-Type: application/json' \
  -d '{"name": "Bash"}'

run_test "POST /translate" \
  -X POST "${BASE_URL}/translate" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello!", "target_language": "Japanese"}'

run_test "POST /describe-image" \
  -X POST "${BASE_URL}/describe-image" \
  -H 'Content-Type: application/json' \
  -d '{}'

run_test "POST /generate-character" \
  -X POST "${BASE_URL}/generate-character" \
  -H 'Content-Type: application/json' \
  -d '{"name": "Luna"}'

run_test "POST /chat" \
  -X POST "${BASE_URL}/chat" \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is Python?"}'

run_test "POST /generate-code" \
  -X POST "${BASE_URL}/generate-code" \
  -H 'Content-Type: application/json' \
  -d '{"description": "a function that checks if a number is prime", "language": "python"}'

run_test "POST /review-code (Dotprompt)" \
  -X POST "${BASE_URL}/review-code" \
  -H 'Content-Type: application/json' \
  -d '{"code": "def add(a, b):\n    return a + b", "language": "python"}'

run_stream_test "POST /tell-story/stream (SSE)" \
  -X POST "${BASE_URL}/tell-story/stream" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "a robot learning to paint"}'

# --- Collect and summarize -------------------------------------------------

collect_results

echo ""
echo "=================================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
