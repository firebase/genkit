// Copyright 2026 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// MCPServerOptions holds configuration for GenkitMCPServer
type MCPServerOptions struct {
	Name    string
	Title   string
	Version string
}

// GenkitMCPServer represents an MCP server that exposes Genkit tools and resources
type GenkitMCPServer struct {
	genkit  *genkit.Genkit
	options MCPServerOptions
	server  *mcp.Server
}

func NewMCPServer(g *genkit.Genkit, opts MCPServerOptions) *GenkitMCPServer {
	if opts.Version == "" {
		opts.Version = "1.0.0"
	}

	return &GenkitMCPServer{
		genkit:  g,
		options: opts,
	}
}

func (s *GenkitMCPServer) setup() error {
	if s.server != nil {
		return nil
	}

	s.server = mcp.NewServer(&mcp.Implementation{
		Name:    s.options.Name,
		Title:   s.options.Title,
		Version: s.options.Version,
	}, &mcp.ServerOptions{
		Capabilities: &mcp.ServerCapabilities{
			Resources: &mcp.ResourceCapabilities{
				ListChanged: true,
			},
			Tools: &mcp.ToolCapabilities{
				ListChanged: true,
			},
		},
	})

	tools := genkit.ListTools(s.genkit)
	for _, t := range tools {
		mcpTool := s.toMCPTool(t)
		s.server.AddTool(mcpTool, s.createToolHandler(t))
	}

	resources := genkit.ListResources(s.genkit)
	for _, r := range resources {
		if err := s.registerResource(r); err != nil {
			return err
		}
	}

	// TODO: add prompt

	return nil
}

func (s *GenkitMCPServer) toMCPTool(t ai.Tool) *mcp.Tool {
	def := t.Definition()
	return &mcp.Tool{
		Name:        def.Name,
		Description: def.Description,
		InputSchema: def.InputSchema,
	}
}

func (s *GenkitMCPServer) createToolHandler(t ai.Tool) mcp.ToolHandler {
	return func(ctx context.Context, req *mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return tracing.RunInNewSpan(ctx, &tracing.SpanMetadata{
			Name:    "mcp.server.call_tool",
			Type:    "action",
			Subtype: "tool",
			IsRoot:  true,
			Metadata: map[string]string{
				"tool": t.Name(),
			},
		}, req, func(ctx context.Context, _ *mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			var args map[string]any

			if len(req.Params.Arguments) > 0 {
				if err := json.Unmarshal(req.Params.Arguments, &args); err != nil {
					return nil, fmt.Errorf("invalid arguments: %w", err)
				}
			}

			res, err := t.RunRaw(ctx, args)
			if err != nil {
				return &mcp.CallToolResult{
					IsError: true,
					Content: []mcp.Content{&mcp.TextContent{Text: err.Error()}},
				}, nil
			}

			var text string
			if s, ok := res.(string); ok {
				text = s
			} else {
				bytes, err := json.Marshal(res)
				if err != nil {
					return nil, fmt.Errorf("failed to marshal tool result: %w", err)
				}
				text = string(bytes)
			}
			return &mcp.CallToolResult{
				Content: []mcp.Content{&mcp.TextContent{Text: text}},
			}, nil
		})
	}
}

func (s *GenkitMCPServer) registerResource(resource ai.Resource) error {
	action, ok := resource.(api.Action)
	if !ok {
		return nil
	}
	desc := action.Desc()

	var uri string
	var isTemplate bool

	// Check metadata for URI/Template.
	if resourceMeta := desc.Metadata["resource"]; resourceMeta != nil {
		if meta, ok := resourceMeta.(map[string]any); ok {
			if u, ok := meta["uri"].(string); ok && u != "" {
				uri = u
			} else if t, ok := meta["template"].(string); ok && t != "" {
				uri = t
				isTemplate = true
			}
		} else {
			bytes, err := json.Marshal(resourceMeta)
			if err == nil {
				var meta struct {
					URI      string `json:"uri"`
					Template string `json:"template"`
				}
				if err := json.Unmarshal(bytes, &meta); err == nil {
					if meta.URI != "" {
						uri = meta.URI
					} else if meta.Template != "" {
						uri = meta.Template
						isTemplate = true
					}
				}
			}
		}
	}

	if uri == "" {
		return nil
	}

	h := s.createResourceHandler(resource)
	if isTemplate {
		s.server.AddResourceTemplate(&mcp.ResourceTemplate{
			URITemplate: uri,
			Name:        desc.Name,
			Description: desc.Description,
		}, h)
	} else {
		s.server.AddResource(&mcp.Resource{
			URI:         uri,
			Name:        desc.Name,
			Description: desc.Description,
		}, h)
	}
	return nil
}

func (s *GenkitMCPServer) createResourceHandler(resource ai.Resource) mcp.ResourceHandler {
	return func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		return tracing.RunInNewSpan(ctx, &tracing.SpanMetadata{
			Name:    "mcp.server.read_resource",
			Type:    "action",
			Subtype: "resource",
			IsRoot:  true,
			Metadata: map[string]string{
				"uri": req.Params.URI,
			},
		}, req, func(ctx context.Context, _ *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
			_, input, err := genkit.FindMatchingResource(s.genkit, req.Params.URI)
			if err != nil {
				return nil, mcp.ResourceNotFoundError(req.Params.URI)
			}

			out, err := resource.Execute(ctx, input)
			if err != nil {
				return nil, err
			}

			contents, err := s.toMCPResourceContents(req.Params.URI, out.Content)
			if err != nil {
				return nil, err
			}

			return &mcp.ReadResourceResult{Contents: contents}, nil
		})
	}
}

func (s *GenkitMCPServer) toMCPResourceContents(requestURI string, parts []*ai.Part) ([]*mcp.ResourceContents, error) {
	var contents []*mcp.ResourceContents
	for _, p := range parts {
		switch {
		case p.IsText():
			contents = append(contents, &mcp.ResourceContents{
				URI:      requestURI,
				MIMEType: "text/plain",
				Text:     p.Text,
			})
		case p.IsMedia():
			contentType, blob, err := uri.Data(p)
			if err != nil {
				return nil, err
			}
			contents = append(contents, &mcp.ResourceContents{
				URI:      requestURI,
				MIMEType: contentType,
				Blob:     blob,
			})
		case p.IsData():
			contents = append(contents, &mcp.ResourceContents{
				URI:      requestURI,
				MIMEType: "application/json",
				Text:     p.Text,
			})
		}
	}
	return contents, nil
}

func (s *GenkitMCPServer) ServeStdio() error {
	if err := s.setup(); err != nil {
		return err
	}
	return s.server.Run(context.Background(), &mcp.StdioTransport{})
}

// HTTPHandler creates an HTTP handler that serves MCP using SSE.
func (s *GenkitMCPServer) HTTPHandler() (http.Handler, error) {
	if err := s.setup(); err != nil {
		return nil, err
	}

	sseHandler := mcp.NewSSEHandler(func(r *http.Request) *mcp.Server {
		return s.server
	}, nil)

	return sseHandler, nil
}

// ListRegisteredTools returns the names of all tools registered in the server's Genkit instance.
func (s *GenkitMCPServer) ListRegisteredTools() []string {
	tools := genkit.ListTools(s.genkit)
	var names []string
	for _, t := range tools {
		names = append(names, t.Name())
	}
	return names
}

// ListRegisteredResources returns the names of all resources registered in the server's Genkit instance.
func (s *GenkitMCPServer) ListRegisteredResources() []string {
	resources := genkit.ListResources(s.genkit)
	var names []string
	for _, r := range resources {
		names = append(names, r.Name())
	}
	return names
}
