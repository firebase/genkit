// Package mcp provides a Genkit plugin for integration with the Model Context Protocol.
package mcp

import (
	"context"
	"encoding/json"
	"fmt" // Keep net/url as it might be used by SSE/WebSocket if uncommented later
	"log"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/invopop/jsonschema"
	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/client/transport"
	"github.com/mark3labs/mcp-go/mcp"
	// "github.com/mark3labs/mcp-go/server" // Unused import
)

// StdioConfig holds configuration for a stdio-based MCP server process.
type StdioConfig struct {
	Command string
	Env     []string
	Args    []string
}

// MCPClientOptions holds configuration for the MCPPlugin.
type MCPClientOptions struct {
	// ServerName for this plugin instance, used for naming tools (defaults to "mcp" if empty in Init)
	ServerName string
	// Version number for this client (defaults to "1.0.0" if empty in Init)
	Version string
	// ServerProcess contains config for starting a local server process using stdio
	ServerProcess *StdioConfig
	// ServerURL for connecting to a remote server via SSE transport
	ServerURL string
	// ServerWebsocketURL for connecting to a remote server via WebSocket
	ServerWebsocketURL string // This transport seems unavailable in the current mcp-go version
	// RawToolResponses returns tool responses in raw MCP form if true
	RawToolResponses bool
}

// MCP represents the MCP plugin that implements the genkit.Plugin interface.
type MCP struct {
	// clients stores all the MCP clients created by this plugin
	clients []*MCPPlugin
}

// Name returns the unique name of this plugin.
// This implements the genkit.Plugin interface.
func (p *MCP) Name() string {
	return "mcp"
}

// Init implements the trivial initialization required by the genkit.Plugin interface.
// The actual initialization work is deferred to NewClient.
func (p *MCP) Init(ctx context.Context, g *genkit.Genkit) error {
	// Init is now trivial - just returns nil
	return nil
}

// NewClient creates a new MCP client with the given options and registers it with Genkit.
// This handles all the initialization that was previously in Init().
func (p *MCP) NewClient(options MCPClientOptions, g *genkit.Genkit) (*MCPPlugin, error) {
	ctx := context.Background()

	log.Println("Creating new MCP client plugin...")
	// Create the new MCP client plugin
	mcpPlugin := &MCPPlugin{
		options: options,
	}

	// Set default version if not provided
	if mcpPlugin.options.Version == "" {
		log.Println("Using default version 1.0.0")
		mcpPlugin.options.Version = "1.0.0"
	}
	// Set default name if not provided
	if mcpPlugin.options.ServerName == "" {
		log.Println("Using default server name 'unnamed'")
		mcpPlugin.options.ServerName = "unnamed"
	}

	// Create transport based on options
	var t transport.Interface
	var err error

	log.Println("Setting up transport...")
	if mcpPlugin.options.ServerProcess != nil {
		log.Printf("Creating stdio transport with command: %s", mcpPlugin.options.ServerProcess.Command)
		// Create stdio transport
		t = transport.NewStdio(mcpPlugin.options.ServerProcess.Command, mcpPlugin.options.ServerProcess.Env, mcpPlugin.options.ServerProcess.Args...)
		if err := t.Start(ctx); err != nil { // Must start the transport
			return nil, fmt.Errorf("failed to start stdio transport: %w", err)
		}
		log.Println("Stdio transport started successfully")
	} else if mcpPlugin.options.ServerURL != "" {
		log.Printf("Creating SSE transport with URL: %s", mcpPlugin.options.ServerURL)
		// Create SSE transport
		t, err = transport.NewSSE(mcpPlugin.options.ServerURL)
		if err != nil {
			return nil, fmt.Errorf("failed to create SSE transport: %w", err)
		}
		if err := t.Start(ctx); err != nil {
			return nil, fmt.Errorf("failed to start SSE transport: %w", err)
		}
		log.Println("SSE transport started successfully")
	} else {
		return nil, fmt.Errorf("no valid transport configuration provided: must specify ServerProcess or ServerURL")
	}

	log.Println("Creating MCP client...")
	// Create MCP client
	mcpPlugin.client = client.NewClient(t)

	log.Println("Initializing MCP client...")
	// Initialize the client
	initReq := mcp.InitializeRequest{
		Params: struct {
			ProtocolVersion string                 `json:"protocolVersion"`
			Capabilities    mcp.ClientCapabilities `json:"capabilities"`
			ClientInfo      mcp.Implementation     `json:"clientInfo"`
		}{
			ProtocolVersion: mcp.LATEST_PROTOCOL_VERSION,
			ClientInfo: mcp.Implementation{
				Name:    "genkit-mcp-plugin",
				Version: mcpPlugin.options.Version,
			},
			// Capabilities: mcp.ClientCapabilities{}, // Optionally specify client capabilities
		},
	}
	initResult, err := mcpPlugin.client.Initialize(ctx, initReq)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize MCP client: %w", err)
	}
	log.Println("MCP client initialized successfully")

	// Get server capabilities from InitializeResult
	capabilities := initResult.Capabilities

	log.Println("Registering components based on server capabilities...")
	// Register tools, prompts, and resources based on capabilities
	if capabilities.Tools != nil {
		log.Println("Registering tools...")
		if err := mcpPlugin.registerTools(ctx, g); err != nil {
			return nil, err
		}
	}

	if capabilities.Prompts != nil {
		log.Println("Registering prompts...")
		if err := mcpPlugin.registerPrompts(ctx, g); err != nil {
			return nil, err
		}
	}

	if capabilities.Resources != nil {
		log.Println("Registering resources...")
		if err := mcpPlugin.registerResources(ctx, g); err != nil {
			return nil, err
		}
	}

	// Add the client to the list of clients
	p.clients = append(p.clients, mcpPlugin)
	log.Println("MCP client setup completed successfully")

	return mcpPlugin, nil
}

