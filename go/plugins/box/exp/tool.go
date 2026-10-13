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

package exp

import (
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/ai/tool"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
)

// NewTool returns an unregistered tool proxy for the tool named name in the
// box. Use it when there is no local copy of the tool (another language, a
// separate entry point); otherwise prefer [NewToolFrom]. The schemas come from
// In and Out, or from [WithInputSchema] / [WithOutputSchema] when In / Out
// are any.
//
//	search := box.NewTool[SearchIn, SearchOut](b, "search", "Search the repo.")
//	genkit.Generate(ctx, g, ai.WithTools(search), ...)
func NewTool[In, Out any](b *Box, name, description string, opts ...ProxyOption) *ai.ToolAction[In, Out] {
	return newToolProxy[In, Out](b, name, name, description, applyProxyOptions(opts))
}

// DefineTool is [NewTool] that also registers the proxy, so it shows up in
// the Dev UI.
func DefineTool[In, Out any](b *Box, name, description string, opts ...ProxyOption) *ai.ToolAction[In, Out] {
	t := NewTool[In, Out](b, name, description, opts...)
	genkit.RegisterAction(b.g, t)
	return t
}

// NewToolFrom returns an unregistered proxy for a real tool: same name,
// description and schemas, with every call running the tool in the box. This
// is the same-language path: define the tool once and hand it over, no schema
// restatement.
//
//	runShell := genkit.DefineTool(g, "runShell", "Run a shell command.", runShellFn)
//	boxedRunShell := box.NewToolFrom(b, runShell)
func NewToolFrom[In, Out any](b *Box, t *ai.ToolAction[In, Out]) *ai.ToolAction[In, Out] {
	def := t.Definition()
	return newToolProxy[In, Out](b, def.Name, def.Name, def.Description, toolSchemas[In, Out](def))
}

// DefineToolFrom is [NewToolFrom] that also registers the proxy under name. It
// must differ from the tool's own name, which the original already occupies;
// the proxy still calls the original tool in the box.
//
//	box.DefineToolFrom(b, runShell, "boxedRunShell")
func DefineToolFrom[In, Out any](b *Box, t *ai.ToolAction[In, Out], name string) *ai.ToolAction[In, Out] {
	def := t.Definition()
	if name == def.Name {
		panic(fmt.Errorf("box.DefineToolFrom: the proxy must be renamed (got %q, same as the original)", name))
	}
	p := newToolProxy[In, Out](b, name, def.Name, def.Description, toolSchemas[In, Out](def))
	genkit.RegisterAction(b.g, p)
	return p
}

// toolSchemas carries a tool's explicit schemas over to its proxy. Typed
// schemas need no copying: the proxy infers the same ones from In and Out.
func toolSchemas[In, Out any](def *ai.ToolDefinition) *proxyOptions {
	o := &proxyOptions{}
	if isAny[In]() {
		o.inputSchema = def.InputSchema
	}
	if isAny[Out]() {
		o.outputSchema = def.OutputSchema
	}
	return o
}

// newToolProxy builds a tool named name that runs the tool target in the box.
//
// It calls the box's tool.v2 action, which returns the multipart envelope
// ({output, content}) in both Go and JS runtimes, so parts the boxed tool
// attaches reach the caller's response too.
func newToolProxy[In, Out any](b *Box, name, target, description string, o *proxyOptions) *ai.ToolAction[In, Out] {
	var toolOpts []ai.ToolOption
	if o.inputSchema != nil {
		requireAny[In]("box tool", name, "an input schema")
		toolOpts = append(toolOpts, ai.WithInputSchema(o.inputSchema))
	}
	if o.outputSchema != nil {
		requireAny[Out]("box tool", name, "an output schema")
		toolOpts = append(toolOpts, ai.WithOutputSchema(o.outputSchema))
	}
	key := actionKey(api.ActionTypeToolV2, target)
	return ai.NewTool(name, description, func(tc *ai.ToolContext, input In) (Out, error) {
		var zero Out
		in, err := json.Marshal(input)
		if err != nil {
			return zero, fmt.Errorf("box tool %q: marshal input: %w", name, err)
		}
		raw, err := b.call(tc, &RunActionRequest{Key: key, Input: in}, nil)
		if err != nil {
			return zero, err
		}
		var env struct {
			Output  json.RawMessage `json:"output"`
			Content []*ai.Part      `json:"content"`
		}
		if err := json.Unmarshal(raw, &env); err != nil {
			return zero, fmt.Errorf("box tool %q: decode response: %w", name, err)
		}
		tool.AttachParts(tc, env.Content...)
		return decodeJSON[Out](env.Output, fmt.Sprintf("tool %q output", name))
	}, toolOpts...)
}
