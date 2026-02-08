#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Setup script for the web-endpoints-hello sample
# =================================================
#
# Installs all development tools needed to run this sample:
#   - uv (Python package manager)
#   - just (command runner)
#   - podman or docker (container runtime for Jaeger / builds)
#   - genkit CLI (Genkit Developer UI)
#   - grpcurl + grpcui (gRPC testing tools)
#   - shellcheck (shell script linting)
#   - Python dev/test extras (pip-audit, pip-licenses, pytest, etc.)
#
# Supported platforms:
#   - macOS (Homebrew)
#   - Debian / Ubuntu (apt)
#   - Fedora (dnf)
#
# Usage:
#   ./setup.sh          # Install everything
#   ./setup.sh --check  # Check what's installed without installing
#
# After setup, run:
#   just dev            # Start app + Jaeger tracing

set -euo pipefail
cd "$(dirname "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

CHECK_ONLY=false
if [[ "${1:-}" == "--check" ]]; then
    CHECK_ONLY=true
fi

# ── Platform detection ────────────────────────────────────────────────

OS="$(uname -s)"     # Darwin or Linux
DISTRO="unknown"     # debian, ubuntu, fedora, arch, etc.
PKG_MGR="none"       # brew, apt, dnf, pacman

_detect_platform() {
    if [[ "$OS" == "Darwin" ]]; then
        DISTRO="macos"
        if command -v brew &>/dev/null; then
            PKG_MGR="brew"
        fi
    elif [[ "$OS" == "Linux" ]]; then
        # Read /etc/os-release for distro identification.
        if [[ -f /etc/os-release ]]; then
            # shellcheck disable=SC1091
            . /etc/os-release
            DISTRO="${ID:-unknown}"
        fi
        if command -v apt-get &>/dev/null; then
            PKG_MGR="apt"
        elif command -v dnf &>/dev/null; then
            PKG_MGR="dnf"
        elif command -v pacman &>/dev/null; then
            PKG_MGR="pacman"
        elif command -v brew &>/dev/null; then
            PKG_MGR="brew"
        fi
    fi
}

_detect_platform

# ── Helper functions ──────────────────────────────────────────────────

_is_installed() {
    command -v "$1" &>/dev/null
}

# Install a package using the system package manager.
# Usage: _install_sys_package <command-name> <brew-pkg> <apt-pkg> <dnf-pkg>
# Pass "-" to skip a package manager (e.g. if the tool isn't in that repo).
_install_sys_package() {
    local cmd="$1"
    local brew_pkg="${2:--}"
    local apt_pkg="${3:--}"
    local dnf_pkg="${4:--}"

    if _is_installed "$cmd"; then
        echo -e "  ${GREEN}✓${NC} $cmd ${DIM}($(command -v "$cmd"))${NC}"
        return 0
    fi

    if $CHECK_ONLY; then
        echo -e "  ${YELLOW}✗${NC} $cmd — not installed"
        return 1
    fi

    case "$PKG_MGR" in
        brew)
            if [[ "$brew_pkg" != "-" ]]; then
                echo -e "  ${BLUE}→${NC} Installing $cmd via brew..."
                brew install "$brew_pkg"
                echo -e "  ${GREEN}✓${NC} $cmd installed"
                return 0
            fi
            ;;
        apt)
            if [[ "$apt_pkg" != "-" ]]; then
                echo -e "  ${BLUE}→${NC} Installing $cmd via apt..."
                sudo apt-get update -qq
                sudo apt-get install -y -qq "$apt_pkg"
                echo -e "  ${GREEN}✓${NC} $cmd installed"
                return 0
            fi
            ;;
        dnf)
            if [[ "$dnf_pkg" != "-" ]]; then
                echo -e "  ${BLUE}→${NC} Installing $cmd via dnf..."
                sudo dnf install -y -q "$dnf_pkg"
                echo -e "  ${GREEN}✓${NC} $cmd installed"
                return 0
            fi
            ;;
    esac

    echo -e "  ${RED}✗${NC} $cmd — no package manager can install it"
    return 1
}

# ── Tool-specific installers ─────────────────────────────────────────

