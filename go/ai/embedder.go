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
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/registry"
)

// Embedder represents an embedder that can perform content embedding.
type Embedder interface {
	// Name returns the registry name of the embedder.
	Name() string
	// Embed embeds to content as part of the [EmbedRequest].
	Embed(ctx context.Context, req *EmbedRequest) (*EmbedResponse, error)
}

// An embedder is used to convert a document to a multidimensional vector.
type embedder core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}]

// DefineEmbedder registers the given embed function as an action, and returns an
// [Embedder] that runs it.
func DefineEmbedder(
	r *registry.Registry,
	provider, name string,
	embed func(context.Context, *EmbedRequest) (*EmbedResponse, error),
) Embedder {
	return (*embedder)(core.DefineAction(r, provider, name, core.ActionTypeEmbedder, nil, embed))
}

// LookupEmbedder looks up an [Embedder] registered by [DefineEmbedder].
// It returns nil if the embedder was not defined.
func LookupEmbedder(r *registry.Registry, provider, name string) Embedder {
	action := core.LookupActionFor[*EmbedRequest, *EmbedResponse, struct{}](r, core.ActionTypeEmbedder, provider, name)
	if action == nil {
		return nil
	}

	return (*embedder)(action)
}

// Name returns the name of the embedder.
func (e *embedder) Name() string {
	return (*core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}])(e).Name()
}

// Embed runs the given [Embedder].
func (e *embedder) Embed(ctx context.Context, req *EmbedRequest) (*EmbedResponse, error) {
	return (*core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}])(e).Run(ctx, req, nil)
}

// Embed invokes the embedder with provided options.
func Embed(ctx context.Context, e Embedder, opts ...EmbedderOption) (*EmbedResponse, error) {
	embedOpts := &embedderOptions{}
	for _, opt := range opts {
		if err := opt.applyEmbedder(embedOpts); err != nil {
			return nil, fmt.Errorf("ai.Embed: error applying options: %w", err)
		}
	}

	req := &EmbedRequest{
		Input:   embedOpts.Documents,
		Options: embedOpts.Config,
	}

	return e.Embed(ctx, req)
}
