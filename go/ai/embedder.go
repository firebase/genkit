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
)

// Embedder is the interface used to convert a document to a
// multidimensional vector. A [DocumentStore] will use a value of this type.
type Embedder interface {
	Embed(context.Context, *EmbedRequest) ([]float32, error)
}

// EmbedRequest is the data we pass to convert a document
// to a multidimensional vector.
type EmbedRequest struct {
	Document *Document `json:"input"`
	Options  any       `json:"options,omitempty"`
}

func DefineEmbedder(name string, embed func(context.Context, *EmbedRequest) ([]float32, error)) Embedder {
	return embedder{core.DefineAction(name, core.ActionTypeEmbedder, nil, embed)}
}

type embedder struct {
	embedAction *core.Action[*EmbedRequest, []float32, struct{}]
}

func (e embedder) Embed(ctx context.Context, req *EmbedRequest) ([]float32, error) {
	return e.embedAction.Run(ctx, req, nil)
}
