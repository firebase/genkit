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
	"encoding/base64"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func (c *GenkitMCPClient) GetActiveResources(ctx context.Context) ([]ai.Resource, error) {
	if !c.IsEnabled() || c.server == nil || c.server.Session == nil {
		return nil, nil
	}
	if c.server.Error != nil {
		return nil, c.server.Error
	}

	var resources []ai.Resource

	// fetch static resources (URIs like "file:///logs/today.txt")
	for res, err := range c.server.Session.Resources(ctx, nil) {
		if err != nil {
			return nil, fmt.Errorf("failed to list resources: %w", err)
		}
		resources = append(resources, c.toGenkitResource(res))
	}

	// fetch resource templates (dynamic URIS like "db://{table}/{id}")
	for res, err := range c.server.Session.ResourceTemplates(ctx, nil) {
		if err != nil {
			return nil, fmt.Errorf("failed to list resource templates: %w", err)
		}
		resources = append(resources, c.toGenkitResourceTemplate(res))
	}

	return resources, nil
}

func (c *GenkitMCPClient) toGenkitResource(r *mcp.Resource) ai.Resource {
	name := fmt.Sprintf("%s_%s", c.options.Name, r.Name)

	metadata := map[string]any{
		"mcp_server": c.options.Name,
		"mcp_uri":    r.URI,
	}

	if r.Annotations != nil {
		if r.Annotations.Audience != nil {
			metadata["audience"] = r.Annotations.Audience
		}
		if r.Annotations.Priority != 0 {
			metadata["priority"] = r.Annotations.Priority
		}
		if r.Annotations.LastModified != "" {
			metadata["last_modified"] = r.Annotations.LastModified
		}
	}

	return ai.NewResource(name, &ai.ResourceOptions{
		URI:         r.URI,
		Description: r.Description,
		Metadata:    metadata,
	}, c.readResourceHandler)
}

func (c *GenkitMCPClient) toGenkitResourceTemplate(rt *mcp.ResourceTemplate) ai.Resource {
	name := fmt.Sprintf("%s_%s", c.options.Name, rt.Name)

	return ai.NewResource(name, &ai.ResourceOptions{
		Template:    rt.URITemplate,
		Description: rt.Description,
	}, c.readResourceHandler)
}

func (c *GenkitMCPClient) readResourceHandler(ctx context.Context, input *ai.ResourceInput) (*ai.ResourceOutput, error) {
	if c.server == nil || c.server.Session == nil {
		return nil, fmt.Errorf("MCP session is closed")
	}
	if c.server.Error != nil {
		return nil, c.server.Error
	}

	params := &mcp.ReadResourceParams{
		URI: input.URI,
	}

	res, err := c.server.Session.ReadResource(ctx, params)
	if err != nil {
		return nil, fmt.Errorf("failed to read MCP resource %s: %w", input.URI, err)
	}

	parts := c.toGenkitParts(res.Contents)

	return &ai.ResourceOutput{
		Content: parts,
	}, nil
}

func (c *GenkitMCPClient) toGenkitParts(contents []*mcp.ResourceContents) []*ai.Part {
	var parts []*ai.Part

	for _, cont := range contents {
		if cont.Text != "" {
			if cont.MIMEType == "application/json" {
				parts = append(parts, ai.NewDataPart(cont.Text))
				continue
			}
			parts = append(parts, ai.NewTextPart(cont.Text))
			continue
		}

		if len(cont.Blob) > 0 {
			encodedString := base64.StdEncoding.EncodeToString(cont.Blob)
			parts = append(parts, ai.NewMediaPart(cont.MIMEType, encodedString))
		}
	}

	return parts
}
