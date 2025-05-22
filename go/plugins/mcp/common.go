// Package mcp provides a client for integration with the Model Context Protocol.
package mcp

import (
	"fmt"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
)

// GetPromptNameWithNamespace returns a prompt name prefixed with the client's namespace
func (c *GenkitMCPClient) GetPromptNameWithNamespace(promptName string) string {
	return fmt.Sprintf("%s_%s", c.options.Name, promptName)
}

// GetToolNameWithNamespace returns a tool name prefixed with the client's namespace
func (c *GenkitMCPClient) GetToolNameWithNamespace(toolName string) string {
	return fmt.Sprintf("%s_%s", c.options.Name, toolName)
}

// ContentToText extracts text content from MCP Content
func ContentToText(contentList []mcp.Content) string {
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

// ExtractTextFromContent extracts text content from MCP Content
func ExtractTextFromContent(content mcp.Content) string {
	if textContent, ok := content.(mcp.TextContent); ok && textContent.Type == "text" {
		return textContent.Text
	} else if resourceContent, ok := content.(mcp.EmbeddedResource); ok {
		if textResource, ok := resourceContent.Resource.(mcp.TextResourceContents); ok {
			return textResource.Text
		}
	}
	return ""
}
