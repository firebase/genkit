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
	"encoding/json"
	"fmt"
	"maps"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
)

const provider = "local"

// A Tool is an implementation of a single tool.
// The ToolDefinition has JSON schemas that describe the types.
// TODO: This should be generic over the function input and output types,
// and something in the general code should handle the JSON conversion.
type Tool struct {
	Action action.Action
}

// DefineTool defines a tool function.
func DefineTool[In, Out any](name, description string, metadata map[string]any, fn func(ctx context.Context, input In) (Out, error)) *Tool {
	if len(metadata) > 0 {
		metadata = maps.Clone(metadata)
	}
	if metadata == nil {
		metadata = make(map[string]any)
	}
	metadata["type"] = "tool"
	metadata["name"] = name
	metadata["description"] = description

	toolAction := core.DefineAction(provider, name, atype.Tool, metadata, fn)

	return &Tool{
		Action: toolAction,
	}
}

func (tool *Tool) Definition() *ToolDefinition {
	return &ToolDefinition{
		Name:         tool.Action.Desc().Metadata["name"].(string),
		Description:  tool.Action.Desc().Metadata["description"].(string),
		InputSchema:  base.SchemaAsMap(tool.Action.Desc().InputSchema),
		OutputSchema: base.SchemaAsMap(tool.Action.Desc().OutputSchema),
	}
}

func (tool *Tool) Run(ctx context.Context, input map[string]any) (any, error) {
	mi, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("error marshalling tool input for %v: %v", tool.Action.Name(), err)
	}
	output, err := tool.Action.RunJSON(ctx, mi, nil)
	if err != nil {
		return nil, fmt.Errorf("error calling tool %v: %v", tool.Action.Name(), err)
	}

	var uo any
	err = json.Unmarshal(output, &uo)
	if err != nil {
		return nil, fmt.Errorf("error parsing tool input for %v: %v", tool.Action.Name(), err)
	}
	return uo, nil
}

func LookupTool(name string) *Tool {
	action := registry.Global.LookupAction(fmt.Sprintf("/tool/local/%s", name))
	return &Tool{
		Action: action,
	}
}
