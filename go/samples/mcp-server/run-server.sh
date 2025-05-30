#!/bin/bash
# Simple wrapper script for Claude Desktop MCP integration

# Set up Go environment automatically
export GOMODCACHE="$HOME/go/pkg/mod"
export GOPATH="$HOME/go"
export GOCACHE="$HOME/Library/Caches/go-build"

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the correct directory and run the server
cd "$SCRIPT_DIR"
/usr/local/go/bin/go run server.go 