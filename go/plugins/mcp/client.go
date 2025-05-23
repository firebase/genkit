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
// Unlike the original MCPClient, this doesn't implement the genkit.Plugin interface.
type GenkitMCPClient struct {
	options        MCPClientOptions
	server         *ServerRef
	ready          bool
	readyListeners []struct {
		resolve func()
		reject  func(error)
	}
}

// NewGenkitMCPClient creates a new GenkitMCPClient with the given options.
func NewGenkitMCPClient(options MCPClientOptions) *GenkitMCPClient {
	// Set default values
	if options.Name == "" {
		options.Name = "unnamed"
	}
	if options.Version == "" {
		options.Version = "1.0.0"
	}

	client := &GenkitMCPClient{
		options: options,
		ready:   false,
		readyListeners: []struct {
			resolve func()
			reject  func(error)
		}{},
	}

	// Initialize the connection
	go client.initializeConnection()

	return client
}

// initializeConnection initializes the MCP server connection
func (c *GenkitMCPClient) initializeConnection() {
	c.ready = false

	err := c.connect(c.options)
	if err != nil {
		log.Printf("Failed to initialize MCP connection: %v", err)
		// Notify listeners of failure
		for _, listener := range c.readyListeners {
			listener.reject(err)
		}
		c.readyListeners = nil
		return
	}

	// Mark as ready and notify listeners
	c.ready = true
	for _, listener := range c.readyListeners {
		listener.resolve()
	}
	c.readyListeners = nil
}

// Ready returns a channel that is closed when the client is ready
func (c *GenkitMCPClient) Ready() <-chan struct{} {
	ch := make(chan struct{})
	if c.ready {
		close(ch)
		return ch
	}

	c.readyListeners = append(c.readyListeners, struct {
		resolve func()
		reject  func(error)
	}{
		resolve: func() { close(ch) },
		reject:  func(error) { close(ch) },
	})

	return ch
}

// WaitForReady blocks until the client is ready or returns an error
func (c *GenkitMCPClient) WaitForReady(ctx context.Context) error {
	if c.ready {
		return nil
	}

	errCh := make(chan error, 1)
	readyCh := make(chan struct{})

	c.readyListeners = append(c.readyListeners, struct {
		resolve func()
		reject  func(error)
	}{
		resolve: func() { close(readyCh) },
		reject:  func(err error) { errCh <- err },
	})

	select {
	case <-readyCh:
		return nil
	case err := <-errCh:
		return err
	case <-ctx.Done():
		return ctx.Err()
	}
}

// connect establishes a connection to an MCP server
func (c *GenkitMCPClient) connect(options MCPClientOptions) error {
	if c.server != nil {
		if err := c.server.Transport.Close(); err != nil {
			log.Printf("Warning: error closing previous transport: %v", err)
		}
	}

	log.Printf("[MCP Client] Connecting to MCP server '%s'", options.Name)

	// Create transport based on options
	var t transport.Interface
	var err error

	if options.Stdio != nil {
		log.Printf("Creating stdio transport with command: %s", options.Stdio.Command)
		// Create stdio transport
		t = transport.NewStdio(options.Stdio.Command, options.Stdio.Env, options.Stdio.Args...)
	} else if options.SSE != nil {
		log.Printf("Creating SSE transport with URL: %s", options.SSE.BaseURL)
		// Create SSE transport with options
		var sseOptions []transport.ClientOption
		if options.SSE.Headers != nil {
			sseOptions = append(sseOptions, transport.WithHeaders(options.SSE.Headers))
		}
		if options.SSE.HTTPClient != nil {
			sseOptions = append(sseOptions, transport.WithHTTPClient(options.SSE.HTTPClient))
		}

		t, err = transport.NewSSE(options.SSE.BaseURL, sseOptions...)
		if err != nil {
			return fmt.Errorf("failed to create SSE transport: %w", err)
		}
	} else {
		return fmt.Errorf("no valid transport configuration provided: must specify Stdio or SSE")
	}

	// Start the transport
	ctx := context.Background() // Using background context for now
	if err := t.Start(ctx); err != nil {
		return fmt.Errorf("failed to start transport: %w", err)
	}

	// Create MCP client
	mcpClient := client.NewClient(t)

	// Initialize the client
	initReq := mcp.InitializeRequest{
		Params: struct {
			ProtocolVersion string                 `json:"protocolVersion"`
			Capabilities    mcp.ClientCapabilities `json:"capabilities"`
			ClientInfo      mcp.Implementation     `json:"clientInfo"`
		}{
			ProtocolVersion: mcp.LATEST_PROTOCOL_VERSION,
			ClientInfo: mcp.Implementation{
				Name:    "genkit-mcp-client",
				Version: options.Version,
			},
			Capabilities: mcp.ClientCapabilities{},
		},
	}

	var serverError string
	if !options.Disabled {
		// Only attempt to initialize if not disabled
		_, err = mcpClient.Initialize(ctx, initReq)
		if err != nil {
			serverError = err.Error()
			log.Printf("Warning: failed to initialize MCP client: %v", err)
		}
	}

	c.server = &ServerRef{
		Client:    mcpClient,
		Transport: t,
		Error:     serverError,
	}

	return nil
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
		log.Printf("[MCP Client] Disabling MCP client '%s'", c.options.Name)
		c.options.Disabled = true
	}
}

