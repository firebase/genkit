#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Common utilities for Genkit Python samples
# ==========================================
#
# This script provides shared functions for all sample run.sh scripts.
# Source this file at the beginning of your run.sh:
#
#   source "$(dirname "$0")/../_common.sh"
#
# Available functions:
#   - print_banner "Title" "emoji"  - Print a colorful banner
#   - check_env_var "VAR_NAME" "get_url" - Check if env var is set
#   - open_browser_for_url "url" - Open browser when URL is ready
#   - genkit_start_with_browser [args...] - Start genkit and auto-open browser

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# Print a colorful banner
# Usage: print_banner "Title Text" "emoji"
print_banner() {
    local title="$1"
    local emoji="${2:-✨}"
    
    # Calculate padding for centering (box is 67 chars wide, content is 65)
    local content="${emoji} ${title} ${emoji}"
    local content_len=${#content}
    local padding=$(( (65 - content_len) / 2 ))
    local left_pad
    left_pad=$(printf '%*s' "$padding" '')
    local right_pad
    right_pad=$(printf '%*s' "$((65 - content_len - padding))" '')
    
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    printf "║%s%s%s║\n" "$left_pad" "$content" "$right_pad"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if an environment variable is set
# Usage: check_env_var "GOOGLE_API_KEY" "https://makersuite.google.com/app/apikey"
check_env_var() {
    local var_name="$1"
    local get_url="$2"
    
    local current_val="${!var_name:-}"

    # Prompt if running interactively
    # We check -t 0 (stdin is TTY) and also explicit check for /dev/tty availability
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        local display_val="${current_val}"
        
        # Simple masking for keys
        if [[ "$var_name" == *"API_KEY"* || "$var_name" == *"SECRET"* ]]; then
            if [[ -n "$current_val" ]]; then
               display_val="******"
            fi
        fi
        
        echo -en "${BLUE}Enter ${var_name}${NC}"
        if [[ -n "$display_val" ]]; then
            echo -en " [${YELLOW}${display_val}${NC}]: "
        else
            echo -n ": "
        fi
        
        local input_val
        # Safely read from TTY
        if read -r input_val < /dev/tty; then
            if [[ -n "$input_val" ]]; then
                export "$var_name"="$input_val"
            fi
        fi
        # Only print newline if we actually prompted
        echo "" 
    fi

    if [[ -z "${!var_name:-}" ]]; then
        echo -e "${YELLOW}Warning: ${var_name} not set${NC}"
        if [[ -n "$get_url" ]]; then
            echo "Get a key from: $get_url"
        fi
        echo ""
        return 1
    fi
    return 0
}

# Check if we have a GUI/display available
# Returns 0 (true) if GUI is available, 1 (false) otherwise
has_display() {
    # Check if running in SSH without X forwarding
    if [[ -n "${SSH_CLIENT:-}" || -n "${SSH_TTY:-}" ]]; then
        # SSH session - check for X forwarding
        if [[ -z "${DISPLAY:-}" ]]; then
            return 1  # No display in SSH without X forwarding
        fi
    fi
    
    # macOS always has a display if not in SSH
    if [[ "$(uname)" == "Darwin" ]]; then
        return 0
    fi
    
    # Linux - check for display server
    if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
        return 0
    fi
    
    # WSL - check for WSLg or access to Windows
    if [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
        if command -v wslview &> /dev/null; then
            return 0
        fi
    fi
    
    # No display detected
    return 1
}

# Open browser for a given URL
# Works cross-platform: macOS, Linux, Windows (Git Bash/WSL)
# Skips browser opening if no display is available (e.g., SSH sessions)
open_browser_for_url() {
    local url="$1"
    
    # Check if we have a display
    if ! has_display; then
        echo -e "${CYAN}Remote session detected - skipping browser auto-open${NC}"
        echo -e "Open manually: ${GREEN}${url}${NC}"
        return 0
    fi
    
    if command -v open &> /dev/null; then
        open "$url"  # macOS
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$url"  # Linux
    elif command -v wslview &> /dev/null; then
        wslview "$url"  # WSL
    elif command -v start &> /dev/null; then
        start "$url"  # Windows Git Bash
    else
        echo -e "${YELLOW}Could not auto-open browser. Please open: ${GREEN}${url}${NC}"
    fi
}

# Watch genkit output for the Developer UI URL and open browser
# This function reads from stdin and watches for the URL pattern
_watch_for_devui_url() {
    local line
    local url_found=false
    
    while IFS= read -r line; do
        # Print the line as it comes (pass through)
        echo "$line"
        
        # Check for the Genkit Developer UI URL
        if [[ "$url_found" == "false" && "$line" == *"Genkit Developer UI:"* ]]; then
            # Extract URL - handle both with and without ANSI codes
            local url
            # Remove ANSI escape codes and extract URL
            url=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g' | grep -oE 'https?://[^ ]+' | head -1)
            
            if [[ -n "$url" ]]; then
                url_found=true
                # Open browser in background
                (
                    # Small delay to ensure server is fully ready
                    sleep 1
                    open_browser_for_url "$url"
                ) &
            fi
        fi
    done
}

# Start genkit with automatic browser opening
# Usage: genkit_start_with_browser -- [your command after --]
# Example: genkit_start_with_browser -- uv run src/main.py
genkit_start_with_browser() {
    echo -e "${BLUE}Starting Genkit Dev UI...${NC}"
    echo -e "Browser will open automatically when ready"
    echo ""
    
    # Run genkit start and pipe through our URL watcher
    # Using stdbuf to disable buffering for real-time output
    if command -v stdbuf &> /dev/null; then
        stdbuf -oL -eL genkit start "$@" 2>&1 | _watch_for_devui_url
    else
        # Fallback without stdbuf (may have buffering issues)
        genkit start "$@" 2>&1 | _watch_for_devui_url
    fi
}

# Install dependencies with uv
install_deps() {
    echo -e "${BLUE}Installing dependencies...${NC}"
    uv sync
    echo ""
}

# Standard help footer
print_help_footer() {
    local port="${1:-4000}"
    echo ""
    echo "Getting Started:"
    echo "  1. Set required environment variables"
    echo "  2. Run: ./run.sh"  
    echo "  3. Browser opens automatically to http://localhost:${port}"
}

# ============================================================================
# Google Cloud (gcloud) Helper Functions
# ============================================================================
# These functions provide interactive API enablement for samples that require
# Google Cloud APIs.

# Check if gcloud CLI is installed; offer to install if missing.
# Usage: check_gcloud_installed || exit 1
check_gcloud_installed() {
    if command -v gcloud &> /dev/null; then
        echo -e "${GREEN}✓ gcloud CLI found${NC}"
        return 0
    fi

    echo -e "${YELLOW}gcloud CLI is not installed.${NC}"
    echo ""
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -en "Install the Google Cloud SDK now? [Y/n]: "
        local response
        read -r response < /dev/tty
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            case "$(uname -s)" in
                Darwin)
                    if command -v brew &> /dev/null; then
                        echo -e "${BLUE}Installing via Homebrew...${NC}"
                        brew install --cask google-cloud-sdk
                    else
                        echo -e "${BLUE}Installing via curl...${NC}"
                        curl -fsSL https://sdk.cloud.google.com | bash -s -- --disable-prompts
                        # shellcheck disable=SC1091
                        source "$HOME/google-cloud-sdk/path.bash.inc" 2>/dev/null || true
                    fi
                    ;;
                Linux)
                    echo -e "${BLUE}Installing via curl...${NC}"
                    curl -fsSL https://sdk.cloud.google.com | bash -s -- --disable-prompts
                    # shellcheck disable=SC1091
                    source "$HOME/google-cloud-sdk/path.bash.inc" 2>/dev/null || true
                    ;;
                *)
                    echo "Visit: https://cloud.google.com/sdk/docs/install"
                    return 1
                    ;;
            esac
            if command -v gcloud &> /dev/null; then
                echo -e "${GREEN}✓ gcloud CLI installed successfully${NC}"
                return 0
            fi
        fi
    fi

    echo -e "${RED}Error: gcloud CLI is required${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    return 1
}

