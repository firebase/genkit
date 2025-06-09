// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package mcp

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/genkit"
)

// MCPServerConfig holds configuration for a single MCP server
type MCPServerConfig struct {
	// Name for this server - used as the key for lookups
	Name string
	// Config holds the client configuration options
	Config MCPClientOptions
}

// MCPManagerOptions holds configuration for MCPManager
type MCPManagerOptions struct {
	// Name for this manager instance - used for logging and identification
	Name string
	// Version number for this manager (defaults to "1.0.0" if empty)
	Version string
	// MCPServers is an array of server configurations
	MCPServers []MCPServerConfig
}

// MCPManager manages connections to multiple MCP servers
type MCPManager struct {
	name    string
	version string
	clients map[string]*GenkitMCPClient // Internal map for efficient lookups
}

// NewMCPManager creates a new MCPManager with the given options
func NewMCPManager(options MCPManagerOptions) (*MCPManager, error) {
	// Set default values
	if options.Name == "" {
		options.Name = "genkit-mcp"
	}
	if options.Version == "" {
		options.Version = "1.0.0"
	}

	manager := &MCPManager{
		name:    options.Name,
		version: options.Version,
		clients: make(map[string]*GenkitMCPClient),
	}

	// Connect to all servers synchronously during initialization
	ctx := context.Background()
	for _, serverConfig := range options.MCPServers {
		if err := manager.Connect(ctx, serverConfig.Name, serverConfig.Config); err != nil {
			logger.FromContext(ctx).Error("Failed to connect to MCP server", "server", serverConfig.Name, "manager", manager.name, "error", err)
			// Continue with other servers
		}
	}

	return manager, nil
}

// Connect connects to a single MCP server with the provided configuration
func (m *MCPManager) Connect(ctx context.Context, serverName string, config MCPClientOptions) error {
	// If a client with this name already exists, disconnect it first
	if existingClient, exists := m.clients[serverName]; exists {
		if err := existingClient.Disconnect(); err != nil {
			logger.FromContext(ctx).Warn("Error disconnecting existing MCP client", "server", serverName, "manager", m.name, "error", err)
		}
	}

	logger.FromContext(ctx).Info("Connecting to MCP server", "server", serverName, "manager", m.name)

	// Set the server name in the config
	if config.Name == "" {
		config.Name = serverName
	}

	// Create and connect the client
	client, err := NewGenkitMCPClient(config)
	if err != nil {
		return fmt.Errorf("error connecting to server %s: %w", serverName, err)
	}

	m.clients[serverName] = client
	return nil
}

// Disconnect disconnects from a specific MCP server
func (m *MCPManager) Disconnect(ctx context.Context, serverName string) error {
	client, exists := m.clients[serverName]
	if !exists {
		return fmt.Errorf("no client found with name '%s'", serverName)
	}

	logger.FromContext(ctx).Info("Disconnecting MCP server", "server", serverName, "manager", m.name)

	err := client.Disconnect()
	delete(m.clients, serverName)
	return err
}

// GetActiveTools retrieves all tools from all connected and enabled MCP clients
func (m *MCPManager) GetActiveTools(ctx context.Context, gk *genkit.Genkit) ([]ai.Tool, error) {
	var allTools []ai.Tool

	// Simple sequential iteration - fast enough for typical usage (1-5 clients)
	for name, client := range m.clients {
		if !client.IsEnabled() {
			continue
		}

		tools, err := client.GetActiveTools(ctx, gk)
		if err != nil {
			logger.FromContext(ctx).Error("Error fetching tools from MCP client", "client", name, "manager", m.name, "error", err)
			continue
		}

		allTools = append(allTools, tools...)
	}

	return allTools, nil
}

// GetPrompt retrieves a specific prompt from a specific server
func (m *MCPManager) GetPrompt(ctx context.Context, gk *genkit.Genkit, serverName, promptName string, args map[string]string) (*ai.Prompt, error) {
	client, exists := m.clients[serverName]
	if !exists {
		return nil, fmt.Errorf("no client found with name '%s'", serverName)
	}

	if !client.IsEnabled() {
		return nil, fmt.Errorf("client '%s' is disabled", serverName)
	}

	return client.GetPrompt(ctx, gk, promptName, args)
}
