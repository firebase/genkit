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

// Retriever supports adding documents to a database, and
// retrieving documents from the database that are similar to a query document.
// Vector databases will implement this interface.
type Retriever interface {
	// Add a document to the database.
	Index(context.Context, *IndexerRequest) error
	// Retrieve matching documents from the database.
	Retrieve(context.Context, *RetrieverRequest) (*RetrieverResponse, error)
}

// IndexerRequest is the data we pass to add documents to the database.
// The Options field is specific to the actual retriever implementation.
type IndexerRequest struct {
	Documents []*Document `json:"docs"`
	Options   any         `json:"options,omitempty"`
}

// RetrieverRequest is the data we pass to retrieve documents from the database.
// The Options field is specific to the actual retriever implementation.
type RetrieverRequest struct {
	Document *Document `json:"content"`
	Options  any       `json:"options,omitempty"`
}

// RetrieverResponse is the response to a document lookup.
type RetrieverResponse struct {
	Documents []*Document `json:"documents"`
}

// DefineRetriever takes index and retrieve functions that access a vector DB
// and returns a new Retriever that wraps them in registered actions.
func DefineRetriever(
	name string,
	index func(context.Context, *IndexerRequest) error,
	retrieve func(context.Context, *RetrieverRequest) (*RetrieverResponse, error),
) Retriever {
	ia := core.NewAction(name, core.ActionTypeIndexer, nil, func(ctx context.Context, req *IndexerRequest) (struct{}, error) {
		return struct{}{}, index(ctx, req)
	})
	core.RegisterAction(name, ia)
	ra := core.NewAction(name, core.ActionTypeRetriever, nil, retrieve)
	core.RegisterAction(name, ra)
	return &retriever{ia, ra}
}

type retriever struct {
	index    *core.Action[*IndexerRequest, struct{}, struct{}]
	retrieve *core.Action[*RetrieverRequest, *RetrieverResponse, struct{}]
}

func (r *retriever) Index(ctx context.Context, req *IndexerRequest) error {
	_, err := r.index.Run(ctx, req, nil)
	return err
}

func (r *retriever) Retrieve(ctx context.Context, req *RetrieverRequest) (*RetrieverResponse, error) {
	return r.retrieve.Run(ctx, req, nil)
}