# Check if AWS CLI is installed; offer to install if missing.
# Usage: check_aws_installed || exit 1
check_aws_installed() {
    if command -v aws &> /dev/null; then
        echo -e "${GREEN}✓ AWS CLI found${NC}"
        return 0
    fi

    echo -e "${YELLOW}AWS CLI is not installed.${NC}"
    echo ""
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -en "Install the AWS CLI now? [Y/n]: "
        local response
        read -r response < /dev/tty
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            case "$(uname -s)" in
                Darwin)
                    if command -v brew &> /dev/null; then
                        echo -e "${BLUE}Installing via Homebrew...${NC}"
                        brew install awscli
                    else
                        echo -e "${BLUE}Installing via pkg...${NC}"
                        curl -fsSL "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o /tmp/AWSCLIV2.pkg
                        sudo installer -pkg /tmp/AWSCLIV2.pkg -target /
                        rm -f /tmp/AWSCLIV2.pkg
                    fi
                    ;;
                Linux)
                    echo -e "${BLUE}Installing AWS CLI v2...${NC}"
                    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
                    unzip -qo /tmp/awscliv2.zip -d /tmp
                    sudo /tmp/aws/install || /tmp/aws/install --install-dir "$HOME/.local/aws-cli" --bin-dir "$HOME/.local/bin"
                    rm -rf /tmp/awscliv2.zip /tmp/aws
                    ;;
                *)
                    echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
                    return 1
                    ;;
            esac
            if command -v aws &> /dev/null; then
                echo -e "${GREEN}✓ AWS CLI installed successfully${NC}"
                return 0
            fi
        fi
    fi

    echo -e "${RED}Error: AWS CLI is required${NC}"
    echo "Install from: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    return 1
}

