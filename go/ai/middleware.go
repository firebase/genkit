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
//
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
)

// middlewareConfigFunc creates a Middleware instance from JSON config.
type middlewareConfigFunc = func([]byte) (Middleware, error)

// Middleware provides hooks for different stages of generation.
type Middleware interface {
	// Name returns the middleware's unique identifier.
	Name() string
	// New returns a fresh instance for each ai.Generate() call, enabling per-invocation state.
	New() Middleware
	// WrapGenerate wraps each iteration of the tool loop.
	WrapGenerate(ctx context.Context, params *GenerateParams, next GenerateNext) (*ModelResponse, error)
	// WrapModel wraps each model API call.
	WrapModel(ctx context.Context, params *ModelParams, next ModelNext) (*ModelResponse, error)
	// WrapTool wraps each tool execution.
	WrapTool(ctx context.Context, params *ToolParams, next ToolNext) (*ToolResponse, error)
	// Tools returns additional tools to make available during generation.
	// These tools are dynamically registered when the middleware is used via [WithUse].
	Tools() []Tool
}

// GenerateParams holds params for the WrapGenerate hook.
type GenerateParams struct {
	// Options is the original options passed to [Generate].
	Options *GenerateActionOptions
	// Request is the current model request for this iteration, with accumulated messages.
	Request *ModelRequest
	// Iteration is the current tool-loop iteration (0-indexed).
	Iteration int
}

// ModelParams holds params for the WrapModel hook.
type ModelParams struct {
	// Request is the model request about to be sent.
	Request *ModelRequest
	// Callback is the streaming callback, or nil if not streaming.
	Callback ModelStreamCallback
}

// ToolParams holds params for the WrapTool hook.
type ToolParams struct {
	// Request is the tool request about to be executed.
	Request *ToolRequest
	// Tool is the resolved tool being called.
	Tool Tool
}

// GenerateNext is the next function in the WrapGenerate hook chain.
type GenerateNext = func(ctx context.Context, params *GenerateParams) (*ModelResponse, error)

// ModelNext is the next function in the WrapModel hook chain.
type ModelNext = func(ctx context.Context, params *ModelParams) (*ModelResponse, error)

// ToolNext is the next function in the WrapTool hook chain.
type ToolNext = func(ctx context.Context, params *ToolParams) (*ToolResponse, error)

// BaseMiddleware provides default pass-through for the three hooks.
// Embed this so you only need to implement Name() and New().
type BaseMiddleware struct{}

func (b *BaseMiddleware) WrapGenerate(ctx context.Context, params *GenerateParams, next GenerateNext) (*ModelResponse, error) {
	return next(ctx, params)
}

func (b *BaseMiddleware) WrapModel(ctx context.Context, params *ModelParams, next ModelNext) (*ModelResponse, error) {
	return next(ctx, params)
}

func (b *BaseMiddleware) WrapTool(ctx context.Context, params *ToolParams, next ToolNext) (*ToolResponse, error) {
	return next(ctx, params)
}

func (b *BaseMiddleware) Tools() []Tool { return nil }

// Register registers the descriptor with the registry.
func (d *MiddlewareDesc) Register(r api.Registry) {
	r.RegisterValue("/middleware/"+d.Name, d)
}

// NewMiddleware creates a middleware descriptor without registering it.
// The prototype carries stable state; configFromJSON calls prototype.New()
// then unmarshals user config on top.
func NewMiddleware[T Middleware](description string, prototype T) *MiddlewareDesc {
	return &MiddlewareDesc{
		Name:         prototype.Name(),
		Description:  description,
		ConfigSchema: core.InferSchemaMap(*new(T)),
		configFromJSON: func(configJSON []byte) (Middleware, error) {
			inst := prototype.New()
			if len(configJSON) > 0 {
				if err := json.Unmarshal(configJSON, inst); err != nil {
					return nil, fmt.Errorf("middleware %q: %w", prototype.Name(), err)
				}
			}
			return inst, nil
		},
	}
}

// DefineMiddleware creates and registers a middleware descriptor.
func DefineMiddleware[T Middleware](r api.Registry, description string, prototype T) *MiddlewareDesc {
	d := NewMiddleware(description, prototype)
	d.Register(r)
	return d
}

// LookupMiddleware looks up a registered middleware descriptor by name.
func LookupMiddleware(r api.Registry, name string) *MiddlewareDesc {
	v := r.LookupValue("/middleware/" + name)
	if v == nil {
		return nil
	}
	d, ok := v.(*MiddlewareDesc)
	if !ok {
		return nil
	}
	return d
}

// MiddlewarePlugin is implemented by plugins that provide middleware.
type MiddlewarePlugin interface {
	ListMiddleware(ctx context.Context) ([]*MiddlewareDesc, error)
}
