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

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
)

// EmbedderAction is used to convert a document to a
// multidimensional vector.
type EmbedderAction = core.Action[*EmbedRequest, []float32, struct{}]

const embedderAssoc = atype.Assoc[EmbedderAction](atype.Embedder)

// EmbedRequest is the data we pass to convert a document
// to a multidimensional vector.
type EmbedRequest struct {
	Document *Document `json:"input"`
	Options  any       `json:"options,omitempty"`
}

// DefineEmbedder registers the given embed function as an action, and returns an
// [EmbedderAction] that runs it.
func DefineEmbedder(provider, name string, embed func(context.Context, *EmbedRequest) ([]float32, error)) *EmbedderAction {
	return core.DefineAction(provider, name, embedderAssoc, nil, embed)
}

// LookupEmbedder looks up an [EmbedderAction] registered by [DefineEmbedder].
// It returns nil if the embedder was not defined.
func LookupEmbedder(provider, name string) *EmbedderAction {
	action := core.LookupAction(embedderAssoc, provider, name)
	if action == nil {
		return nil
	}
	return action
}

// Embed runs the given [EmbedderAction].
func Embed(ctx context.Context, emb *EmbedderAction, req *EmbedRequest) ([]float32, error) {
	return emb.Run(ctx, req, nil)
}
