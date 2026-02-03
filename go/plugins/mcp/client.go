// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

// Package mcp provides a client for integration with the Model Context Protocol.
package mcp

import (
	"context"
	"fmt"
	"net/http"
	"os/exec"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const DefaultHTTPClientTimeout = 30

// StdioConfig holds configuration for a stdio-based MCP server process
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

// StreamableHTTPConfig contains options for the Streamable HTTP transport
type StreamableHTTPConfig struct {
	BaseURL    string
	Headers    map[string]string
	HTTPClient *http.Client  // Optional custom HTTP client
	Timeout    time.Duration // HTTP request timeout
}

// MCPClientOptions contains options for the Streamable HTTP transport
type MCPClientOptions struct {
	// Name for this client instance
	Name string
	// Version number for this client (defaults to "1.0.0")
	Version string

	// Disabled flag to temporarily disable this client
	Disabled bool

	// Transport options -- only one should be provided

	// Stdio contains config for starting a local server process using stdio transport
	Stdio *StdioConfig

	// SSE contains config for connecting to a remote server via SSE transport
	SSE *SSEConfig

	// StreamableHTTP contains config for connecting to a remote server via Streamable HTTP transport
	StreamableHTTP *StreamableHTTPConfig
}

// ServerRef represents an active connection to an MCP server
type ServerRef struct {
	Session *mcp.ClientSession
	Error   error
}

// GenkitMCPClient represents a client for interacting with MCP servers
type GenkitMCPClient struct {
	options MCPClientOptions
	client  *mcp.Client
	server  *ServerRef
}

// NewClient creates a new GenkitMCPClient with the given options.
func NewClient(ctx context.Context, opts MCPClientOptions) (*GenkitMCPClient, error) {
	if opts.Name == "" {
		opts.Name = "unnamed"
	}
	if opts.Version == "" {
		opts.Version = "1.0.0"
	}

	c := &GenkitMCPClient{
		options: opts,
		client: mcp.NewClient(&mcp.Implementation{
			Name:    opts.Name,
			Version: opts.Version,
		}, nil),
	}

	if err := c.connect(ctx); err != nil {
		return nil, fmt.Errorf("failed to initialize MCP client: %w", err)
	}
	if c.server.Error != nil {
		return nil, c.server.Error
	}

	return c, nil
}

// NewGenkitMCPClient creates a new [GenkitMCPClient] with the given options.
// Deprecated: Use NewClient(ctx, opts) instead.
func NewGenkitMCPClient(opts MCPClientOptions) (*GenkitMCPClient, error) {
	return NewClient(context.Background(), opts)
}

// connect establishes a connection to an MCP server
func (c *GenkitMCPClient) connect(ctx context.Context) error {
	if c.server != nil && c.server.Session != nil {
		if err := c.server.Session.Close(); err != nil {
			logger.FromContext(ctx).Warn("Error closing previous MCP session", "client", c.options.Name, "error", err)
		}
	}

	// if disabled, return without establishing a session
	if c.options.Disabled {
		c.server = nil
		return nil
	}

	transport, err := c.createTransport()
	if err != nil {
		// no transport means no ability to create a server
		c.server = &ServerRef{Error: err}
		return err
	}

	session, err := c.client.Connect(ctx, transport, nil)
	if err != nil {
		c.server = &ServerRef{
			Error: err,
		}
		return fmt.Errorf("failed to connect to MCP server: %w", err)
	}

	c.server = &ServerRef{
		Session: session,
	}

	return nil
}

// headerTransport is a [http.RoundTripper] that adds custom headers to every request
type headerTransport struct {
	rt      http.RoundTripper
	headers map[string]string
}

func (t *headerTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	for k, v := range t.headers {
		req.Header.Set(k, v)
	}
	return t.rt.RoundTrip(req)
}

// wrapHTTPClient wraps an existing client with custom headers
func wrapHTTPClient(client *http.Client, headers map[string]string) *http.Client {
	if len(headers) == 0 {
		if client == nil {
			return http.DefaultClient
		}
		return client
	}

	newClient := &http.Client{}
	if client != nil {
		*newClient = *client
	} else {
		newClient.Timeout = DefaultHTTPClientTimeout * time.Second
	}

	transport := newClient.Transport
	if transport == nil {
		transport = http.DefaultTransport
	}

	newClient.Transport = &headerTransport{
		rt:      transport,
		headers: headers,
	}
	return newClient
}

// createTransport creates the appropriate transport based on client options
func (c *GenkitMCPClient) createTransport() (mcp.Transport, error) {
	if c.options.Stdio != nil {
		cmd := exec.Command(c.options.Stdio.Command, c.options.Stdio.Args...)
		cmd.Env = c.options.Stdio.Env
		return &mcp.CommandTransport{
			Command: cmd,
		}, nil
	}

	if c.options.SSE != nil {
		httpClient := wrapHTTPClient(c.options.SSE.HTTPClient, c.options.SSE.Headers)
		return &mcp.SSEClientTransport{
			Endpoint:   c.options.SSE.BaseURL,
			HTTPClient: httpClient,
		}, nil
	}

	if c.options.StreamableHTTP != nil {
		httpClient := wrapHTTPClient(c.options.StreamableHTTP.HTTPClient, c.options.StreamableHTTP.Headers)
		return &mcp.StreamableClientTransport{
			Endpoint:   c.options.StreamableHTTP.BaseURL,
			HTTPClient: httpClient,
		}, nil
	}

	return nil, fmt.Errorf("no valid transport configuration provided: must specify Stdio, SSE or StreamableHTTP")
}

// Name returns the name of the client
func (c *GenkitMCPClient) Name() string {
	return c.options.Name
}

// IsEnabled return whether the client is enabled
func (c *GenkitMCPClient) IsEnabled() bool {
	return !c.options.Disabled
}

// Disable temporarily disables the client by closing the connection
func (c *GenkitMCPClient) Disable() {
	if !c.options.Disabled {
		c.options.Disabled = true
		c.Disconnect()
	}
}

// ReenableWithContext re-enables a previously disabled client by reconnecting it.
func (c *GenkitMCPClient) ReenableWithContext(ctx context.Context) error {
	if c.options.Disabled {
		c.options.Disabled = false
		return c.connect(ctx)
	}
	return nil
}

// Reenable re-enables a previously disabled client by reconnecting it.
// Deprecated: Use ReenableWithContext instead.
func (c *GenkitMCPClient) Reenable() {
	_ = c.ReenableWithContext(context.Background())
}

// Restart restarts the transport connection
func (c *GenkitMCPClient) Restart(ctx context.Context) error {
	if err := c.Disconnect(); err != nil {
		logger.FromContext(ctx).Warn("Error closing MCP session during restart", "client", c.options.Name, "error", err)
	}
	return c.connect(ctx)
}

// Disconnect closes the session with the MCP server
func (c *GenkitMCPClient) Disconnect() error {
	if c.server != nil && c.server.Session != nil {
		err := c.server.Session.Close()
		c.server = nil
		return err
	}
	return nil
}
