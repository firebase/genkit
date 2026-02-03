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

# Genkit Chat - Run Script
# Works on Linux, macOS, and Windows (with Git Bash or WSL)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

show_help() {
    cat << EOF
Genkit Chat - Multi-model AI Chat Application

Usage: ./run.sh [command] [options]

Commands:
    start       Run backend (DevUI) and frontend concurrently
    dev         Run backend with Genkit DevUI (recommended for development)
    backend     Run backend only
    frontend    Run frontend development server
    build       Build frontend for production
    lint        Run lint and type checks on backend code
    test        Run backend integration tests
    stop        Stop all running services (kills ports 8080, 4000, 4001, 4034, 4200)
    container   Build container image with Podman/Docker
    deploy      Deploy to Cloud Run
    help        Show this help message

Backend Options:
    --framework robyn|fastapi   Web framework to use (default: robyn)
    --port PORT                 Server port (default: 8080)

Environment Variables:
    GEMINI_API_KEY          Gemini API key (recommended for Google AI)
    GOOGLE_GENAI_API_KEY    Legacy Google AI API key (use GEMINI_API_KEY instead)
    ANTHROPIC_API_KEY       Anthropic API key (optional)
    OPENAI_API_KEY          OpenAI API key (optional)
    OLLAMA_HOST             Ollama server URL (default: http://localhost:11434)
    PORT                    Server port (default: 8080)

Ollama Models:
    If Ollama is installed and running, this script will automatically pull
    the following models if they are not already available:
      - llama3.2       Default chat model (~2GB)
      - gemma3:4b      Compact Google model (~3.3GB)
      - mistral        General purpose (~4.1GB)
      - qwen2.5-coder  Code-focused model (~4.7GB)

Examples:
    ./run.sh start                        # Start with Robyn (default)
    ./run.sh dev --framework fastapi      # Start with FastAPI + DevUI
    ./run.sh backend --framework robyn    # Backend only with Robyn
    ./run.sh backend --framework fastapi  # Backend only with FastAPI
    ./run.sh stop                         # Stop all running services
    ./run.sh container                    # Build container image
EOF
}

stop_services() {
    log_info "Stopping all Genkit Chat services..."
    
    local ports=(8080 4000 4001 4034 4200)
    local killed=0
    
    for port in "${ports[@]}"; do
        local pids
        pids=$(lsof -ti:"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            log_success "Killed process(es) on port $port"
            killed=$((killed + 1))
        fi
    done
    
    if [ "$killed" -eq 0 ]; then
        log_info "No services were running"
    else
        log_success "Stopped $killed service(s)"
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        exit 1
    fi
    log_success "Python 3 found: $(python3 --version)"
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        log_warning "uv not found. Installing..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    log_success "uv found: $(uv --version)"
}

check_node() {
    local required_major=24
    
    # Try to use fnm if available
    if command -v fnm &> /dev/null; then
        log_info "Using fnm for Node.js version management"
        # Set up fnm environment (required for fnm use to work)
        eval "$(fnm env --shell bash 2>/dev/null)" || eval "$(fnm env)"
        
        # Check if Node 24 is installed via fnm
        if ! fnm list 2>/dev/null | grep -q "v${required_major}"; then
            log_info "Installing Node.js ${required_major} via fnm..."
            fnm install ${required_major}
        fi
        fnm use ${required_major} --silent-if-unchanged 2>/dev/null || fnm use ${required_major}
        log_success "Node.js (via fnm): $(node --version)"
        return 0
    fi
    
    # Fall back to system node
    if ! command -v node &> /dev/null; then
        log_error "Node.js ${required_major}+ is required for frontend."
        log_info "Install via fnm: curl -fsSL https://fnm.vercel.app/install | bash && fnm install ${required_major}"
        log_info "Or from: https://nodejs.org"
        exit 1
    fi
    
    # Check version
    local node_version
    node_version=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$node_version" -lt "$required_major" ]; then
        log_warning "Node.js ${required_major}+ recommended (found v${node_version})"
        log_info "Update via fnm: fnm install ${required_major} && fnm use ${required_major}"
    fi
    
    log_success "Node.js found: $(node --version)"
}

check_genkit_cli() {
    if ! command -v genkit &> /dev/null; then
        log_warning "Genkit CLI not found. Installing..."
        npm install -g genkit
    fi
    log_success "Genkit CLI found"
}

check_ollama() {
    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        log_warning "Ollama not found. Install from: https://ollama.com/download"
        log_info "Ollama models will not be available."
        return 1
    fi
    
    # Check if Ollama server is running
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        log_warning "Ollama server not responding. Start with: ollama serve"
        log_info "Ollama models will not be available until the server is running."
        return 1
    fi
    
    log_success "Ollama server is running"
    return 0
}

setup_ollama_models() {
    # All Ollama models used in genkit-chat
    # These are listed in order of priority (default model first)
    local RECOMMENDED_MODELS=(
        "llama3.2"        # Default chat model (~2GB)
        "gemma3:4b"       # Compact Google model (~3.3GB)
        "mistral"         # General purpose (~4.1GB)
        "qwen2.5-coder"   # Code-focused model (~4.7GB)
    )
    
    log_info "Checking Ollama models..."
    log_info "Note: First-time model pulls can take several minutes depending on your connection."
    
    for model in "${RECOMMENDED_MODELS[@]}"; do
        # Check if model exists (match at start of line or after whitespace)
        if ollama list 2>/dev/null | grep -qE "(^|[[:space:]])${model}"; then
            log_success "Model '$model' is available"
        else
            log_info "Pulling model '$model'..."
            if ollama pull "$model"; then
                log_success "Model '$model' pulled successfully"
            else
                log_warning "Failed to pull model '$model' - you can pull it manually with: ollama pull $model"
            fi
        fi
    done
}

setup_backend() {
    log_info "Setting up backend..."
    
    cd "$BACKEND_DIR"
    
    # Create venv and sync dependencies using uv
    if [ ! -d ".venv" ]; then
        uv venv
        log_success "Created virtual environment"
    fi
    
    # Sync dependencies from pyproject.toml (including test group for lint tools)
    uv sync --group test
    
    log_success "Backend dependencies installed"
}

check_lint() {
    log_info "Running lint checks..."
    
    cd "$BACKEND_DIR"
    
    # Run ruff check
    if ! uv run --with ruff ruff check src/ tests/; then
        log_error "Ruff lint check failed!"
        log_info "Run 'cd backend && uv run --with ruff ruff check --fix src/ tests/' to auto-fix"
        return 1
    fi
    log_success "Ruff lint check passed"
    
    # Run ruff format check
    if ! uv run --with ruff ruff format --check src/ tests/; then
        log_error "Ruff format check failed!"
        log_info "Run 'cd backend && uv run --with ruff ruff format src/ tests/' to auto-fix"
        return 1
    fi
    log_success "Ruff format check passed"
    
    # Run pyright type check
    if ! uv run --with pyright pyright src/ tests/; then
        log_error "Pyright type check failed!"
        return 1
    fi
    log_success "Pyright type check passed"
    
    log_success "All lint checks passed!"
}

run_dev() {
    local framework="robyn"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --framework)
                framework="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Starting Genkit Chat with DevUI (${framework})..."
    check_python
    check_uv
    check_genkit_cli
    setup_backend
    
    # Setup Ollama models if Ollama is available
    if check_ollama; then
        setup_ollama_models
    fi
    
    log_info "DevUI will be available at http://localhost:4000"
    log_info "API will be available at http://localhost:8080"
    
    cd "$BACKEND_DIR"
    source "$BACKEND_DIR/.venv/bin/activate" 2>/dev/null || source "$BACKEND_DIR/.venv/Scripts/activate" 2>/dev/null
    genkit start -- python src/main.py --framework "$framework"
}

run_start() {
    local framework="robyn"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --framework)
                framework="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Starting Genkit Chat (Backend + Frontend) with ${framework}..."
    check_python
    check_uv
    check_node
    check_genkit_cli
    
    # Setup backend
    setup_backend
    
    # Setup Ollama models if Ollama is available
    if check_ollama; then
        setup_ollama_models
    fi
    
    # Setup frontend
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
        log_success "Frontend dependencies installed"
    fi
    
    log_info ""
    log_info "Starting services:"
    log_info "  DevUI:    http://localhost:4000"
    log_info "  API:      http://localhost:8080 (${framework})"
    log_info "  Frontend: http://localhost:4200"
    log_info ""
    log_info "Press Ctrl+C to stop all services"
    log_info ""
    
    # Trap to kill all background processes on exit
    trap 'kill $(jobs -p) 2>/dev/null' EXIT
    
    # Start backend with DevUI in background
    cd "$BACKEND_DIR"
    source "$BACKEND_DIR/.venv/bin/activate" 2>/dev/null || source "$BACKEND_DIR/.venv/Scripts/activate" 2>/dev/null
    genkit start -- python src/main.py --framework "$framework" &
    BACKEND_PID=$!
    
    # Wait a bit for backend to start
    sleep 3
    
    # Start frontend in foreground
    cd "$FRONTEND_DIR"
    npm start
}