_install_uv() {
    if _is_installed uv; then
        echo -e "  ${GREEN}✓${NC} uv ${DIM}($(uv --version 2>/dev/null || echo 'installed'))${NC}"
        return 0
    fi

    if $CHECK_ONLY; then
        echo -e "  ${YELLOW}✗${NC} uv — not installed"
        return 1
    fi

    echo -e "  ${BLUE}→${NC} Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the env so uv is on PATH for the rest of this script.
    # shellcheck disable=SC1091
    [[ -f "$HOME/.local/bin/env" ]] && . "$HOME/.local/bin/env" || true
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "  ${GREEN}✓${NC} uv installed"
}

_install_just() {
    if _is_installed just; then
        echo -e "  ${GREEN}✓${NC} just ${DIM}($(command -v just))${NC}"
        return 0
    fi

    if $CHECK_ONLY; then
        echo -e "  ${YELLOW}✗${NC} just — not installed"
        return 1
    fi

    # macOS: use brew.
    if [[ "$PKG_MGR" == "brew" ]]; then
        echo -e "  ${BLUE}→${NC} Installing just via brew..."
        brew install just
        echo -e "  ${GREEN}✓${NC} just installed"
        return 0
    fi

    # Debian/Ubuntu 24.04+ and Fedora 39+ have just in their repos.
    if [[ "$PKG_MGR" == "apt" ]]; then
        # Check if 'just' is available in apt (Ubuntu 24.04+, Debian 13+).
        if apt-cache show just &>/dev/null 2>&1; then
            echo -e "  ${BLUE}→${NC} Installing just via apt..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq just
            echo -e "  ${GREEN}✓${NC} just installed"
            return 0
        fi
    elif [[ "$PKG_MGR" == "dnf" ]]; then
        if dnf info just &>/dev/null 2>&1; then
            echo -e "  ${BLUE}→${NC} Installing just via dnf..."
            sudo dnf install -y -q just
            echo -e "  ${GREEN}✓${NC} just installed"
            return 0
        fi
    fi

    # Fallback: official install script (works everywhere).
    echo -e "  ${BLUE}→${NC} Installing just via official installer..."
    local install_dir="$HOME/.local/bin"
    mkdir -p "$install_dir"
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
        | bash -s -- --to "$install_dir"
    export PATH="$install_dir:$PATH"
    echo -e "  ${GREEN}✓${NC} just installed to $install_dir"
}

_install_genkit() {
    if _is_installed genkit; then
        echo -e "  ${GREEN}✓${NC} genkit CLI ${DIM}($(command -v genkit))${NC}"
        return 0
    fi

    if $CHECK_ONLY; then
        echo -e "  ${YELLOW}✗${NC} genkit CLI — not installed"
        return 1
    fi

    echo -e "  ${BLUE}→${NC} Installing genkit CLI..."
    if _is_installed npm; then
        npm install -g genkit-cli
    else
        echo -e "  ${YELLOW}!${NC} npm not found — install genkit CLI manually:"
        echo "       npm install -g genkit-cli"
        echo "       Or: curl -sL cli.genkit.dev | bash"
        return 1
    fi
    echo -e "  ${GREEN}✓${NC} genkit CLI installed"
}

_install_grpcurl() {
    if _is_installed grpcurl; then
        echo -e "  ${GREEN}✓${NC} grpcurl ${DIM}($(command -v grpcurl))${NC}"
        return 0
    fi

    if $CHECK_ONLY; then
        echo -e "  ${YELLOW}✗${NC} grpcurl — not installed ${DIM}(optional)${NC}"
        return 1
    fi

    # macOS: brew.
    if [[ "$PKG_MGR" == "brew" ]]; then
        echo -e "  ${BLUE}→${NC} Installing grpcurl via brew..."
        brew install grpcurl
        echo -e "  ${GREEN}✓${NC} grpcurl installed"
        return 0
    fi

    # Linux: try Go install, then prebuilt binary.
    if _is_installed go; then
        echo -e "  ${BLUE}→${NC} Installing grpcurl via go install..."
        go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
        echo -e "  ${GREEN}✓${NC} grpcurl installed"
        return 0
    fi

    # Download prebuilt binary from GitHub.
    echo -e "  ${BLUE}→${NC} Downloading grpcurl prebuilt binary..."
    local arch
    arch="$(uname -m)"
    case "$arch" in
        x86_64)  arch="linux_x86_64" ;;
        aarch64) arch="linux_arm64" ;;
        arm64)   arch="linux_arm64" ;;
        *)
            echo -e "  ${YELLOW}!${NC} grpcurl — unsupported architecture: $arch"
            echo "       Install manually: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest"
            return 1
            ;;
    esac
    local version
    version=$(curl -sSf https://api.github.com/repos/fullstorydev/grpcurl/releases/latest \
        | grep '"tag_name"' | head -1 | sed 's/.*"v\(.*\)".*/\1/')
    local url="https://github.com/fullstorydev/grpcurl/releases/download/v${version}/grpcurl_${version}_${arch}.tar.gz"
    local install_dir="$HOME/.local/bin"
    mkdir -p "$install_dir"
    curl -sSfL "$url" | tar xz -C "$install_dir" grpcurl
    chmod +x "$install_dir/grpcurl"
    export PATH="$install_dir:$PATH"
    echo -e "  ${GREEN}✓${NC} grpcurl installed to $install_dir"
}

