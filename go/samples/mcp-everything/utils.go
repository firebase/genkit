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

package main

import (
	"github.com/firebase/genkit/go/genkit"
)

// Helper function to list all available tools in Genkit
type ToolInfo struct {
	Name        string
	Description string
}

func listTools(g *genkit.Genkit) []ToolInfo {
	var tools []ToolInfo

	// Iterate through all registered actions in Genkit
	// This is a workaround since there's no direct API to list all tools
	// We'll gather what we can from the available tools
	// In a real application, you might use a more direct method if available

	// A basic check is to try some common tool names we might expect
	knownPrefixes := []string{"everything/", ""}
	knownTools := []string{"randomNumber", "randomInt", "add", "echo"}

	for _, prefix := range knownPrefixes {
		for _, toolName := range knownTools {
			fullName := prefix + toolName
			tool := genkit.LookupTool(g, fullName)
			if tool != nil {
				tools = append(tools, ToolInfo{
					Name:        fullName,
					Description: tool.Definition().Description,
				})
			}
		}
	}

	return tools
}
