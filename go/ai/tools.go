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

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
)

const provider = "local"

// A ToolDef is an implementation of a single tool.
// The ToolDefinition has JSON schemas that describe the types.
// TODO: This should be generic over the function input and output types,
// and something in the general code should handle the JSON conversion.
type ToolDef[In, Out any] struct {
	action *core.Action[In, Out, struct{}]
}

type toolAction struct {
	action action.Action
}

type Tool interface {
	Definition() *ToolDefinition
	Action() action.Action
	Run(ctx context.Context, input map[string]any) (any, error)
}

// DefineTool defines a tool function.
func DefineTool[In, Out any](name, description string, fn func(ctx context.Context, input In) (Out, error)) *ToolDef[In, Out] {
	metadata := make(map[string]any)
	metadata["type"] = "tool"
	metadata["name"] = name
	metadata["description"] = description

	toolAction := core.DefineAction(provider, name, atype.Tool, metadata, fn)

	return &ToolDef[In, Out]{
		action: toolAction,
	}
}

func (ta *ToolDef[In, Out]) Action() action.Action {
	return ta.action
}

func (ta *toolAction) Action() action.Action {
	return ta.action
}

func (ta *ToolDef[In, Out]) Definition() *ToolDefinition {
	return definition(ta)
}

func (ta *toolAction) Definition() *ToolDefinition {
	return definition(ta)
}

func definition(ta Tool) *ToolDefinition {
	return &ToolDefinition{
		Name:         ta.Action().Desc().Metadata["name"].(string),
		Description:  ta.Action().Desc().Metadata["description"].(string),
		InputSchema:  base.SchemaAsMap(ta.Action().Desc().InputSchema),
		OutputSchema: base.SchemaAsMap(ta.Action().Desc().OutputSchema),
	}
}

func (ta *toolAction) Run(ctx context.Context, input map[string]any) (any, error) {
	return runAction(ctx, ta, input)

}

func (ta *ToolDef[In, Out]) Run(ctx context.Context, input map[string]any) (any, error) {
	return runAction(ctx, ta, input)
}

func runAction(ctx context.Context, action Tool, input map[string]any) (any, error) {
	mi, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("error marshalling tool input for %v: %v", action.Definition().Name, err)
	}
	output, err := action.Action().RunJSON(ctx, mi, nil)
	if err != nil {
		return nil, fmt.Errorf("error calling tool %v: %v", action.Definition().Name, err)
	}

	var uo any
	err = json.Unmarshal(output, &uo)
	if err != nil {
		return nil, fmt.Errorf("error parsing tool input for %v: %v", action.Definition().Name, err)
	}
	return uo, nil
}

func LookupTool(name string) Tool {
	return &toolAction{action: registry.Global.LookupAction(fmt.Sprintf("/tool/local/%s", name))}
}
