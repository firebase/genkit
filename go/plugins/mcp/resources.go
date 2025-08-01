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
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/mark3labs/mcp-go/mcp"
)

// GetActiveResources fetches detached resources from the MCP server
func (c *GenkitMCPClient) GetActiveResources(ctx context.Context) ([]core.DetachedResourceAction, error) {
	if !c.IsEnabled() || c.server == nil {
		return nil, fmt.Errorf("MCP client is disabled or not connected")
	}

	var resources []core.DetachedResourceAction

	// List static resources from MCP server
	listReq := mcp.ListResourcesRequest{}
	listResp, err := c.server.Client.ListResources(ctx, listReq)
	if err != nil {
		return nil, fmt.Errorf("failed to list resources from %s: %w", c.options.Name, err)
	}

	// Create detached resources for each static resource
	for _, mcpResource := range listResp.Resources {
		detachedResource, err := c.createDetachedMCPResource(mcpResource)
		if err != nil {
			return nil, fmt.Errorf("failed to create detached resource %s: %w", mcpResource.Name, err)
		}
		resources = append(resources, detachedResource)
	}

	// List resource templates from MCP server
	templateReq := mcp.ListResourceTemplatesRequest{}
	templateResp, err := c.server.Client.ListResourceTemplates(ctx, templateReq)
	if err != nil {
		// Resource templates might not be supported by all servers
		return resources, nil // Continue without template resources
	}

	// Create detached resources for each template resource
	for _, mcpTemplate := range templateResp.ResourceTemplates {
		detachedResource, err := c.createDetachedMCPResourceTemplate(mcpTemplate)
		if err != nil {
			return nil, fmt.Errorf("failed to create detached resource template %s: %w", mcpTemplate.Name, err)
		}
		resources = append(resources, detachedResource)
	}

	return resources, nil
}

// createDetachedMCPResource creates a detached Genkit resource from an MCP static resource
func (c *GenkitMCPClient) createDetachedMCPResource(mcpResource mcp.Resource) (core.DetachedResourceAction, error) {
	// Create namespaced resource name
	resourceName := c.GetResourceNameWithNamespace(mcpResource.Name)

	// Create detached Genkit resource that bridges to MCP
	return genkit.DynamicResource(genkit.ResourceOptions{
		Name:        resourceName,
		URI:         mcpResource.URI,
		Description: mcpResource.Description,
		Metadata: map[string]any{
			"mcp_server": c.options.Name,
			"mcp_name":   mcpResource.Name,
			"source":     "mcp",
			"mime_type":  mcpResource.MIMEType,
		},
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		return c.readMCPResource(ctx, input.URI)
	})
}

// createDetachedMCPResourceTemplate creates a detached Genkit template resource from MCP template
func (c *GenkitMCPClient) createDetachedMCPResourceTemplate(mcpTemplate mcp.ResourceTemplate) (core.DetachedResourceAction, error) {
	resourceName := c.GetResourceNameWithNamespace(mcpTemplate.Name)

	// Convert URITemplate to string - extract the raw template string
	var templateStr string
	if mcpTemplate.URITemplate != nil && mcpTemplate.URITemplate.Template != nil {
		templateStr = mcpTemplate.URITemplate.Template.Raw()
	}

	return genkit.DynamicResource(genkit.ResourceOptions{
		Name:        resourceName,
		Template:    templateStr,
		Description: mcpTemplate.Description,
		Metadata: map[string]any{
			"mcp_server":   c.options.Name,
			"mcp_name":     mcpTemplate.Name,
			"mcp_template": templateStr,
			"source":       "mcp",
			"mime_type":    mcpTemplate.MIMEType,
		},
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		return c.readMCPResource(ctx, input.URI)
	})
}

// readMCPResource fetches content from MCP server for a given URI
func (c *GenkitMCPClient) readMCPResource(ctx context.Context, uri string) (genkit.ResourceOutput, error) {
	if !c.IsEnabled() || c.server == nil {
		return genkit.ResourceOutput{}, fmt.Errorf("MCP client is disabled or not connected")
	}

	// Create ReadResource request
	readReq := mcp.ReadResourceRequest{
		Params: struct {
			URI       string                 `json:"uri"`
			Arguments map[string]interface{} `json:"arguments,omitempty"`
		}{
			URI:       uri,
			Arguments: nil,
		},
	}

	// Call the MCP server to read the resource
	readResp, err := c.server.Client.ReadResource(ctx, readReq)
	if err != nil {
		return genkit.ResourceOutput{}, fmt.Errorf("failed to read resource from MCP server %s: %w", c.options.Name, err)
	}

	// Convert MCP ResourceContents to Genkit Parts
	parts, err := convertMCPResourceContentsToGenkitParts(readResp.Contents)
	if err != nil {
		return genkit.ResourceOutput{}, fmt.Errorf("failed to convert MCP resource contents to Genkit parts: %w", err)
	}

	return genkit.ResourceOutput{Content: parts}, nil
}

// convertMCPResourceContentsToGenkitParts converts MCP ResourceContents to Genkit Parts
func convertMCPResourceContentsToGenkitParts(mcpContents []mcp.ResourceContents) ([]*ai.Part, error) {
	var parts []*ai.Part

	for _, content := range mcpContents {
		// Handle TextResourceContents
		if textContent, ok := content.(mcp.TextResourceContents); ok {
			parts = append(parts, ai.NewTextPart(textContent.Text))
			continue
		}

		// Handle BlobResourceContents
		if blobContent, ok := content.(mcp.BlobResourceContents); ok {
			// Create media part using ai.NewMediaPart for binary data
			parts = append(parts, ai.NewMediaPart(blobContent.MIMEType, blobContent.Blob))
			continue
		}

		// Handle unknown resource content types as text
		parts = append(parts, ai.NewTextPart(fmt.Sprintf("[Unknown MCP resource content type: %T]", content)))
	}

	return parts, nil
}
