// Copyright 2024 Google LLC
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

package ai

import (
	"context"
	"fmt"
	"maps"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
)

const provider = "local"

// A Tool is an implementation of a single tool.
// The ToolDefinition has JSON schemas that describe the types.
// TODO: This should be generic over the function input and output types,
// and something in the general code should handle the JSON conversion.
type Tool struct {
	Definition *ToolDefinition
	Fn         func(context.Context, map[string]any) (map[string]any, error)
}

// DefineTool defines a tool function.
func DefineTool(definition *ToolDefinition, metadata map[string]any, fn func(ctx context.Context, input map[string]any) (map[string]any, error)) {
	if len(metadata) > 0 {
		metadata = maps.Clone(metadata)
	}
	if metadata == nil {
		metadata = make(map[string]any)
	}
	metadata["type"] = "tool"

	core.DefineAction(provider, definition.Name, atype.Tool, metadata, fn)
}

// RunTool looks up a tool registered by [DefineTool],
// runs it with the given input, and returns the result.
func RunTool(ctx context.Context, name string, input map[string]any) (map[string]any, error) {
	action := core.LookupActionFor[map[string]any, map[string]any, struct{}](atype.Tool, provider, name)
	if action == nil {
		return nil, fmt.Errorf("no tool named %q", name)
	}
	return action.Run(ctx, input, nil)
}
