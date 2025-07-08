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
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
)

// Embedder represents an embedder that can perform content embedding.
type Embedder interface {
	// Name returns the registry name of the embedder.
	Name() string
	// Embed embeds to content as part of the [EmbedRequest].
	Embed(ctx context.Context, req *EmbedRequest) (*EmbedResponse, error)
}

// EmbedderInfo represents the structure of the embedder information object.
type EmbedderInfo struct {
	// Label is a user-friendly name for the embedder model (e.g., "Google AI - Gemini Pro").
	Label string `json:"label,omitempty"`
	// Supports defines the capabilities of the embedder, such as input types and multilingual support.
	Supports *EmbedderSupports `json:"supports,omitempty"`
	// Dimensions specifies the number of dimensions in the embedding vector.
	Dimensions int `json:"dimensions,omitempty"`
}

// EmbedderSupports represents the supported capabilities of the embedder model.
type EmbedderSupports struct {
	// Input lists the types of data the model can process (e.g., "text", "image", "video").
	Input []string `json:"input,omitempty"`
	// Multilingual indicates whether the model supports multiple languages.
	Multilingual bool `json:"multilingual,omitempty"`
}

// EmbedderOptions represents the configuration options for an embedder.
type EmbedderOptions struct {
	// ConfigSchema defines the schema for the embedder's configuration options.
	ConfigSchema any `json:"configSchema,omitempty"`
	// Info contains metadata about the embedder, such as its label and capabilities.
	Info *EmbedderInfo `json:"info,omitempty"`
}

// An embedder is used to convert a document to a multidimensional vector.
type embedder core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}]

// DefineEmbedder registers the given embed function as an action, and returns an
// [Embedder] that runs it.
func DefineEmbedder(
	r *registry.Registry,
	provider, name string,
	opts *EmbedderOptions,
	embed func(context.Context, *EmbedRequest) (*EmbedResponse, error),
) Embedder {
	metadata := map[string]any{}
	metadata["type"] = "embedder"
	metadata["info"] = opts.Info
	if opts.ConfigSchema != nil {
		metadata["embedder"] = map[string]any{"customOptions": base.ToSchemaMap(opts.ConfigSchema)}
	}
	inputSchema := base.InferJSONSchema(EmbedRequest{})
	if inputSchema.Properties != nil && opts.ConfigSchema != nil {
		if _, ok := inputSchema.Properties.Get("options"); ok {
			inputSchema.Properties.Set("options", base.InferJSONSchema(opts.ConfigSchema))
		}
	}
	return (*embedder)(core.DefineActionWithInputSchema(r, provider, name, core.ActionTypeEmbedder, metadata, inputSchema, embed))
}

// LookupEmbedder looks up an [Embedder] registered by [DefineEmbedder].
// It will try to resolve the embedder dynamically if the embedder is not found.
// It returns nil if the embedder was not resolved.
func LookupEmbedder(r *registry.Registry, provider, name string) Embedder {
	action := core.ResolveActionFor[*EmbedRequest, *EmbedResponse, struct{}](r, core.ActionTypeEmbedder, provider, name)
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
