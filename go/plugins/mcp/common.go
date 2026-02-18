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
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const (
	RoleUser      mcp.Role = "user"
	RoleAssistant mcp.Role = "assistant"
)

// ExtractTextFromContent extracts text content from MCP Content
func ExtractTextFromContent(content mcp.Content) string {
	if content == nil {
		return ""
	}

	switch c := content.(type) {
	case *mcp.TextContent:
		return c.Text
	case *mcp.EmbeddedResource:
		if c.Resource != nil {
			return c.Resource.Text
		}
	}

	return ""
}