// MCPPlugin represents a specific MCP client instance.
type MCPPlugin struct {
	options MCPClientOptions
	client  *client.Client
}

// Helper methods for registering MCP components
func (p *MCPPlugin) registerTools(ctx context.Context, g *genkit.Genkit) error {
	var cursor mcp.Cursor

	for {
		listReq := mcp.ListToolsRequest{
			PaginatedRequest: mcp.PaginatedRequest{
				Params: struct {
					Cursor mcp.Cursor `json:"cursor,omitempty"`
				}{
					Cursor: cursor,
				},
			},
		}
		result, err := p.client.ListTools(ctx, listReq)
		if err != nil {
			return fmt.Errorf("failed to list tools: %w", err)
		}

		for _, mcpTool := range result.Tools {
			log.Printf("Registering MCP Tool: %s, InputSchema Type: %s", mcpTool.Name, mcpTool.InputSchema.Type)

			var inputSchemaForAI *jsonschema.Schema
			if mcpTool.InputSchema.Type != "" { // Check if schema type is defined
				// Marshal the mcp.ToolInputSchema (which embeds mcp.ToolInputSchemaJSON) to JSON bytes
				schemaBytes, err := json.Marshal(mcpTool.InputSchema) // mcpTool.InputSchema is mcp.ToolInputSchema
				if err != nil {
					return fmt.Errorf("failed to marshal MCP input schema for tool %s: %w", mcpTool.Name, err)
				}
				inputSchemaForAI = new(jsonschema.Schema)
				if err := json.Unmarshal(schemaBytes, inputSchemaForAI); err != nil {
					log.Printf("Warning: Failed to unmarshal MCP input schema directly for tool %s: %v. Using empty schema.", mcpTool.Name, err)
					inputSchemaForAI = &jsonschema.Schema{}
				}
			} else {
				log.Printf("MCP Tool %s has no input schema defined (Type is empty). Using empty schema.", mcpTool.Name)
				inputSchemaForAI = &jsonschema.Schema{}
			}

			// Capture mcpTool by value for the closure
			currentMCPTool := mcpTool
			toolFunc := func(toolCtx *ai.ToolContext, args interface{}) (interface{}, error) {
				log.Printf("Executing MCP tool (via ai.DefineToolWithInputSchema) %q", currentMCPTool.Name)
				log.Printf("Raw input args: %+v (type: %T)", args, args)

				var callToolArgs map[string]interface{}
				if args != nil {
					jsonBytes, jsonErr := json.Marshal(args)
					if jsonErr != nil {
						log.Printf("Failed to marshal args to JSON for tool %s: %v", currentMCPTool.Name, jsonErr)
						return nil, fmt.Errorf("tool arguments must be marshallable to map[string]interface{}, got %T (marshal error: %v)", args, jsonErr)
					}
					if err := json.Unmarshal(jsonBytes, &callToolArgs); err != nil {
						log.Printf("Failed to unmarshal JSON args to map[string]any for tool %s: %v. Args: %s", currentMCPTool.Name, err, string(jsonBytes))
						return nil, fmt.Errorf("tool arguments could not be converted to map[string]interface{} for tool %s (re-marshal/unmarshal error: %v)", currentMCPTool.Name, err)
					}
					log.Printf("Successfully converted args for tool %s via JSON marshal/unmarshal: %+v", currentMCPTool.Name, callToolArgs)
				}

				callReq := mcp.CallToolRequest{
					Params: struct {
						Name      string         `json:"name"`
						Arguments map[string]any `json:"arguments,omitempty"`
						Meta      *mcp.Meta      `json:"_meta,omitempty"`
					}{
						Name:      currentMCPTool.Name,
						Arguments: callToolArgs,
						Meta:      nil,
					},
				}

				log.Printf("Calling MCP tool %q with request: %+v", currentMCPTool.Name, callReq)
				mcpResult, err := p.client.CallTool(toolCtx, callReq)
				if err != nil {
					log.Printf("Tool %q execution failed: %v", currentMCPTool.Name, err)
					return nil, fmt.Errorf("failed to call tool %s: %w", currentMCPTool.Name, err)
				}
				log.Printf("Tool %q execution succeeded with result: %+v", currentMCPTool.Name, mcpResult)

				if p.options.RawToolResponses {
					log.Printf("Returning raw tool response for %s", currentMCPTool.Name)
					return mcpResult, nil
				}
				log.Printf("Processing tool result for %s", currentMCPTool.Name)
				return p.processToolResult(mcpResult)
			}

			ai.DefineToolWithInputSchema(
				g.Registry(), // Pass the registry from genkit.Genkit
				mcpTool.Name,
				mcpTool.Description,
				inputSchemaForAI,
				toolFunc,
			)
			log.Printf("Successfully registered tool %s with explicit input schema using ai.DefineToolWithInputSchema.", mcpTool.Name)
		}

		cursor = result.NextCursor
		if cursor == "" {
			break
		}
	}
	return nil
}