# Check if Azure CLI is installed; offer to install if missing.
# Usage: check_az_installed || exit 1
check_az_installed() {
    if command -v az &> /dev/null; then
        echo -e "${GREEN}✓ Azure CLI found${NC}"
        return 0
    fi

    echo -e "${YELLOW}Azure CLI is not installed.${NC}"
    echo ""
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -en "Install the Azure CLI now? [Y/n]: "
        local response
        read -r response < /dev/tty
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            case "$(uname -s)" in
                Darwin)
                    if command -v brew &> /dev/null; then
                        echo -e "${BLUE}Installing via Homebrew...${NC}"
                        brew install azure-cli
                    else
                        echo -e "${BLUE}Installing via script...${NC}"
                        curl -fsSL https://aka.ms/InstallAzureCLIDeb | bash
                    fi
                    ;;
                Linux)
                    echo -e "${BLUE}Installing via script...${NC}"
                    curl -fsSL https://aka.ms/InstallAzureCLIDeb | sudo bash
                    ;;
                *)
                    echo "Visit: https://learn.microsoft.com/cli/azure/install-azure-cli"
                    return 1
                    ;;
            esac
            if command -v az &> /dev/null; then
                echo -e "${GREEN}✓ Azure CLI installed successfully${NC}"
                return 0
            fi
        fi
    fi

    echo -e "${RED}Error: Azure CLI is required${NC}"
    echo "Install from: https://learn.microsoft.com/cli/azure/install-azure-cli"
    return 1
}

# Check if flyctl CLI is installed; offer to install if missing.
# Usage: check_flyctl_installed || exit 1
check_flyctl_installed() {
    if command -v flyctl &> /dev/null; then
        echo -e "${GREEN}✓ flyctl CLI found${NC}"
        return 0
    fi

    echo -e "${YELLOW}flyctl CLI is not installed.${NC}"
    echo ""
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -en "Install flyctl now? [Y/n]: "
        local response
        read -r response < /dev/tty
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            echo -e "${BLUE}Installing flyctl...${NC}"
            curl -fsSL https://fly.io/install.sh | sh
            export PATH="$HOME/.fly/bin:$PATH"
            if command -v flyctl &> /dev/null; then
                echo -e "${GREEN}✓ flyctl installed successfully${NC}"
                return 0
            fi
        fi
    fi

    echo -e "${RED}Error: flyctl is required${NC}"
    echo "Install from: https://fly.io/docs/flyctl/install/"
    return 1
}

