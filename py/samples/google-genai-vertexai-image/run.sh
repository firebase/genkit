#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Vertex AI Image Demo
# ====================
#
# Demonstrates image generation with Vertex AI Imagen.
#
# This script automates most of the setup:
#   - Detects/prompts for GOOGLE_CLOUD_PROJECT
#   - Checks gcloud authentication
#   - Enables required APIs
#   - Installs dependencies
#
# Usage:
#   ./run.sh          # Start the demo with Dev UI
#   ./run.sh --setup  # Run setup only (check auth, enable APIs)
#   ./run.sh --help   # Show this help message

set -euo pipefail

cd "$(dirname "$0")"
source "../_common.sh"

# Required APIs for this demo
REQUIRED_APIS=(
    "aiplatform.googleapis.com"  # Vertex AI API (includes Imagen)
)

print_help() {
    print_banner "Vertex AI Image Demo" "🖼️"
    echo "Usage: ./run.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help     Show this help message"
    echo "  --setup    Run setup only (auth check, enable APIs)"
    echo ""
    echo "The script will automatically:"
    echo "  1. Prompt for GOOGLE_CLOUD_PROJECT if not set"
    echo "  2. Check gcloud authentication"
    echo "  3. Enable required APIs (with your permission)"
    echo "  4. Install dependencies"
    echo "  5. Start the demo and open the browser"
    echo ""
    echo "Required APIs (enabled automatically):"
    echo "  - Vertex AI API (aiplatform.googleapis.com)"
    print_help_footer
}

# Check if gcloud is installed
check_gcloud_installed() {
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}Error: gcloud CLI is not installed${NC}"
        echo ""
        echo "Install the Google Cloud SDK from:"
        echo "  https://cloud.google.com/sdk/docs/install"
        echo ""
        return 1
    fi
    return 0
}

# Check if gcloud is authenticated
check_gcloud_auth() {
    echo -e "${BLUE}Checking gcloud authentication...${NC}"
    
    # Check application default credentials
    if ! gcloud auth application-default print-access-token &> /dev/null; then
        echo -e "${YELLOW}Application default credentials not found.${NC}"
        echo ""
        
        if [[ -t 0 ]] && [ -c /dev/tty ]; then
            echo -en "Run ${GREEN}gcloud auth application-default login${NC} now? [Y/n]: "
            local response
            read -r response < /dev/tty
            if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
                echo ""
                gcloud auth application-default login
                echo ""
            else
                echo -e "${YELLOW}Skipping authentication. You may encounter auth errors.${NC}"
                return 1
            fi
        else
            echo "Run: gcloud auth application-default login"
            return 1
        fi
    else
        echo -e "${GREEN}✓ Application default credentials found${NC}"
    fi
    
    echo ""
    return 0
}

# Check if an API is enabled
is_api_enabled() {
    local api="$1"
    local project="$2"
    
    gcloud services list --project="$project" --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"
}

# Enable required APIs
enable_required_apis() {
    local project="${GOOGLE_CLOUD_PROJECT:-}"
    
    if [[ -z "$project" ]]; then
        echo -e "${YELLOW}GOOGLE_CLOUD_PROJECT not set, skipping API enablement${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Checking required APIs for project: ${project}${NC}"
    
    local apis_to_enable=()
    
    for api in "${REQUIRED_APIS[@]}"; do
        if is_api_enabled "$api" "$project"; then
            echo -e "  ${GREEN}✓${NC} $api"
        else
            echo -e "  ${YELLOW}✗${NC} $api (not enabled)"
            apis_to_enable+=("$api")
        fi
    done
    
    echo ""
    
    if [[ ${#apis_to_enable[@]} -eq 0 ]]; then
        echo -e "${GREEN}All required APIs are already enabled!${NC}"
        echo ""
        return 0
    fi
    
    # Prompt to enable APIs
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -e "${YELLOW}The following APIs need to be enabled:${NC}"
        for api in "${apis_to_enable[@]}"; do
            echo "  - $api"
        done
        echo ""
        echo -en "Enable these APIs now? [Y/n]: "
        local response
        read -r response < /dev/tty
        
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            for api in "${apis_to_enable[@]}"; do
                echo -e "${BLUE}Enabling $api...${NC}"
                if gcloud services enable "$api" --project="$project"; then
                    echo -e "${GREEN}✓ Enabled $api${NC}"
                else
                    echo -e "${RED}✗ Failed to enable $api${NC}"
                    return 1
                fi
            done
            echo ""
            echo -e "${GREEN}All APIs enabled successfully!${NC}"
        else
            echo -e "${YELLOW}Skipping API enablement. You may encounter errors.${NC}"
            return 1
        fi
    else
        echo "Enable APIs with:"
        for api in "${apis_to_enable[@]}"; do
            echo "  gcloud services enable $api --project=$project"
        done
        return 1
    fi
    
    echo ""
    return 0
}

# Run full setup
run_setup() {
    print_banner "Setup" "⚙️"
    
    # Check gcloud is installed
    check_gcloud_installed || exit 1
    
    # Check/prompt for project
    check_env_var "GOOGLE_CLOUD_PROJECT" "" || {
        echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT is required${NC}"
        echo ""
        echo "Set it with:"
        echo "  export GOOGLE_CLOUD_PROJECT=your-project-id"
        echo ""
        exit 1
    }
    
    # Check authentication
    check_gcloud_auth || true
    
    # Enable APIs
    enable_required_apis || true
    
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
}

# Main
case "${1:-}" in
    --help|-h)
        print_help
        exit 0
        ;;
    --setup)
        run_setup
        exit 0
        ;;
esac

print_banner "Vertex AI Image Demo" "🖼️"

# Check gcloud is installed
check_gcloud_installed || exit 1

# Check/prompt for project
check_env_var "GOOGLE_CLOUD_PROJECT" "" || {
    echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT is required${NC}"
    echo ""
    echo "Set it with:"
    echo "  export GOOGLE_CLOUD_PROJECT=your-project-id"
    echo ""
    exit 1
}

# Check authentication
check_gcloud_auth || true

# Enable APIs
enable_required_apis || true

# Install dependencies
install_deps

# Start the demo
genkit_start_with_browser -- \
    uv tool run --from watchdog watchmedo auto-restart \
        -d src \
        -d ../../packages \
        -d ../../plugins \
        -p '*.py;*.prompt;*.json' \
        -R \
        -- uv run src/main.py "$@"
