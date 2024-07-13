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
	"errors"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
)

// An Embedder is used to convert a document to a
// multidimensional vector.
type Embedder core.Action[*EmbedRequest, *EmbedResponse, struct{}]

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
// [EmbedderAction] that runs it.
func DefineEmbedder(provider, name string, embed func(context.Context, *EmbedRequest) (*EmbedResponse, error)) *Embedder {
	return (*Embedder)(core.DefineAction(provider, name, atype.Embedder, nil, embed))
}

// LookupEmbedder looks up an [EmbedderAction] registered by [DefineEmbedder].
// It returns nil if the embedder was not defined.
func LookupEmbedder(provider, name string) *Embedder {
	action := core.LookupActionFor[*EmbedRequest, *EmbedResponse, struct{}](atype.Embedder, provider, name)
	if action == nil {
		return nil
	}
	return (*Embedder)(action)
}

// Embed runs the given [Embedder].
func (e *Embedder) Embed(ctx context.Context, req *EmbedRequest) (*EmbedResponse, error) {
	if e == nil {
		return nil, errors.New("Embed called on a nil Embedder; check that all embedders are defined")
	}
	a := (*core.Action[*EmbedRequest, *EmbedResponse, struct{}])(e)
	return a.Run(ctx, req, nil)
}
