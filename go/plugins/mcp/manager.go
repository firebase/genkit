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

// Package mcp provides a client for integration with the Model Context Protocol.
package mcp

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// ClientState tracks the state of a MCP client for internal logging
type ClientState struct {
	Error struct {
		Message string
		Detail  interface{}
	}
}

// MCPManagerOptions holds configuration for MCPManager
type MCPManagerOptions struct {
	// Name for this manager instance - used for logging and identification
	Name string
	// Version number for this manager (defaults to "1.0.0" if empty)
	Version string
	// MCPServers is a map of server names to their configurations
	MCPServers map[string]MCPClientOptions
	// DefaultTimeout is the default timeout for connection operations
	DefaultTimeout time.Duration
}

// MCPManager manages connections to multiple MCP servers
type MCPManager struct {
	Name           string
	version        string
	clients        map[string]*GenkitMCPClient
	clientStates   map[string]*ClientState
	ready          bool
	readyMu        sync.Mutex
	readyWg        sync.WaitGroup
	readyChan      chan struct{}
	defaultTimeout time.Duration
}

// NewMCPManager creates a new MCPManager with the given options
func NewMCPManager(options MCPManagerOptions) *MCPManager {
	// Set default values
	if options.Name == "" {
		options.Name = "genkit-mcp"
	}
	if options.Version == "" {
		options.Version = "1.0.0"
	}
	if options.DefaultTimeout == 0 {
		options.DefaultTimeout = 30 * time.Second
	}

	manager := &MCPManager{
		Name:           options.Name,
		version:        options.Version,
		clients:        make(map[string]*GenkitMCPClient),
		clientStates:   make(map[string]*ClientState),
		ready:          false,
		readyChan:      make(chan struct{}),
		defaultTimeout: options.DefaultTimeout,
	}

	// Initialize connections if servers were provided
	if options.MCPServers != nil && len(options.MCPServers) > 0 {
		go manager.UpdateServers(options.MCPServers)
	}

	return manager
}

// Ready returns a channel that is closed when the manager has completed initial connection attempts
func (m *MCPManager) Ready() <-chan struct{} {
	m.readyMu.Lock()
	defer m.readyMu.Unlock()

	if m.ready {
		ch := make(chan struct{})
		close(ch)
		return ch
	}

	return m.readyChan
}