// Reenable re-enables a previously disabled client
func (c *GenkitMCPClient) Reenable() {
	if c.options.Disabled {
		log.Printf("[MCP Client] Re-enabling MCP client '%s'", c.options.Name)
		c.options.Disabled = false
	}
}

// Restart restarts the transport connection
func (c *GenkitMCPClient) Restart(ctx context.Context) error {
	log.Printf("[MCP Client] Restarting connection to MCP server '%s'", c.options.Name)
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
		log.Printf("[MCP Client] Disconnecting from MCP server '%s'", c.options.Name)
		err := c.server.Transport.Close()
		c.server = nil
		return err
	}
	return nil
}

/*
// MCPPlugin implements the genkit.Plugin interface to provide MCP functionality
// as a Genkit plugin while using the GenkitMCPClient underneath
type MCPPlugin struct {
	client *GenkitMCPClient
}

// NewMCPPlugin creates a new MCP plugin with the given options
func NewMCPPlugin(options MCPClientOptions) *MCPPlugin {
	return &MCPPlugin{
		client: NewGenkitMCPClient(options),
	}
}

// Name returns the unique name of this plugin
func (p *MCPPlugin) Name() string {
	return p.client.Name()
}

// Init initializes the MCP plugin and registers it with Genkit
func (p *MCPPlugin) Init(ctx context.Context, g *genkit.Genkit) error {
	// Wait for the client to be ready
	if err := p.client.WaitForReady(ctx); err != nil {
		return fmt.Errorf("failed to initialize MCP client: %w", err)
	}

	// Skip if this client is disabled
	if !p.client.IsEnabled() {
		log.Println("MCP client is disabled, skipping initialization")
		return nil
	}

	log.Println("Registering MCP tools...")
	tools, err := p.client.GetActiveTools(ctx, g)
	if err != nil {
		return fmt.Errorf("failed to register tools: %w", err)
	}

	log.Printf("Registered %d MCP tools", len(tools))
	return nil
}

// GetActiveTools returns all active tools from the underlying client
func (p *MCPPlugin) GetActiveTools(ctx context.Context, g *genkit.Genkit) ([]ai.Tool, error) {
	return p.client.GetActiveTools(ctx, g)
}

// GetPrompt retrieves a prompt from the underlying client
func (p *MCPPlugin) GetPrompt(ctx context.Context, g *genkit.Genkit, promptName string, args map[string]string) (*ai.Prompt, error) {
	return p.client.GetPrompt(ctx, g, promptName, args)
}

// For backward compatibility, keep the original function name
func NewMCPClient(options MCPClientOptions) *MCPPlugin {
	return NewMCPPlugin(options)
}
*/