run_backend() {
    local framework="robyn"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --framework)
                framework="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Starting backend server (${framework})..."
    check_python
    check_uv
    setup_backend
    
    # Setup Ollama models if Ollama is available
    if check_ollama; then
        setup_ollama_models
    fi
    
    cd "$BACKEND_DIR"
    source "$BACKEND_DIR/.venv/bin/activate" 2>/dev/null || source "$BACKEND_DIR/.venv/Scripts/activate" 2>/dev/null
    
    python src/main.py --framework "$framework"
}

run_frontend() {
    log_info "Starting frontend development server..."
    check_node
    
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        npm install
        log_success "Frontend dependencies installed"
    fi
    
    npm start
}

build_frontend() {
    log_info "Building frontend for production..."
    check_node
    
    cd "$FRONTEND_DIR"
    npm install
    npm run build
    
    # Copy to backend static directory
    rm -rf "$BACKEND_DIR/static"
    cp -r dist/browser "$BACKEND_DIR/static"
    log_success "Frontend built and copied to backend/static"
}

build_container() {
    log_info "Building container image..."
    
    # Detect container runtime
    if command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
    else
        log_error "Neither Podman nor Docker found. Please install one."
        exit 1
    fi
    
    log_info "Using $CONTAINER_CMD"
    
    cd "$SCRIPT_DIR"
    $CONTAINER_CMD build -t genkit-chat:latest -f Containerfile .
    log_success "Container image built: genkit-chat:latest"
}

