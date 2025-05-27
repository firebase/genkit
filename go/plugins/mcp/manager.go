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
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// MCPManagerOptions holds configuration for MCPManager
type MCPManagerOptions struct {
	// Name for this manager instance - used for logging and identification
	Name string
	// Version number for this manager (defaults to "1.0.0" if empty)
	Version string
	// MCPServers is a map of server names to their configurations
	MCPServers map[string]MCPClientOptions
}

// MCPManager manages connections to multiple MCP servers
type MCPManager struct {
	name    string
	version string
	clients map[string]*GenkitMCPClient
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
	for serverName, config := range options.MCPServers {
		if err := manager.Connect(serverName, config); err != nil {
			log.Printf("[MCP Manager] Failed to connect to %s: %v", serverName, err)
			// Continue with other servers
		}
	}

	return manager, nil
}

// Connect connects to a single MCP server with the provided configuration
func (m *MCPManager) Connect(serverName string, config MCPClientOptions) error {
	// If a client with this name already exists, disconnect it first
	if existingClient, exists := m.clients[serverName]; exists {
		if err := existingClient.Disconnect(); err != nil {
			log.Printf("[MCP Manager] Warning: error disconnecting existing client %s: %v", serverName, err)
		}
	}

	log.Printf("[MCP Manager] Connecting to MCP server '%s' in manager '%s'", serverName, m.name)

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
func (m *MCPManager) Disconnect(serverName string) error {
	client, exists := m.clients[serverName]
	if !exists {
		return fmt.Errorf("no client found with name '%s'", serverName)
	}

	log.Printf("[MCP Manager] Disconnecting MCP server '%s' in manager '%s'", serverName, m.name)

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
			log.Printf("[MCP Manager] Error fetching tools from client %s: %v", name, err)
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