func (p *MCPPlugin) processToolResult(result *mcp.CallToolResult) (interface{}, error) {
	if result.IsError {
		errorMsg := "tool error"
		if len(result.Content) > 0 {
			tempMsg := p.contentToText(result.Content)
			if tempMsg != "" {
				errorMsg = tempMsg
			}
		}
		return nil, fmt.Errorf("tool error: %s", errorMsg)
	}

	isAllText := true
	if len(result.Content) == 0 {
		isAllText = false
	}
	for _, contentItem := range result.Content {
		textContent, ok := contentItem.(mcp.TextContent)
		if !ok || textContent.Type != "text" {
			isAllText = false
			break
		}
	}

	if isAllText {
		text := p.contentToText(result.Content)
		trimmedText := strings.TrimSpace(text)
		if strings.HasPrefix(trimmedText, "{") || strings.HasPrefix(trimmedText, "[") {
			var jsonData interface{}
			if err := json.Unmarshal([]byte(trimmedText), &jsonData); err == nil {
				return jsonData, nil
			}
		}
		return text, nil
	}

	if len(result.Content) == 1 {
		contentItem := result.Content[0]
		if tc, ok := contentItem.(mcp.TextContent); ok && tc.Type == "text" {
			trimmedText := strings.TrimSpace(tc.Text)
			if strings.HasPrefix(trimmedText, "{") || strings.HasPrefix(trimmedText, "[") {
				var jsonData interface{}
				if err := json.Unmarshal([]byte(trimmedText), &jsonData); err == nil {
					return jsonData, nil
				}
			}
			return tc.Text, nil
		}
		if ec, ok := contentItem.(mcp.EmbeddedResource); ok && ec.Type == "resource" {
			if trc, ok := ec.Resource.(mcp.TextResourceContents); ok && trc.MIMEType == "application/json" {
				var jsonData interface{}
				if err := json.Unmarshal([]byte(trc.Text), &jsonData); err == nil {
					return jsonData, nil
				}
			}
		}
		return contentItem, nil
	}

	return result.Content, nil
}

func (p *MCPPlugin) contentToText(contentList []mcp.Content) string {
	var textParts []string
	for _, contentItem := range contentList {
		if textContent, ok := contentItem.(mcp.TextContent); ok && textContent.Type == "text" {
			textParts = append(textParts, textContent.Text)
		} else if erContent, ok := contentItem.(mcp.EmbeddedResource); ok {
			if trc, ok := erContent.Resource.(mcp.TextResourceContents); ok {
				textParts = append(textParts, trc.Text)
			}
		}
	}
	return strings.Join(textParts, "")
}

func (p *MCPPlugin) registerPrompts(ctx context.Context, g *genkit.Genkit) error {
	// Placeholder
	return nil
}

// decodeToolArgs is a helper to unmarshal tool arguments from interface{} into a struct.
func decodeToolArgs(args interface{}, out interface{}) error {
	if args == nil {
		return nil
	}
	jsonBytes, err := json.Marshal(args)
	if err != nil {
		return fmt.Errorf("failed to marshal tool arguments: %w", err)
	}
	if err := json.Unmarshal(jsonBytes, out); err != nil {
		return fmt.Errorf("failed to unmarshal tool arguments: %w", err)
	}
	return nil
}

