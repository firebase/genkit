// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"errors"
	"maps"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"
)

// A Prompt is used to render a prompt template,
// producing a [GenerateRequest] that may be passed to a [Model].
type Prompt core.ActionDef[any, *ModelRequest, struct{}]

// DefinePrompt takes a function that renders a prompt template
// into a [GenerateRequest] that may be passed to a [Model].
// The prompt expects some input described by inputSchema.
// DefinePrompt registers the function as an action,
// and returns a [Prompt] that runs it.
func DefinePrompt(r *registry.Registry, provider, name string, metadata map[string]any, inputSchema *jsonschema.Schema, render func(context.Context, any) (*ModelRequest, error)) *Prompt {
	mm := maps.Clone(metadata)
	if mm == nil {
		mm = make(map[string]any)
	}
	mm["type"] = "prompt"
	return (*Prompt)(core.DefineActionWithInputSchema(r, provider, name, atype.Prompt, mm, inputSchema, render))
}

// IsDefinedPrompt reports whether a [Prompt] is defined.
func IsDefinedPrompt(r *registry.Registry, provider, name string) bool {
	return LookupPrompt(r, provider, name) != nil
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(r *registry.Registry, provider, name string) *Prompt {
	return (*Prompt)(core.LookupActionFor[any, *ModelRequest, struct{}](r, atype.Prompt, provider, name))
}

// Render renders the [Prompt] with some input data.
func (p *Prompt) Render(ctx context.Context, input any) (*ModelRequest, error) {
	if p == nil {
		return nil, errors.New("Render called on a nil Prompt; check that all prompts are defined")
	}
	return (*core.ActionDef[any, *ModelRequest, struct{}])(p).Run(ctx, input, nil)
}