// WaitForReady blocks until the manager is ready or context is canceled
func (m *MCPManager) WaitForReady(ctx context.Context) error {
	m.readyMu.Lock()
	if m.ready {
		m.readyMu.Unlock()
		return nil
	}
	m.readyMu.Unlock()

	select {
	case <-m.readyChan:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

// Connect connects to a single MCP server with the provided configuration
func (m *MCPManager) Connect(serverName string, config MCPClientOptions) error {
	// If a client with this name already exists, disconnect it first
	if existingClient, exists := m.clients[serverName]; exists {
		err := existingClient.Disconnect()
		if err != nil {
			existingClient.Disable()
			m.setError(serverName, "Error disconnecting from existing connection", err)
			// Continue with reconnection even if disconnect failed
		}
	}

	// Set the server name in the config
	if config.Name == "" {
		config.Name = serverName
	}

	// Create and connect the client
	client := NewGenkitMCPClient(config)
	m.clients[serverName] = client

	// Wait for client to be ready to detect connection errors
	ctx, cancel := context.WithTimeout(context.Background(), m.defaultTimeout)
	defer cancel()

	if err := client.WaitForReady(ctx); err != nil {
		m.setError(serverName, "Error connecting to server", err)
		client.Disable()
		return err
	}

	return nil
}

// Disconnect disconnects from a specific MCP server
func (m *MCPManager) Disconnect(serverName string) error {
	client, exists := m.clients[serverName]
	if !exists {
		return fmt.Errorf("no client found with name '%s'", serverName)
	}

	err := client.Disconnect()
	if err != nil {
		client.Disable()
		m.setError(serverName, "Error disconnecting from server", err)
	}

	delete(m.clients, serverName)
	return err
}

// Disable temporarily disables a server connection
func (m *MCPManager) Disable(serverName string) error {
	client, exists := m.clients[serverName]
	if !exists {
		return fmt.Errorf("no client found with name '%s'", serverName)
	}

	if client.IsEnabled() {
		client.Disable()
	}

	return nil
}

// Reenable re-enables a previously disabled server connection
func (m *MCPManager) Reenable(serverName string) error {
	client, exists := m.clients[serverName]
	if !exists {
		return fmt.Errorf("no client found with name '%s'", serverName)
	}

	client.Reenable()
	return nil
}

// Restart restarts the connection for a specific server
func (m *MCPManager) Restart(ctx context.Context, serverName string) error {
	client, exists := m.clients[serverName]
	if !exists {
		return fmt.Errorf("no client found with name '%s'", serverName)
	}

	err := client.Restart(ctx)
	if err != nil {
		client.Disable()
		m.setError(serverName, "Error restarting connection to server", err)
		return err
	}

	return nil
}

// UpdateServers updates the connections based on the provided map of server configurations
func (m *MCPManager) UpdateServers(mcpServers map[string]MCPClientOptions) {
	m.readyMu.Lock()
	m.ready = false

	// Reset the readyChan if it was already closed
	select {
	case <-m.readyChan:
		m.readyChan = make(chan struct{})
	default:
		// Channel already open, no need to recreate
	}
	m.readyMu.Unlock()

	// Get current server names
	currentServers := make(map[string]bool)
	for name := range m.clients {
		currentServers[name] = true
	}

	// Track new operations for concurrency
	var wg sync.WaitGroup

	// Connect to new or updated servers
	for serverName, config := range mcpServers {
		wg.Add(1)
		go func(name string, cfg MCPClientOptions) {
			defer wg.Done()
			m.Connect(name, cfg)
			// Remove from current servers since we're handling it
			delete(currentServers, name)
		}(serverName, config)
	}

	// Disconnect servers that are no longer in the config
	for serverName := range currentServers {
		wg.Add(1)
		go func(name string) {
			defer wg.Done()
			m.Disconnect(name)
		}(serverName)
	}

	// Wait for all operations to complete
	wg.Wait()

	// Mark as ready and notify listeners
	m.readyMu.Lock()
	m.ready = true
	close(m.readyChan)
	m.readyMu.Unlock()
}

// Tool represents a tool that can be used by the MCP client
// This is a placeholder type - replace with your actual Tool type
type Tool interface{}

// GetActiveTools retrieves all tools from all connected and enabled MCP clients
func (m *MCPManager) GetActiveTools(ctx context.Context, gk *genkit.Genkit) ([]ai.Tool, error) {
	if err := m.WaitForReady(ctx); err != nil {
		return nil, fmt.Errorf("manager not ready: %w", err)
	}

	var allTools []ai.Tool
	var mu sync.Mutex
	var wg sync.WaitGroup
	var errors []error

	for serverName, client := range m.clients {
		if !client.IsEnabled() || m.hasError(serverName) {
			continue
		}

		wg.Add(1)
		go func(name string, c *GenkitMCPClient) {
			defer wg.Done()

			tools, err := c.GetActiveTools(ctx, gk)
			if err != nil {
				mu.Lock()
				errors = append(errors, fmt.Errorf("error fetching tools from client %s: %w", name, err))
				mu.Unlock()
				return
			}

			mu.Lock()
			allTools = append(allTools, tools...)
			mu.Unlock()
		}(serverName, client)
	}

	wg.Wait()

	if len(errors) > 0 {
		return allTools, fmt.Errorf("errors occurred while fetching tools")
	}

	return allTools, nil
}

// getToolsFromClient is a placeholder method to fetch tools from a client
// This will need to be implemented based on your actual tool representation
func (m *MCPManager) getToolsFromClient(ctx context.Context, client *GenkitMCPClient) ([]Tool, error) {
	// This is a placeholder implementation
	// In a real implementation, you would call methods on the client to get tools
	return []Tool{}, nil
}

// Prompt represents a prompt that can be used by the MCP client
// This is a placeholder type - replace with your actual Prompt type
type Prompt interface{}

// GetPrompt retrieves a specific prompt from a specific server
func (m *MCPManager) GetPrompt(ctx context.Context, serverName, promptName string) (Prompt, error) {
	if err := m.WaitForReady(ctx); err != nil {
		return nil, fmt.Errorf("manager not ready: %w", err)
	}

	client, exists := m.clients[serverName]
	if !exists {
		return nil, fmt.Errorf("no client found with name '%s'", serverName)
	}

	if m.hasError(serverName) {
		return nil, fmt.Errorf("client '%s' is in an error state", serverName)
	}

	if !client.IsEnabled() {
		return nil, fmt.Errorf("client '%s' is disabled", serverName)
	}

	// Note: This is a placeholder for a method that doesn't exist yet
	// You'll need to implement GetPrompt on the GenkitMCPClient
	prompt, err := m.getPromptFromClient(ctx, client, promptName)
	if err != nil {
		return nil, fmt.Errorf("unable to fetch prompt '%s' from server '%s': %w", promptName, serverName, err)
	}

	return prompt, nil
}

// getPromptFromClient is a placeholder method to fetch a prompt from a client
// This will need to be implemented based on your actual prompt representation
func (m *MCPManager) getPromptFromClient(ctx context.Context, client *GenkitMCPClient, promptName string) (Prompt, error) {
	// This is a placeholder implementation
	// In a real implementation, you would call methods on the client to get the prompt
	return nil, fmt.Errorf("not implemented")
}

// Helper method to track client errors without logging
func (m *MCPManager) setError(serverName, message string, detail interface{}) {
	state := &ClientState{}
	state.Error.Message = message
	state.Error.Detail = detail

	m.clientStates[serverName] = state
}

// Check if a client has an error
func (m *MCPManager) hasError(serverName string) bool {
	state, exists := m.clientStates[serverName]
	return exists && state.Error.Message != ""
}