_install_grpcui() {
    if _is_installed grpcui; then
        echo -e "  ${GREEN}✓${NC} grpcui ${DIM}($(command -v grpcui))${NC}"
        return 0
    fi

    if $CHECK_ONLY; then
        echo -e "  ${YELLOW}✗${NC} grpcui — not installed ${DIM}(optional)${NC}"
        return 1
    fi

    # macOS: brew.
    if [[ "$PKG_MGR" == "brew" ]]; then
        echo -e "  ${BLUE}→${NC} Installing grpcui via brew..."
        brew install grpcui
        echo -e "  ${GREEN}✓${NC} grpcui installed"
        return 0
    fi

    # Linux: Go install is the only reliable method.
    if _is_installed go; then
        echo -e "  ${BLUE}→${NC} Installing grpcui via go install..."
        go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
        echo -e "  ${GREEN}✓${NC} grpcui installed"
        return 0
    fi

    echo -e "  ${YELLOW}!${NC} grpcui — requires Go to install on Linux"
    echo "       Install Go: https://go.dev/dl/"
    echo "       Then: go install github.com/fullstorydev/grpcui/cmd/grpcui@latest"
    return 1
}

# ── Main ──────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}web-endpoints-hello — Development Setup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${DIM}Platform: $OS / $DISTRO / pkg: $PKG_MGR${NC}"
echo ""

if $CHECK_ONLY; then
    echo "Checking installed tools..."
else
    echo "Installing development tools..."
fi
echo ""

all_ok=true

# 1. uv — Python package manager (cross-platform curl installer)
_install_uv || all_ok=false

# 2. just — command runner (brew / apt / dnf / official installer)
_install_just || all_ok=false

# 3. Container runtime for Jaeger — podman preferred, docker also works.
if _is_installed podman; then
    echo -e "  ${GREEN}✓${NC} podman ${DIM}($(command -v podman))${NC}"
elif _is_installed docker; then
    echo -e "  ${GREEN}✓${NC} docker ${DIM}($(command -v docker)) — using as container runtime${NC}"
else
    # Neither found — install podman.
    _install_sys_package podman podman podman podman || all_ok=false
fi

# 4. genkit CLI — Developer UI (npm)
_install_genkit || all_ok=false

# 5. shellcheck — script linting (optional; brew / apt / dnf)
_install_sys_package shellcheck shellcheck shellcheck ShellCheck || true

# 6. grpcurl — gRPC CLI testing tool (optional; brew / go / prebuilt binary)
_install_grpcurl || true

# 7. grpcui — gRPC web UI testing tool (optional; brew / go)
_install_grpcui || true

echo ""

# Install Python dependencies (including dev + test extras).
if ! $CHECK_ONLY; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    uv sync --extra dev --extra test
    echo -e "  ${GREEN}✓${NC} Python dependencies installed (including dev + test extras)"
    echo ""
fi

# Copy .env if needed
if [[ ! -f local.env ]]; then
    if [[ -f local.env.example ]]; then
        cp local.env.example local.env
        echo -e "${YELLOW}Created local.env from local.env.example${NC}"
        echo "Edit local.env to set your GEMINI_API_KEY"
        echo ""
    fi
fi

if $all_ok; then
    echo -e "${GREEN}All tools installed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Set your API key:  export GEMINI_API_KEY=your-key"
    echo "  2. Start developing:  just dev"
    echo ""
else
    echo -e "${YELLOW}Some tools could not be installed.${NC}"
    echo "Install them manually and re-run ./setup.sh --check"
    echo ""
fi
