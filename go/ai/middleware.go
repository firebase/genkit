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
	// Generate wraps each iteration of the tool loop.
	Generate(ctx context.Context, state *GenerateState, next GenerateNext) (*ModelResponse, error)
	// Model wraps each model API call.
	Model(ctx context.Context, state *ModelState, next ModelNext) (*ModelResponse, error)
	// Tool wraps each tool execution.
	Tool(ctx context.Context, state *ToolState, next ToolNext) (*ToolResponse, error)
}

// GenerateState holds state for the Generate hook.
type GenerateState struct {
	// Options is the original options passed to [Generate].
	Options *GenerateActionOptions
	// Request is the current model request for this iteration, with accumulated messages.
	Request *ModelRequest
	// Iteration is the current tool-loop iteration (0-indexed).
	Iteration int
}

// ModelState holds state for the Model hook.
type ModelState struct {
	// Request is the model request about to be sent.
	Request *ModelRequest
	// Callback is the streaming callback, or nil if not streaming.
	Callback ModelStreamCallback
}

// ToolState holds state for the Tool hook.
type ToolState struct {
	// Request is the tool request about to be executed.
	Request *ToolRequest
	// Tool is the resolved tool being called.
	Tool Tool
}

// GenerateNext is the next function in the Generate hook chain.
type GenerateNext = func(ctx context.Context, state *GenerateState) (*ModelResponse, error)

// ModelNext is the next function in the Model hook chain.
type ModelNext = func(ctx context.Context, state *ModelState) (*ModelResponse, error)

// ToolNext is the next function in the Tool hook chain.
type ToolNext = func(ctx context.Context, state *ToolState) (*ToolResponse, error)

// BaseMiddleware provides default pass-through for the three hooks.
// Embed this so you only need to implement Name() and New().
type BaseMiddleware struct{}

func (b *BaseMiddleware) Generate(ctx context.Context, state *GenerateState, next GenerateNext) (*ModelResponse, error) {
	return next(ctx, state)
}

func (b *BaseMiddleware) Model(ctx context.Context, state *ModelState, next ModelNext) (*ModelResponse, error) {
	return next(ctx, state)
}

func (b *BaseMiddleware) Tool(ctx context.Context, state *ToolState, next ToolNext) (*ToolResponse, error) {
	return next(ctx, state)
}

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
