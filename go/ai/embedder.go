// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"errors"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
)

// Embedder represents an embedder that can perform content embedding.
type Embedder interface {
	// Name returns the registry name of the embedder.
	Name() string
	// Embed embeds to content as part of the [EmbedRequest].
	Embed(ctx context.Context, req *EmbedRequest) (*EmbedResponse, error)
}

// An embedderActionDef is used to convert a document to a
// multidimensional vector.
type embedderActionDef core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}]

type embedderAction = core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}]

// EmbedRequest is the data we pass to convert one or more documents
// to a multidimensional vector.
type EmbedRequest struct {
	Documents []*Document `json:"input"`
	Options   any         `json:"options,omitempty"`
}

type EmbedResponse struct {
	// One embedding for each Document in the request, in the same order.
	Embeddings []*DocumentEmbedding `json:"embeddings"`
}

// DocumentEmbedding holds emdedding information about a single document.
type DocumentEmbedding struct {
	// The vector for the embedding.
	Embedding []float32 `json:"embedding"`
}

// DefineEmbedder registers the given embed function as an action, and returns an
// [Embedder] that runs it.
func DefineEmbedder(
	r *registry.Registry,
	provider, name string,
	embed func(context.Context, *EmbedRequest) (*EmbedResponse, error),
) Embedder {
	return (*embedderActionDef)(core.DefineAction(r, provider, name, atype.Embedder, nil, embed))
}

// IsDefinedEmbedder reports whether an embedder is defined.
func IsDefinedEmbedder(r *registry.Registry, provider, name string) bool {
	return LookupEmbedder(r, provider, name) != nil
}

// LookupEmbedder looks up an [Embedder] registered by [DefineEmbedder].
// It returns nil if the embedder was not defined.
func LookupEmbedder(r *registry.Registry, provider, name string) Embedder {
	action := core.LookupActionFor[*EmbedRequest, *EmbedResponse, struct{}](r, atype.Embedder, provider, name)
	if action == nil {
		return nil
	}
	return (*embedderActionDef)(action)
}

// Embed runs the given [Embedder].
func (e *embedderActionDef) Embed(ctx context.Context, req *EmbedRequest) (*EmbedResponse, error) {
	if e == nil {
		return nil, errors.New("Embed called on a nil Embedder; check that all embedders are defined")
	}
	a := (*core.ActionDef[*EmbedRequest, *EmbedResponse, struct{}])(e)
	return a.Run(ctx, req, nil)
}

func (e *embedderActionDef) Name() string {
	return (*embedderAction)(e).Name()
}

// EmbedOption configures params of the Embed call.
type EmbedOption func(req *EmbedRequest) error

// WithEmbedOptions set embedder options on [EmbedRequest]
func WithEmbedOptions(opts any) EmbedOption {
	return func(req *EmbedRequest) error {
		req.Options = opts
		return nil
	}
}

// WithEmbedText adds simple text documents to [EmbedRequest]
func WithEmbedText(text ...string) EmbedOption {
	return func(req *EmbedRequest) error {
		var docs []*Document
		for _, p := range text {
			docs = append(docs, DocumentFromText(p, nil))
		}
		req.Documents = append(req.Documents, docs...)
		return nil
	}
}

// WithEmbedDocs adds documents to [EmbedRequest]
func WithEmbedDocs(docs ...*Document) EmbedOption {
	return func(req *EmbedRequest) error {
		req.Documents = append(req.Documents, docs...)
		return nil
	}
}

// Embed invokes the embedder with provided options.
func Embed(ctx context.Context, e Embedder, opts ...EmbedOption) (*EmbedResponse, error) {
	req := &EmbedRequest{}
	for _, with := range opts {
		err := with(req)
		if err != nil {
			return nil, err
		}
	}
	return e.Embed(ctx, req)
}
