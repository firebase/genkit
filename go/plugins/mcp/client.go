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
	"log"
	"net/http"

	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/client/transport"
	"github.com/mark3labs/mcp-go/mcp"
)

// StdioConfig holds configuration for a stdio-based MCP server process.
type StdioConfig struct {
	Command string
	Env     []string
	Args    []string
}

// SSEConfig contains options for the SSE transport
type SSEConfig struct {
	BaseURL    string
	Headers    map[string]string
	HTTPClient *http.Client // Optional custom HTTP client
}

// MCPClientOptions holds configuration for the MCPClient.
type MCPClientOptions struct {
	// Name for this client instance - ideally a nickname for the server
	Name string
	// Version number for this client (defaults to "1.0.0" if empty)
	Version string

	// Disabled flag to temporarily disable this client
	Disabled bool

	// Transport options - only one should be provided

	// Stdio contains config for starting a local server process using stdio transport
	Stdio *StdioConfig

	// SSE contains config for connecting to a remote server via SSE transport
	SSE *SSEConfig
}

// ServerRef represents an active connection to an MCP server
type ServerRef struct {
	Client    *client.Client
	Transport transport.Interface
	Error     string
}

// GenkitMCPClient represents a client for interacting with MCP servers.
type GenkitMCPClient struct {
	options MCPClientOptions
	server  *ServerRef
}

// NewGenkitMCPClient creates a new GenkitMCPClient with the given options.
// Returns an error if the initial connection fails.
func NewGenkitMCPClient(options MCPClientOptions) (*GenkitMCPClient, error) {
	// Set default values
	if options.Name == "" {
		options.Name = "unnamed"
	}
	if options.Version == "" {
		options.Version = "1.0.0"
	}

	client := &GenkitMCPClient{
		options: options,
	}

	if err := client.connect(options); err != nil {
		return nil, fmt.Errorf("failed to initialize MCP client: %w", err)
	}

	return client, nil
}

// connect establishes a connection to an MCP server
func (c *GenkitMCPClient) connect(options MCPClientOptions) error {
	// Close existing connection if any
	if c.server != nil {
		if err := c.server.Transport.Close(); err != nil {
			log.Printf("Warning: error closing previous transport: %v", err)
		}
	}

	// Create and configure transport
	transport, err := c.createTransport(options)
	if err != nil {
		return err
	}

	// Start the transport
	ctx := context.Background()
	if err := transport.Start(ctx); err != nil {
		return fmt.Errorf("failed to start transport: %w", err)
	}

	// Create MCP client
	mcpClient := client.NewClient(transport)

	// Initialize the client if not disabled
	var serverError string
	if !options.Disabled {
		serverError = c.initializeClient(ctx, mcpClient, options.Version)
	}

	c.server = &ServerRef{
		Client:    mcpClient,
		Transport: transport,
		Error:     serverError,
	}

	return nil
}

// createTransport creates the appropriate transport based on client options
func (c *GenkitMCPClient) createTransport(options MCPClientOptions) (transport.Interface, error) {
	if options.Stdio != nil {
		return transport.NewStdio(options.Stdio.Command, options.Stdio.Env, options.Stdio.Args...), nil
	}

	if options.SSE != nil {
		var sseOptions []transport.ClientOption
		if options.SSE.Headers != nil {
			sseOptions = append(sseOptions, transport.WithHeaders(options.SSE.Headers))
		}
		if options.SSE.HTTPClient != nil {
			sseOptions = append(sseOptions, transport.WithHTTPClient(options.SSE.HTTPClient))
		}

		return transport.NewSSE(options.SSE.BaseURL, sseOptions...)
	}

	return nil, fmt.Errorf("no valid transport configuration provided: must specify Stdio or SSE")
}

// initializeClient initializes the MCP client connection
func (c *GenkitMCPClient) initializeClient(ctx context.Context, mcpClient *client.Client, version string) string {
	initReq := mcp.InitializeRequest{
		Params: struct {
			ProtocolVersion string                 `json:"protocolVersion"`
			Capabilities    mcp.ClientCapabilities `json:"capabilities"`
			ClientInfo      mcp.Implementation     `json:"clientInfo"`
		}{
			ProtocolVersion: mcp.LATEST_PROTOCOL_VERSION,
			ClientInfo: mcp.Implementation{
				Name:    "genkit-mcp-client",
				Version: version,
			},
			Capabilities: mcp.ClientCapabilities{},
		},
	}

	_, err := mcpClient.Initialize(ctx, initReq)
	if err != nil {
		return err.Error()
	}

	return ""
}

// Name returns the client name
func (c *GenkitMCPClient) Name() string {
	return c.options.Name
}

// IsEnabled returns whether the client is enabled
func (c *GenkitMCPClient) IsEnabled() bool {
	return !c.options.Disabled
}

// Disable temporarily disables the client
func (c *GenkitMCPClient) Disable() {
	if !c.options.Disabled {
		c.options.Disabled = true
	}
}

// Reenable re-enables a previously disabled client
func (c *GenkitMCPClient) Reenable() {
	if c.options.Disabled {
		c.options.Disabled = false
	}
}

// Restart restarts the transport connection
func (c *GenkitMCPClient) Restart(ctx context.Context) error {
	if c.server != nil {
		if err := c.server.Transport.Close(); err != nil {
			log.Printf("Warning: error closing transport during restart: %v", err)
		}
		c.server = nil
	}
	return c.connect(c.options)
}

// Disconnect closes the connection to the MCP server
func (c *GenkitMCPClient) Disconnect() error {
	if c.server != nil {
		err := c.server.Transport.Close()
		c.server = nil
		return err
	}
	return nil
}