// Input struct for the listResources tool
type listResourcesInput struct {
	Cursor string `json:"cursor,omitempty"`
	All    bool   `json:"all,omitempty"`
}

// Input struct for the listResourceTemplates tool
type listResourceTemplatesInput struct {
	Cursor string `json:"cursor,omitempty"`
	All    bool   `json:"all,omitempty"`
}

// Input struct for the readResource tool
type readResourceInput struct {
	URI string `json:"uri"`
}

func (p *MCPPlugin) registerResources(ctx context.Context, g *genkit.Genkit) error {
	// Define listResources tool
	genkit.DefineTool(g, fmt.Sprintf("%s/listResources", p.options.ServerName), fmt.Sprintf("list all available resources for '%s'", p.options.ServerName),
		func(toolCtx *ai.ToolContext, args interface{}) (interface{}, error) {
			input := listResourcesInput{}
			if err := decodeToolArgs(args, &input); err != nil {
				return nil, err
			}

			if !input.All {
				req := mcp.ListResourcesRequest{
					PaginatedRequest: mcp.PaginatedRequest{
						Params: struct {
							Cursor mcp.Cursor `json:"cursor,omitempty"`
						}{
							Cursor: mcp.Cursor(input.Cursor),
						},
					},
				}
				return p.client.ListResources(toolCtx.Context, req)
			}

			var allResources []mcp.Resource
			currentCursor := mcp.Cursor(input.Cursor)
			for {
				req := mcp.ListResourcesRequest{
					PaginatedRequest: mcp.PaginatedRequest{
						Params: struct {
							Cursor mcp.Cursor `json:"cursor,omitempty"`
						}{
							Cursor: currentCursor,
						},
					},
				}
				resp, err := p.client.ListResources(toolCtx.Context, req)
				if err != nil {
					return nil, fmt.Errorf("failed to list resources page: %w", err)
				}
				if resp != nil {
					allResources = append(allResources, resp.Resources...)
					currentCursor = resp.NextCursor
					if currentCursor == "" {
						break
					}
				} else {
					break
				}
			}
			return map[string]interface{}{"resources": allResources}, nil
		})

	// Define listResourceTemplates tool
	genkit.DefineTool(g, fmt.Sprintf("%s/listResourceTemplates", p.options.ServerName), fmt.Sprintf("list all available resource templates for '%s'", p.options.ServerName),
		func(toolCtx *ai.ToolContext, args interface{}) (interface{}, error) {
			input := listResourceTemplatesInput{}
			if err := decodeToolArgs(args, &input); err != nil {
				return nil, err
			}

			if !input.All {
				req := mcp.ListResourceTemplatesRequest{
					PaginatedRequest: mcp.PaginatedRequest{
						Params: struct {
							Cursor mcp.Cursor `json:"cursor,omitempty"`
						}{
							Cursor: mcp.Cursor(input.Cursor),
						},
					},
				}
				return p.client.ListResourceTemplates(toolCtx.Context, req)
			}

			var allTemplates []mcp.ResourceTemplate
			currentCursor := mcp.Cursor(input.Cursor)
			for {
				req := mcp.ListResourceTemplatesRequest{
					PaginatedRequest: mcp.PaginatedRequest{
						Params: struct {
							Cursor mcp.Cursor `json:"cursor,omitempty"`
						}{
							Cursor: currentCursor,
						},
					},
				}
				resp, err := p.client.ListResourceTemplates(toolCtx.Context, req)
				if err != nil {
					return nil, fmt.Errorf("failed to list resource templates page: %w", err)
				}
				if resp != nil {
					allTemplates = append(allTemplates, resp.ResourceTemplates...)
					currentCursor = resp.NextCursor
					if currentCursor == "" {
						break
					}
				} else {
					break
				}
			}
			return map[string]interface{}{"resourceTemplates": allTemplates}, nil
		})

	// Define readResource tool
	genkit.DefineTool(g, fmt.Sprintf("%s/readResource", p.options.ServerName), fmt.Sprintf("this tool can read resources from '%s'", p.options.ServerName),
		func(toolCtx *ai.ToolContext, args interface{}) (interface{}, error) {
			input := readResourceInput{}
			if err := decodeToolArgs(args, &input); err != nil {
				return nil, err
			}
			if input.URI == "" {
				return nil, fmt.Errorf("uri parameter is required for readResource")
			}

			req := mcp.ReadResourceRequest{
				Params: struct {
					URI       string         `json:"uri"`
					Arguments map[string]any `json:"arguments,omitempty"`
				}{
					URI:       input.URI,
					Arguments: nil,
				},
			}
			return p.client.ReadResource(toolCtx.Context, req)
		})

	return nil
}