# Check if gcloud is authenticated with Application Default Credentials.
# Prompts the user to login if not authenticated (interactive).
# Usage: check_gcloud_auth || true
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

# Check if AWS CLI is authenticated.
# Prompts the user to run `aws configure` if no credentials found.
# Usage: check_aws_auth || true
check_aws_auth() {
    echo -e "${BLUE}Checking AWS authentication...${NC}"
    
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "${GREEN}✓ AWS credentials found${NC}"
        echo ""
        return 0
    fi
    
    echo -e "${YELLOW}AWS credentials not found.${NC}"
    echo ""
    
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -en "Run ${GREEN}aws configure${NC} now? [Y/n]: "
        local response
        read -r response < /dev/tty
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            aws configure
            echo ""
        else
            echo -e "${YELLOW}Skipping authentication. You may encounter auth errors.${NC}"
            return 1
        fi
    else
        echo "Run: aws configure"
        return 1
    fi
    
    return 0
}

# Check if Azure CLI is authenticated.
# Prompts the user to run `az login` if no credentials found.
# Usage: check_az_auth || true
check_az_auth() {
    echo -e "${BLUE}Checking Azure authentication...${NC}"
    
    if az account show &> /dev/null; then
        echo -e "${GREEN}✓ Azure credentials found${NC}"
        echo ""
        return 0
    fi
    
    echo -e "${YELLOW}Azure credentials not found.${NC}"
    echo ""
    
    if [[ -t 0 ]] && [ -c /dev/tty ]; then
        echo -en "Run ${GREEN}az login${NC} now? [Y/n]: "
        local response
        read -r response < /dev/tty
        if [[ -z "$response" || "$response" =~ ^[Yy] ]]; then
            echo ""
            az login
            echo ""
        else
            echo -e "${YELLOW}Skipping authentication. You may encounter auth errors.${NC}"
            return 1
        fi
    else
        echo "Run: az login"
        return 1
    fi
    
    return 0
}

# Check if a specific Google Cloud API is enabled
# Usage: is_api_enabled "aiplatform.googleapis.com" "$GOOGLE_CLOUD_PROJECT"
is_api_enabled() {
    local api="$1"
    local project="$2"
    
    gcloud services list --project="$project" --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"
}

# Enable required Google Cloud APIs interactively
# Usage: 
#   REQUIRED_APIS=("aiplatform.googleapis.com" "discoveryengine.googleapis.com")
#   enable_required_apis "${REQUIRED_APIS[@]}"
#
# The function will:
#   1. Check which APIs are already enabled
#   2. Prompt the user to enable missing APIs
#   3. Enable APIs on user confirmation
enable_required_apis() {
    local project="${GOOGLE_CLOUD_PROJECT:-}"
    local apis=("$@")
    
    if [[ -z "$project" ]]; then
        echo -e "${YELLOW}GOOGLE_CLOUD_PROJECT not set, skipping API enablement${NC}"
        return 1
    fi
    
    if [[ ${#apis[@]} -eq 0 ]]; then
        echo -e "${YELLOW}No APIs specified${NC}"
        return 0
    fi
    
    echo -e "${BLUE}Checking required APIs for project: ${project}${NC}"
    
    local apis_to_enable=()
    
    for api in "${apis[@]}"; do
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

# Run common GCP setup: check gcloud, auth, and enable APIs
# Usage:
#   REQUIRED_APIS=("aiplatform.googleapis.com")
#   run_gcp_setup "${REQUIRED_APIS[@]}"
run_gcp_setup() {
    local apis=("$@")
    
    # Check gcloud is installed
    check_gcloud_installed || return 1
    
    # Check/prompt for project
    check_env_var "GOOGLE_CLOUD_PROJECT" "" || {
        echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT is required${NC}"
        echo ""
        echo "Set it with:"
        echo "  export GOOGLE_CLOUD_PROJECT=your-project-id"
        echo ""
        return 1
    }
    
    # Check authentication
    check_gcloud_auth || true
    
    # Enable APIs if any were specified
    if [[ ${#apis[@]} -gt 0 ]]; then
        enable_required_apis "${apis[@]}" || true
    fi
    
    return 0
}
