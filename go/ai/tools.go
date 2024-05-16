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

	"github.com/firebase/genkit/go/genkit"
)

// A Tool is an implementation of a single tool.
// The ToolDefinition has JSON schemas that describe the types.
// TODO: This should be generic over the function input and output types,
// and something in the general code should handle the JSON conversion.
type Tool struct {
	Definition *ToolDefinition
	Fn         func(context.Context, map[string]any) (map[string]any, error)
}

// RegisterTool registers a tool function.
func RegisterTool(name string, definition *ToolDefinition, metadata map[string]any, fn func(ctx context.Context, input map[string]any) (map[string]any, error)) {
	if len(metadata) > 0 {
		metadata = maps.Clone(metadata)
	}
	if metadata == nil {
		metadata = make(map[string]any)
	}
	metadata["type"] = "tool"

	// TODO: There is no provider for a tool.
	genkit.RegisterAction(genkit.ActionTypeTool, "tool",
		genkit.NewAction(definition.Name, metadata, fn))
}

// toolActionType is the instantiated genkit.Action type registered
// by RegisterTool.
type toolActionType = genkit.Action[map[string]any, map[string]any, struct{}]

// RunTool looks up a tool registered by [RegisterTool],
// runs it with the given input, and returns the result.
func RunTool(ctx context.Context, name string, input map[string]any) (map[string]any, error) {
	action := genkit.LookupAction(genkit.ActionTypeTool, "tool", name)
	if action == nil {
		return nil, fmt.Errorf("no tool named %q", name)
	}
	toolInst, ok := action.(*toolActionType)
	if !ok {
		return nil, fmt.Errorf("RunTool: tool action %q has type %T, want %T", name, action, &toolActionType{})
	}
	return toolInst.Run(ctx, input, nil)
}