deploy_cloudrun() {
    log_info "Deploying to Cloud Run..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Install from https://cloud.google.com/sdk"
        exit 1
    fi
    
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        log_error "No GCP project configured. Run: gcloud config set project YOUR_PROJECT"
        exit 1
    fi
    
    log_info "Deploying to project: $PROJECT_ID"
    
    cd "$SCRIPT_DIR"
    gcloud builds submit --tag "gcr.io/$PROJECT_ID/genkit-chat"
    gcloud run deploy genkit-chat \
        --image "gcr.io/$PROJECT_ID/genkit-chat" \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated
    
    log_success "Deployed to Cloud Run!"
}

# Main entry point
cmd="${1:-help}"
shift 2>/dev/null || true  # Remove the command, keep remaining args

case "$cmd" in
    start)
        run_start "$@"
        ;;
    dev)
        run_dev "$@"
        ;;
    backend)
        run_backend "$@"
        ;;
    frontend)
        run_frontend
        ;;
    build)
        build_frontend
        ;;
    lint)
        check_python
        check_uv
        setup_backend
        check_lint
        ;;
    test)
        check_python
        check_uv
        setup_backend
        cd "$BACKEND_DIR"
        uv run --group test pytest tests/ -v
        ;;
    stop)
        stop_services
        ;;
    container)
        build_container
        ;;
    deploy)
        deploy_cloudrun
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $cmd"
        show_help
        exit 1
        ;;
esac
